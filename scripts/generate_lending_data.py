"""Deterministic SME lending fixtures.

`--golden` rewrites `seeds/lending/` from the scenario table in
`lending_scenarios.py`. The seed does not change that output. `--scale N`
writes the same column layout as parquet under `data/lending/` (git-ignored)
for a later volume run. Parquet uses DuckDB, which this project already
installs; the Python standard library has no parquet writer. Generation and
the golden CSV path use the standard library only.

    python scripts/generate_lending_data.py --golden
    python scripts/generate_lending_data.py --scale 1000 --seed 7
"""

from __future__ import annotations

import argparse
import calendar
import csv
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from lending_scenarios import EXTRA_APPLICATIONS, GOLDEN_LOAN_IDS, LOANS


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "seeds" / "lending"
SCALE_DIR = ROOT / "data" / "lending"
ACCOUNTS_PATH = ROOT / "seeds" / "raw_salesforce_accounts.csv"
GOLDEN_ROW_CAP = 200
CURRENCY = "EUR"

# Column order is the contract order. Types are the contract types.
COLUMNS: dict[str, list[tuple[str, str]]] = {
    "applications": [
        ("event_id", "string"),
        ("event_type", "string"),
        ("application_id", "string"),
        ("account_id", "string"),
        ("product_id", "string"),
        ("requested_amount_minor", "integer"),
        ("approved_amount_minor", "integer"),
        ("currency_code", "string"),
        ("term_months", "integer"),
        ("effective_at", "timestamp"),
        ("recorded_at", "timestamp"),
        ("_loaded_at", "timestamp"),
    ],
    "loans": [
        ("event_id", "string"),
        ("event_type", "string"),
        ("loan_id", "string"),
        ("application_id", "string"),
        ("account_id", "string"),
        ("product_id", "string"),
        ("currency_code", "string"),
        ("principal_minor", "integer"),
        ("credit_limit_minor", "integer"),
        ("term_months", "integer"),
        ("monthly_rate_bps", "integer"),
        ("schedule_version", "integer"),
        ("effective_at", "timestamp"),
        ("recorded_at", "timestamp"),
        ("_loaded_at", "timestamp"),
    ],
    "repayment_schedule": [
        ("event_id", "string"),
        ("event_type", "string"),
        ("loan_id", "string"),
        ("account_id", "string"),
        ("schedule_version", "integer"),
        ("instalment_id", "string"),
        ("instalment_number", "integer"),
        ("due_date", "date"),
        ("principal_due_minor", "integer"),
        ("interest_due_minor", "integer"),
        ("currency_code", "string"),
        ("effective_at", "timestamp"),
        ("recorded_at", "timestamp"),
        ("_loaded_at", "timestamp"),
    ],
    "repayments": [
        ("event_id", "string"),
        ("event_type", "string"),
        ("loan_id", "string"),
        ("account_id", "string"),
        ("amount_minor", "integer"),
        ("principal_minor", "integer"),
        ("interest_minor", "integer"),
        ("currency_code", "string"),
        ("effective_at", "timestamp"),
        ("recorded_at", "timestamp"),
        ("_loaded_at", "timestamp"),
    ],
}

FILES = {
    "applications": "raw_lending__applications.csv",
    "loans": "raw_lending__loans.csv",
    "repayment_schedule": "raw_lending__repayment_schedule.csv",
    "repayments": "raw_lending__repayments.csv",
}

LOAN_KEYS = {
    "loan_id",
    "account_id",
    "product_id",
    "principal_minor",
    "credit_limit_minor",
    "term_months",
    "monthly_rate_bps",
    "originated_on",
    "close_on",
    "schedule",
    "draws",
    "cash_repayments",
    "cure",
    "default",
    "prepay",
    "restructure",
    "currency_code",
}
SCHEDULE_KEYS = {
    "n",
    "due",
    "principal_minor",
    "interest_minor",
    "paid_on",
    "superseded_on",
    "recorded_at",
}
EXCLUSIVE = ("cure", "default", "prepay", "restructure")


class FixtureError(Exception):
    pass


def stamp(day: str, hour: int, minute: int = 0) -> str:
    date.fromisoformat(day)
    return f"{day}T{hour:02d}:{minute:02d}:00Z"


def shift_days(day: str, days: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def loaded_at(recorded: str) -> str:
    day = datetime.strptime(recorded, "%Y-%m-%dT%H:%M:%SZ").date()
    return stamp((day + timedelta(days=1)).isoformat(), 6)


def times(effective: str, recorded: str | None = None) -> dict:
    recorded = recorded or effective
    row = {
        "effective_at": effective,
        "recorded_at": recorded,
        "_loaded_at": loaded_at(recorded),
    }
    if not (row["effective_at"] <= row["recorded_at"] <= row["_loaded_at"]):
        raise FixtureError(f"timestamps out of order: {row}")
    return row


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def interest_due(opening_principal: int, monthly_rate_bps: int) -> int:
    return opening_principal * monthly_rate_bps // 10_000


def salesforce_account_ids(path: Path = ACCOUNTS_PATH) -> set[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["account_id"] for row in csv.DictReader(handle)}


def assign_ids(rows: list[dict], prefix: str) -> None:
    for index, row in enumerate(rows, start=1):
        row["event_id"] = f"evt_{prefix}_{index:06d}"


def application_events(loans: list[dict], extras: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for loan in loans:
        application_id = f"APP_{loan['loan_id']}"
        product = loan["product_id"]
        requested = loan["credit_limit_minor"] if product == "RCF_SME" else loan["principal_minor"]
        term = None if product == "RCF_SME" else loan["term_months"]
        submitted = stamp(shift_days(loan["originated_on"], -5), 9)
        approved = stamp(shift_days(loan["originated_on"], -1), 9)
        rows.append(
            {
                "event_type": "submitted",
                "application_id": application_id,
                "account_id": loan["account_id"],
                "product_id": product,
                "requested_amount_minor": requested,
                "approved_amount_minor": None,
                "currency_code": loan.get("currency_code", CURRENCY),
                "term_months": term,
                **times(submitted),
            }
        )
        rows.append(
            {
                "event_type": "approved",
                "application_id": application_id,
                "account_id": loan["account_id"],
                "product_id": product,
                "requested_amount_minor": requested,
                "approved_amount_minor": requested,
                "currency_code": loan.get("currency_code", CURRENCY),
                "term_months": term,
                **times(approved),
            }
        )
    for extra in extras:
        currency = extra.get("currency_code", CURRENCY)
        common = {
            "application_id": extra["application_id"],
            "account_id": extra["account_id"],
            "product_id": extra["product_id"],
            "requested_amount_minor": extra["requested_amount_minor"],
            "currency_code": currency,
            "term_months": extra["term_months"],
        }
        rows.append(
            {
                "event_type": "submitted",
                "approved_amount_minor": None,
                **common,
                **times(stamp(extra["submitted_on"], 9)),
            }
        )
        rows.append(
            {
                "event_type": extra["decision"],
                "approved_amount_minor": None,
                **common,
                **times(stamp(extra["decided_on"], 9)),
            }
        )
    assign_ids(rows, "app")
    return rows


def loan_shell(loan: dict, event_type: str, effective: str, **amounts) -> dict:
    blank = {
        "principal_minor": None,
        "credit_limit_minor": None,
        "term_months": None,
        "monthly_rate_bps": None,
        "schedule_version": None,
    }
    blank.update(amounts)
    return {
        "event_type": event_type,
        "loan_id": loan["loan_id"],
        "application_id": f"APP_{loan['loan_id']}",
        "account_id": loan["account_id"],
        "product_id": loan["product_id"],
        "currency_code": loan.get("currency_code", CURRENCY),
        **blank,
        **times(effective),
    }


def schedule_row(loan: dict, item: dict, version: int, event_type: str, effective: str) -> dict:
    return {
        "event_type": event_type,
        "loan_id": loan["loan_id"],
        "account_id": loan["account_id"],
        "schedule_version": version,
        "instalment_id": f"{loan['loan_id']}-v{version}-{item['n']}",
        "instalment_number": item["n"],
        "due_date": item["due"],
        "principal_due_minor": item["principal_minor"],
        "interest_due_minor": item["interest_minor"],
        "currency_code": loan.get("currency_code", CURRENCY),
        **times(effective),
    }


def repayment_row(
    loan: dict,
    event_type: str,
    principal: int,
    interest: int,
    paid_on: str,
    recorded_at: str | None = None,
) -> dict:
    return {
        "event_type": event_type,
        "loan_id": loan["loan_id"],
        "account_id": loan["account_id"],
        "amount_minor": principal + interest,
        "principal_minor": principal,
        "interest_minor": interest,
        "currency_code": loan.get("currency_code", CURRENCY),
        **times(stamp(paid_on, 10), recorded_at),
    }


def compile_loans(loans: list[dict]) -> dict[str, list[dict]]:
    loan_rows: list[dict] = []
    schedule_rows: list[dict] = []
    repayment_rows: list[dict] = []
    for loan in loans:
        _check_shape(loan)
        originated = loan_shell(
            loan,
            "originated",
            stamp(loan["originated_on"], 9),
            principal_minor=0 if loan["product_id"] == "RCF_SME" else loan["principal_minor"],
            credit_limit_minor=loan.get("credit_limit_minor"),
            term_months=None if loan["product_id"] == "RCF_SME" else loan["term_months"],
            monthly_rate_bps=loan["monthly_rate_bps"],
            schedule_version=1,
        )
        loan_rows.append(originated)
        # A term schedule exists at origination. A revolving bill exists on its statement date.
        version_one = stamp(loan["originated_on"], 9)
        _emit_schedule(
            loan,
            loan["schedule"],
            1,
            version_one,
            schedule_rows,
            repayment_rows,
            effective_on_due=loan["product_id"] == "RCF_SME",
        )
        if loan["product_id"] == "RCF_SME":
            for draw in loan.get("draws", []):
                repayment_rows.append(
                    repayment_row(loan, "draw_posted", draw["amount_minor"], 0, draw["on"])
                )
            for cash in loan.get("cash_repayments", []):
                repayment_rows.append(
                    repayment_row(
                        loan,
                        "repayment_posted",
                        cash["principal_minor"],
                        cash["interest_minor"],
                        cash["on"],
                    )
                )
        if "restructure" in loan:
            reshaped = loan["restructure"]
            loan_rows.append(
                loan_shell(
                    loan,
                    "restructured",
                    stamp(reshaped["on"], 9),
                    principal_minor=reshaped["principal_minor"],
                    term_months=reshaped["term_months"],
                    monthly_rate_bps=reshaped["monthly_rate_bps"],
                    schedule_version=2,
                )
            )
            _emit_schedule(
                loan,
                reshaped["schedule"],
                2,
                stamp(reshaped["on"], 9),
                schedule_rows,
                repayment_rows,
            )
        if "prepay" in loan:
            repayment_rows.append(
                repayment_row(loan, "repayment_posted", loan["prepay"]["principal_minor"], 0, loan["prepay"]["on"])
            )
        if "cure" in loan:
            repayment_rows.append(
                repayment_row(
                    loan,
                    "repayment_posted",
                    loan["cure"]["principal_minor"],
                    loan["cure"]["interest_minor"],
                    loan["cure"]["on"],
                )
            )
        if "default" in loan:
            loan_rows.append(
                loan_shell(
                    loan,
                    "defaulted",
                    stamp(loan["default"]["on"], 9),
                    principal_minor=loan["default"]["principal_minor"],
                )
            )
            loan_rows.append(
                loan_shell(
                    loan,
                    "written_off",
                    stamp(loan["default"]["on"], 10),
                    principal_minor=loan["default"]["principal_minor"],
                )
            )
        if loan.get("close_on"):
            loan_rows.append(loan_shell(loan, "closed", stamp(loan["close_on"], 11), principal_minor=0))
    order = {loan["loan_id"]: index for index, loan in enumerate(loans)}
    repayment_rows.sort(
        key=lambda row: (order[row["loan_id"]], row["effective_at"], row["event_type"], row["amount_minor"])
    )
    assign_ids(loan_rows, "ln")
    assign_ids(schedule_rows, "sch")
    assign_ids(repayment_rows, "pmt")
    return {
        "loans": loan_rows,
        "repayment_schedule": schedule_rows,
        "repayments": repayment_rows,
    }


def _emit_schedule(loan, items, version, effective, schedule_rows, repayment_rows, effective_on_due=False) -> None:
    cash: list[dict] = []
    for item in items:
        unknown = set(item) - SCHEDULE_KEYS
        if unknown:
            raise FixtureError(f"{loan['loan_id']} instalment has unknown keys {sorted(unknown)}")
        if item.get("paid_on") and item.get("superseded_on"):
            raise FixtureError(f"{loan['loan_id']} instalment {item['n']} is both paid and superseded")
        item_effective = stamp(item["due"], 9) if effective_on_due else effective
        schedule_rows.append(schedule_row(loan, item, version, "instalment_scheduled", item_effective))
        if item.get("superseded_on"):
            schedule_rows.append(
                schedule_row(loan, item, version, "instalment_superseded", stamp(item["superseded_on"], 9))
            )
        if item.get("paid_on"):
            cash.append(
                repayment_row(
                    loan,
                    "repayment_posted",
                    item["principal_minor"],
                    item["interest_minor"],
                    item["paid_on"],
                    item.get("recorded_at"),
                )
            )
    # Keep cash in scenario order. The caller sorts only when it means to.
    repayment_rows.extend(cash)


def _check_shape(loan: dict) -> None:
    unknown = set(loan) - LOAN_KEYS
    if unknown:
        raise FixtureError(f"{loan.get('loan_id')} has unknown keys {sorted(unknown)}")
    chosen = [name for name in EXCLUSIVE if name in loan]
    if len(chosen) > 1:
        raise FixtureError(f"{loan['loan_id']} combines {chosen}")
    product = loan["product_id"]
    if product == "RCF_SME":
        if "credit_limit_minor" not in loan or loan.get("principal_minor", 0) not in (0, None):
            raise FixtureError(f"{loan['loan_id']} revolving line needs a limit and no disbursed principal")
        if any(name in loan for name in ("cure", "default", "prepay", "restructure", "close_on", "term_months")):
            raise FixtureError(f"{loan['loan_id']} revolving line does not amortise, close, or restructure here")
    elif product == "TERM_SME":
        for key in ("principal_minor", "term_months"):
            if key not in loan:
                raise FixtureError(f"{loan['loan_id']} is missing {key}")
        if "default" in loan and loan.get("close_on"):
            raise FixtureError(f"{loan['loan_id']} is written off and also closed")
        if "default" not in loan and not loan.get("close_on"):
            raise FixtureError(f"{loan['loan_id']} neither closes nor defaults")
    else:
        raise FixtureError(f"{loan['loan_id']} has unknown product {product}")


def build_book(loans: list[dict], extras: list[dict] | None = None) -> dict[str, list[dict]]:
    compiled = compile_loans(loans)
    return {
        "applications": application_events(loans, extras or []),
        "loans": compiled["loans"],
        "repayment_schedule": compiled["repayment_schedule"],
        "repayments": compiled["repayments"],
    }


def build_golden() -> dict[str, list[dict]]:
    book = build_book(LOANS, EXTRA_APPLICATIONS)
    check_book(book, accounts=salesforce_account_ids(), max_rows=GOLDEN_ROW_CAP, expect_loan_ids=GOLDEN_LOAN_IDS)
    return book


def build_scale(count: int, seed: int) -> dict[str, list[dict]]:
    if count < 1:
        raise FixtureError("--scale N must be at least 1")
    rng = random.Random(seed)
    loans = [_scale_loan(index, rng) for index in range(1, count + 1)]
    book = build_book(loans, [])
    forbidden = salesforce_account_ids()
    check_book(book, accounts=None, max_rows=None, expect_loan_ids=None)
    used = {row["account_id"] for row in book["loans"]}
    overlap = used & forbidden
    if overlap:
        raise FixtureError(f"scale account ids collide with Salesforce accounts: {sorted(overlap)}")
    return book


def _scale_loan(index: int, rng: random.Random) -> dict:
    origin = date(2024, 1, 15) + timedelta(days=rng.randrange(0, 300))
    origin = origin.replace(day=15)
    loan_id = f"SCALE_{index:05d}"
    account_id = f"S{index:06d}"
    if index % 7 == 0:
        limit = rng.randrange(50, 200) * 10_000
        draw_one = rng.randrange(10, 40) * 10_000
        draw_two = rng.randrange(10, 30) * 10_000
        if draw_one + draw_two > limit:
            draw_two = max(10_000, limit - draw_one)
        repay = rng.randrange(1, max(2, (draw_one + draw_two) // 10_000)) * 10_000
        draws = [
            {"on": add_months(origin, 1).replace(day=1).isoformat(), "amount_minor": draw_one},
            {"on": add_months(origin, 3).replace(day=1).isoformat(), "amount_minor": draw_two},
        ]
        cash = [
            {
                "on": add_months(origin, 4).replace(day=10).isoformat(),
                "principal_minor": repay,
                "interest_minor": 0,
            }
        ]
        schedule = []
        for number in range(1, 6):
            due = add_months(origin, number).replace(day=20)
            balance = _balance_before(draws, cash, due.isoformat() + "T09:00:00Z")
            schedule.append(
                {
                    "n": number,
                    "due": due.isoformat(),
                    "principal_minor": 0,
                    "interest_minor": interest_due(balance, 100),
                    "paid_on": due.isoformat(),
                }
            )
        return {
            "loan_id": loan_id,
            "account_id": account_id,
            "product_id": "RCF_SME",
            "credit_limit_minor": limit,
            "monthly_rate_bps": 100,
            "originated_on": origin.isoformat(),
            "draws": draws,
            "cash_repayments": cash,
            "schedule": schedule,
        }
    term = rng.choice((3, 6, 12))
    principal = rng.randrange(10, 400) * 10_000
    principal -= principal % term
    if principal < term * 10_000:
        principal = term * 10_000
    instalment = principal // term
    schedule = []
    opening = principal
    for number in range(1, term + 1):
        due = add_months(origin, number)
        due_interest = interest_due(opening, 100)
        schedule.append(
            {
                "n": number,
                "due": due.isoformat(),
                "principal_minor": instalment,
                "interest_minor": due_interest,
                "paid_on": due.isoformat(),
            }
        )
        opening -= instalment
    return {
        "loan_id": loan_id,
        "account_id": account_id,
        "product_id": "TERM_SME",
        "principal_minor": principal,
        "term_months": term,
        "monthly_rate_bps": 100,
        "originated_on": origin.isoformat(),
        "close_on": add_months(origin, term).isoformat(),
        "schedule": schedule,
    }


def _balance_before(draws: list[dict], cash: list[dict], as_of: str) -> int:
    balance = 0
    for draw in draws:
        if stamp(draw["on"], 10) < as_of:
            balance += draw["amount_minor"]
    for repayment in cash:
        if stamp(repayment["on"], 10) < as_of:
            balance -= repayment["principal_minor"]
    return balance


def check_book(
    book: dict[str, list[dict]],
    accounts: set[str] | None,
    max_rows: int | None,
    expect_loan_ids: tuple[str, ...] | None,
) -> None:
    total = sum(len(rows) for rows in book.values())
    if max_rows is not None and total > max_rows:
        raise FixtureError(f"golden book has {total} rows; cap is {max_rows}")
    originated = [row for row in book["loans"] if row["event_type"] == "originated"]
    by_loan = {row["loan_id"]: row for row in originated}
    if len(by_loan) != len(originated):
        raise FixtureError("duplicate originated loan_id")
    if expect_loan_ids is not None and tuple(by_loan) != expect_loan_ids:
        raise FixtureError(f"loan ids {tuple(by_loan)} != {expect_loan_ids}")
    if accounts is not None:
        used = {row["account_id"] for row in book["applications"]}
        unknown = used - accounts
        if unknown:
            raise FixtureError(f"account_id values are not Salesforce accounts: {sorted(unknown)}")
    _check_timestamps_and_money(book)
    _check_interest_and_principal(book, by_loan)
    _check_credit_lines(book, by_loan)


def _check_timestamps_and_money(book: dict[str, list[dict]]) -> None:
    for name, rows in book.items():
        seen = set()
        for row in rows:
            if row["event_id"] in seen:
                raise FixtureError(f"duplicate event_id {row['event_id']} in {name}")
            seen.add(row["event_id"])
            if not (row["effective_at"] <= row["recorded_at"] <= row["_loaded_at"]):
                raise FixtureError(f"{row['event_id']} timestamps out of order")
            for key, value in row.items():
                if key.endswith("_minor") and value is not None and value < 0:
                    raise FixtureError(f"{row['event_id']} {key} is negative")
    for row in book["repayments"]:
        if row["principal_minor"] + row["interest_minor"] != row["amount_minor"]:
            raise FixtureError(f"{row['event_id']} allocation does not sum to amount")
        if row["event_type"] == "draw_posted" and row["interest_minor"] != 0:
            raise FixtureError(f"{row['event_id']} draw carries interest")


def _scheduled(book, loan_id: str, version: int) -> list[dict]:
    rows = [
        row
        for row in book["repayment_schedule"]
        if row["loan_id"] == loan_id
        and row["schedule_version"] == version
        and row["event_type"] == "instalment_scheduled"
    ]
    return sorted(rows, key=lambda row: row["instalment_number"])


def _check_interest_and_principal(book, originated: dict[str, dict]) -> None:
    for loan_id, origin in originated.items():
        if origin["product_id"] != "TERM_SME":
            continue
        _walk_interest(loan_id, _scheduled(book, loan_id, 1), origin["principal_minor"], origin["monthly_rate_bps"])
        reshaped = [
            row for row in book["loans"] if row["loan_id"] == loan_id and row["event_type"] == "restructured"
        ]
        if reshaped:
            _walk_interest(
                loan_id,
                _scheduled(book, loan_id, 2),
                reshaped[0]["principal_minor"],
                reshaped[0]["monthly_rate_bps"],
            )
        repaid = sum(
            row["principal_minor"]
            for row in book["repayments"]
            if row["loan_id"] == loan_id and row["event_type"] == "repayment_posted"
        )
        written = sum(
            row["principal_minor"]
            for row in book["loans"]
            if row["loan_id"] == loan_id and row["event_type"] == "written_off"
        )
        if repaid + written != origin["principal_minor"]:
            raise FixtureError(
                f"{loan_id} principal {origin['principal_minor']} != repaid {repaid} + written off {written}"
            )
        if written and not any(
            row["event_type"] == "defaulted" and row["principal_minor"] == written
            for row in book["loans"]
            if row["loan_id"] == loan_id
        ):
            raise FixtureError(f"{loan_id} write-off does not match default")


def _walk_interest(loan_id: str, rows: list[dict], opening: int, rate_bps: int) -> None:
    remaining = opening
    if not rows:
        raise FixtureError(f"{loan_id} has no schedule")
    for row in rows:
        expect = interest_due(remaining, rate_bps)
        if row["interest_due_minor"] != expect:
            raise FixtureError(
                f"{loan_id} instalment {row['instalment_number']} interest "
                f"{row['interest_due_minor']} != {expect}"
            )
        remaining -= row["principal_due_minor"]
    if remaining != 0:
        raise FixtureError(f"{loan_id} schedule principal does not sum to {opening}")


def _check_credit_lines(book, originated: dict[str, dict]) -> None:
    for loan_id, origin in originated.items():
        if origin["product_id"] != "RCF_SME":
            continue
        limit = origin["credit_limit_minor"]
        draws = [
            row for row in book["repayments"] if row["loan_id"] == loan_id and row["event_type"] == "draw_posted"
        ]
        repayments = [
            row
            for row in book["repayments"]
            if row["loan_id"] == loan_id and row["event_type"] == "repayment_posted"
        ]
        if not draws:
            raise FixtureError(f"{loan_id} revolving line has no draw")
        balance = 0
        events = sorted(draws + repayments, key=lambda row: row["effective_at"])
        for row in events:
            if row["event_type"] == "draw_posted":
                balance += row["principal_minor"]
            elif row["principal_minor"]:
                balance -= row["principal_minor"]
            if balance < 0 or balance > limit:
                raise FixtureError(f"{loan_id} balance {balance} is outside 0..{limit}")
        for bill in _scheduled(book, loan_id, 1):
            if bill["principal_due_minor"] != 0:
                raise FixtureError(f"{loan_id} revolving bill amortises principal")
            drawn = 0
            for row in events:
                if row["effective_at"] >= bill["effective_at"]:
                    continue
                if row["event_type"] == "draw_posted":
                    drawn += row["principal_minor"]
                else:
                    drawn -= row["principal_minor"]
            expect = interest_due(drawn, origin["monthly_rate_bps"])
            if bill["interest_due_minor"] != expect:
                raise FixtureError(
                    f"{loan_id} bill {bill['instalment_number']} interest "
                    f"{bill['interest_due_minor']} != {expect} on drawn {drawn}"
                )


def write_csv(directory: Path, book: dict[str, list[dict]]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, filename in FILES.items():
        path = directory / filename
        columns = [column for column, _type in COLUMNS[name]]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n", extrasaction="raise")
            writer.writeheader()
            for row in book[name]:
                writer.writerow({key: "" if row[key] is None else row[key] for key in columns})


def write_parquet(directory: Path, book: dict[str, list[dict]]) -> None:
    try:
        import duckdb
    except ImportError as exc:
        raise FixtureError(
            "Parquet output needs the duckdb package already installed with dbt-duckdb. "
            "Run: docker compose run --rm --entrypoint python dbt scripts/generate_lending_data.py --scale N"
        ) from exc
    directory.mkdir(parents=True, exist_ok=True)
    sql_type = {"string": "VARCHAR", "integer": "BIGINT", "date": "DATE", "timestamp": "TIMESTAMPTZ"}
    connection = duckdb.connect()
    try:
        for name, rows in book.items():
            specs = COLUMNS[name]
            definitions = ", ".join(f'"{column}" {sql_type[kind]}' for column, kind in specs)
            connection.execute(f'CREATE OR REPLACE TABLE "{name}" ({definitions})')
            placeholders = ", ".join(["?"] * len(specs))
            payload = [tuple(row[column] for column, _kind in specs) for row in rows]
            if payload:
                connection.executemany(f'INSERT INTO "{name}" VALUES ({placeholders})', payload)
            destination = (directory / f"raw_lending__{name}.parquet").as_posix().replace("'", "''")
            connection.execute(f"COPY \"{name}\" TO '{destination}' (FORMAT PARQUET)")
    finally:
        connection.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic SME lending fixtures.")
    parser.add_argument("--seed", type=int, default=7, help="RNG seed for --scale. Ignored by --golden.")
    parser.add_argument("--golden", action="store_true", help="Write the named-scenario CSVs.")
    parser.add_argument("--scale", type=int, metavar="N", help="Write N loans as parquet under data/lending/.")
    parser.add_argument("--output", type=Path, help="Directory for --golden CSVs. Default: seeds/lending/.")
    args = parser.parse_args(argv)
    if not args.golden and args.scale is None:
        parser.error("pass --golden, --scale N, or both")
    if args.scale is not None and args.scale < 1:
        parser.error("--scale N must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.golden:
            if args.seed != 7 and "--seed" in (sys.argv if argv is None else argv):
                print("golden fixtures are the scenario table; --seed does not change them", file=sys.stderr)
            book = build_golden()
            write_csv(args.output or GOLDEN_DIR, book)
            total = sum(len(rows) for rows in book.values())
            counts = ", ".join(f"{name}={len(rows)}" for name, rows in book.items())
            print(f"golden loans={len(GOLDEN_LOAN_IDS)} rows={total} ({counts})")
        if args.scale is not None:
            book = build_scale(args.scale, args.seed)
            write_parquet(SCALE_DIR, book)
            total = sum(len(rows) for rows in book.values())
            print(f"scale loans={args.scale} seed={args.seed} rows={total} dir={SCALE_DIR}")
    except FixtureError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
