"""Named SME lending scenarios for the golden fixtures.

This is the table `scripts/generate_lending_data.py --golden` compiles into
`seeds/lending/`. Amounts are integer minor units of EUR (100 minor = 1.00).
The rate is an illustrative simple monthly rate: interest for an instalment
is `opening_principal * monthly_rate_bps // 10000`. It is not an APR, and it
is not a lender's price. Prepayment charges remaining principal only;
unearned future interest is cancelled, not collected. A write-off removes
remaining principal and does not capitalise unpaid interest.

Days past due, for a later month-end fact, is the number of calendar days from
the earliest unpaid instalment due date to the as-of date, and 0 when nothing
is past due (as-of on the due date is still current). An instalment is unpaid
when principal collected against it, using rows with `effective_at` on or
before the as-of date and `recorded_at` on or before the knowledge cutoff, is
below `principal_due_minor`. Superseded instalments are not due. Allocation is
oldest due date first.

`recorded_at` is when the lending system committed the event. `effective_at`
is when it took effect. `LN_LATE_POSTED` is the case where those differ: the
March repayment is effective on its due date and recorded on 4 April, so a
March close that cuts knowledge off before that `recorded_at` still sees the
instalment as unpaid (11 days past due on 31 March).

Customers are Salesforce `account_id` values from `seeds/raw_salesforce_accounts.csv`.
`loan_id` is the scenario name so a row can be found without a side map.
"""

from __future__ import annotations


# Funded loans, in the order the CSV is written. Eight named scenarios.
LOANS = [
    {
        "loan_id": "LN_ON_TIME",
        "account_id": "A002",
        "product_id": "TERM_SME",
        "principal_minor": 600_000,
        "term_months": 6,
        "monthly_rate_bps": 100,
        "originated_on": "2025-01-15",
        "close_on": "2025-07-15",
        "schedule": [
            {"n": 1, "due": "2025-02-15", "principal_minor": 100_000, "interest_minor": 6_000, "paid_on": "2025-02-15"},
            {"n": 2, "due": "2025-03-15", "principal_minor": 100_000, "interest_minor": 5_000, "paid_on": "2025-03-15"},
            {"n": 3, "due": "2025-04-15", "principal_minor": 100_000, "interest_minor": 4_000, "paid_on": "2025-04-15"},
            {"n": 4, "due": "2025-05-15", "principal_minor": 100_000, "interest_minor": 3_000, "paid_on": "2025-05-15"},
            {"n": 5, "due": "2025-06-15", "principal_minor": 100_000, "interest_minor": 2_000, "paid_on": "2025-06-15"},
            {"n": 6, "due": "2025-07-15", "principal_minor": 100_000, "interest_minor": 1_000, "paid_on": "2025-07-15"},
        ],
    },
    {
        # Unpaid on 31 March: due 16 March, so days past due = 15. Paid 1 April.
        "loan_id": "LN_LATE_15",
        "account_id": "A003",
        "product_id": "TERM_SME",
        "principal_minor": 300_000,
        "term_months": 3,
        "monthly_rate_bps": 100,
        "originated_on": "2025-01-16",
        "close_on": "2025-04-16",
        "schedule": [
            {"n": 1, "due": "2025-02-16", "principal_minor": 100_000, "interest_minor": 3_000, "paid_on": "2025-02-16"},
            {"n": 2, "due": "2025-03-16", "principal_minor": 100_000, "interest_minor": 2_000, "paid_on": "2025-04-01"},
            {"n": 3, "due": "2025-04-16", "principal_minor": 100_000, "interest_minor": 1_000, "paid_on": "2025-04-16"},
        ],
    },
    {
        # 30 days past due on 31 March (due 1 March), 60 on 30 April, cured 6 May.
        "loan_id": "LN_DPD_30_CURED",
        "account_id": "A004",
        "product_id": "TERM_SME",
        "principal_minor": 400_000,
        "term_months": 4,
        "monthly_rate_bps": 100,
        "originated_on": "2025-01-01",
        "close_on": "2025-05-06",
        "schedule": [
            {"n": 1, "due": "2025-02-01", "principal_minor": 100_000, "interest_minor": 4_000, "paid_on": "2025-02-01"},
            {"n": 2, "due": "2025-03-01", "principal_minor": 100_000, "interest_minor": 3_000},
            {"n": 3, "due": "2025-04-01", "principal_minor": 100_000, "interest_minor": 2_000},
            {"n": 4, "due": "2025-05-01", "principal_minor": 100_000, "interest_minor": 1_000},
        ],
        "cure": {"on": "2025-05-06", "principal_minor": 300_000, "interest_minor": 6_000},
    },
    {
        # 91 days past due on 31 May (due 1 March). Default and write-off on 1 June.
        "loan_id": "LN_DEFAULT_90",
        "account_id": "A005",
        "product_id": "TERM_SME",
        "principal_minor": 300_000,
        "term_months": 3,
        "monthly_rate_bps": 100,
        "originated_on": "2025-01-01",
        "schedule": [
            {"n": 1, "due": "2025-02-01", "principal_minor": 100_000, "interest_minor": 3_000, "paid_on": "2025-02-01"},
            {"n": 2, "due": "2025-03-01", "principal_minor": 100_000, "interest_minor": 2_000},
            {"n": 3, "due": "2025-04-01", "principal_minor": 100_000, "interest_minor": 1_000},
        ],
        "default": {"on": "2025-06-01", "principal_minor": 200_000},
    },
    {
        "loan_id": "LN_PREPAID",
        "account_id": "A006",
        "product_id": "TERM_SME",
        "principal_minor": 240_000,
        "term_months": 4,
        "monthly_rate_bps": 100,
        "originated_on": "2025-02-01",
        "close_on": "2025-03-20",
        "schedule": [
            {"n": 1, "due": "2025-03-01", "principal_minor": 60_000, "interest_minor": 2_400, "paid_on": "2025-03-01"},
            {"n": 2, "due": "2025-04-01", "principal_minor": 60_000, "interest_minor": 1_800, "superseded_on": "2025-03-20"},
            {"n": 3, "due": "2025-05-01", "principal_minor": 60_000, "interest_minor": 1_200, "superseded_on": "2025-03-20"},
            {"n": 4, "due": "2025-06-01", "principal_minor": 60_000, "interest_minor": 600, "superseded_on": "2025-03-20"},
        ],
        "prepay": {"on": "2025-03-20", "principal_minor": 180_000},
    },
    {
        # February instalment paid. On 1 March the remaining 400_000 is spread
        # over four instalments. The original March and April rows are superseded.
        "loan_id": "LN_RESTRUCTURED",
        "account_id": "A001",
        "product_id": "TERM_SME",
        "principal_minor": 600_000,
        "term_months": 3,
        "monthly_rate_bps": 100,
        "originated_on": "2025-01-15",
        "close_on": "2025-06-15",
        "schedule": [
            {"n": 1, "due": "2025-02-15", "principal_minor": 200_000, "interest_minor": 6_000, "paid_on": "2025-02-15"},
            {"n": 2, "due": "2025-03-15", "principal_minor": 200_000, "interest_minor": 4_000, "superseded_on": "2025-03-01"},
            {"n": 3, "due": "2025-04-15", "principal_minor": 200_000, "interest_minor": 2_000, "superseded_on": "2025-03-01"},
        ],
        "restructure": {
            "on": "2025-03-01",
            "principal_minor": 400_000,
            "term_months": 4,
            "monthly_rate_bps": 100,
            "schedule": [
                {"n": 1, "due": "2025-03-15", "principal_minor": 100_000, "interest_minor": 4_000, "paid_on": "2025-03-15"},
                {"n": 2, "due": "2025-04-15", "principal_minor": 100_000, "interest_minor": 3_000, "paid_on": "2025-04-15"},
                {"n": 3, "due": "2025-05-15", "principal_minor": 100_000, "interest_minor": 2_000, "paid_on": "2025-05-15"},
                {"n": 4, "due": "2025-06-15", "principal_minor": 100_000, "interest_minor": 1_000, "paid_on": "2025-06-15"},
            ],
        },
    },
    {
        # Same Salesforce account as LN_ON_TIME, second product. Draws and a
        # principal repayment. Bills are interest on the drawn balance.
        "loan_id": "LN_CREDIT_LINE_REVOLVING",
        "account_id": "A002",
        "product_id": "RCF_SME",
        "credit_limit_minor": 1_000_000,
        "monthly_rate_bps": 100,
        "originated_on": "2025-01-20",
        "draws": [
            {"on": "2025-02-01", "amount_minor": 400_000},
            {"on": "2025-03-10", "amount_minor": 250_000},
            {"on": "2025-05-02", "amount_minor": 100_000},
        ],
        "cash_repayments": [
            {"on": "2025-04-15", "principal_minor": 150_000, "interest_minor": 0},
        ],
        "schedule": [
            {"n": 1, "due": "2025-02-20", "principal_minor": 0, "interest_minor": 4_000, "paid_on": "2025-02-20"},
            {"n": 2, "due": "2025-03-20", "principal_minor": 0, "interest_minor": 6_500, "paid_on": "2025-03-20"},
            {"n": 3, "due": "2025-04-20", "principal_minor": 0, "interest_minor": 5_000, "paid_on": "2025-04-20"},
            {"n": 4, "due": "2025-05-20", "principal_minor": 0, "interest_minor": 6_000, "paid_on": "2025-05-20"},
            {"n": 5, "due": "2025-06-20", "principal_minor": 0, "interest_minor": 6_000, "paid_on": "2025-06-20"},
        ],
    },
    {
        # Value date 20 March, committed 4 April. Loaded in the next day's batch.
        "loan_id": "LN_LATE_POSTED",
        "account_id": "A004",
        "product_id": "TERM_SME",
        "principal_minor": 200_000,
        "term_months": 2,
        "monthly_rate_bps": 100,
        "originated_on": "2025-02-20",
        "close_on": "2025-04-20",
        "schedule": [
            {
                "n": 1,
                "due": "2025-03-20",
                "principal_minor": 100_000,
                "interest_minor": 2_000,
                "paid_on": "2025-03-20",
                "recorded_at": "2025-04-04T15:00:00Z",
            },
            {"n": 2, "due": "2025-04-20", "principal_minor": 100_000, "interest_minor": 1_000, "paid_on": "2025-04-20"},
        ],
    },
]


# Applications that never become a loan, so the enum is not only approvals.
EXTRA_APPLICATIONS = [
    {
        "application_id": "APP_DECLINED",
        "account_id": "A003",
        "product_id": "RCF_SME",
        "requested_amount_minor": 2_000_000,
        "term_months": None,
        "submitted_on": "2025-02-01",
        "decision": "declined",
        "decided_on": "2025-02-03",
    },
    {
        "application_id": "APP_WITHDRAWN",
        "account_id": "A006",
        "product_id": "TERM_SME",
        "requested_amount_minor": 120_000,
        "term_months": 6,
        "submitted_on": "2025-03-01",
        "decision": "withdrawn",
        "decided_on": "2025-03-04",
    },
]


GOLDEN_LOAN_IDS = (
    "LN_ON_TIME",
    "LN_LATE_15",
    "LN_DPD_30_CURED",
    "LN_DEFAULT_90",
    "LN_PREPAID",
    "LN_RESTRUCTURED",
    "LN_CREDIT_LINE_REVOLVING",
    "LN_LATE_POSTED",
)
