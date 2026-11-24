import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_lending_data as gen
from lending_scenarios import GOLDEN_LOAN_IDS


def test_committed_fixtures_match_the_scenario_table(tmp_path):
    gen.write_csv(tmp_path, gen.build_golden())
    for filename in gen.FILES.values():
        assert (tmp_path / filename).read_bytes() == (ROOT / "seeds" / "lending" / filename).read_bytes()


def test_golden_book_is_eight_loans_under_the_row_cap():
    book = gen.build_golden()
    originated = [row for row in book["loans"] if row["event_type"] == "originated"]
    assert [row["loan_id"] for row in originated] == list(GOLDEN_LOAN_IDS)
    assert sum(len(rows) for rows in book.values()) < 200
    accounts = {row["account_id"] for row in book["applications"]}
    assert accounts <= gen.salesforce_account_ids()
    assert accounts == {"A001", "A002", "A003", "A004", "A005", "A006"}


def test_late_posted_repayment_is_known_after_month_end():
    book = gen.build_golden()
    row = next(
        item
        for item in book["repayments"]
        if item["loan_id"] == "LN_LATE_POSTED" and item["effective_at"].startswith("2025-03-20")
    )
    assert row["recorded_at"] == "2025-04-04T15:00:00Z"
    assert row["_loaded_at"] == "2025-04-05T06:00:00Z"
    assert row["recorded_at"] > "2025-03-31T23:59:59Z"


def test_credit_line_draws_and_repayments_net_to_the_limit():
    book = gen.build_golden()
    rows = [row for row in book["repayments"] if row["loan_id"] == "LN_CREDIT_LINE_REVOLVING"]
    draws = sum(row["principal_minor"] for row in rows if row["event_type"] == "draw_posted")
    repaid = sum(row["principal_minor"] for row in rows if row["event_type"] == "repayment_posted")
    assert draws == 750_000
    assert repaid == 150_000
    assert draws - repaid == 600_000


def test_golden_output_does_not_depend_on_seed(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert gen.main(["--golden", "--seed", "1", "--output", str(first)]) == 0
    assert gen.main(["--golden", "--seed", "99", "--output", str(second)]) == 0
    for filename in gen.FILES.values():
        assert (first / filename).read_bytes() == (second / filename).read_bytes()


def test_scale_is_deterministic_and_does_not_reuse_salesforce_accounts():
    first = gen.build_scale(12, 7)
    again = gen.build_scale(12, 7)
    other = gen.build_scale(12, 8)
    assert first == again
    assert first != other
    used = {row["account_id"] for row in first["loans"]}
    assert used.isdisjoint(gen.salesforce_account_ids())
    assert all(account.startswith("S") for account in used)
