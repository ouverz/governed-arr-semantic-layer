I built a small ARR Semantic Layer Lab to answer a question I think a lot of RevOps and data teams will run into soon:

**Can we define one ARR number that Finance trusts, RevOps can explain, and AI can safely reuse?**

The project goes deep on one metric — **Ending ARR** — instead of spreading across too many surfaces.

What it includes:
- synthetic Salesforce-style data
- staging → intermediate → marts flow
- a certified month-end ARR fact
- ARR movement logic
- dbt semantic models
- model contracts, singular tests, and unit tests
- a governed path for BI and AI consumption

A few things I learned:
- ARR is not just a sum; it is a contract.
- Effective dates matter more than current status.
- If you do not certify the metric once, every downstream tool will reinvent it.
- AI is only useful here if it reads certified meaning, not raw ambiguity.

If I were to describe the project in one sentence: it is intentionally narrow, but deep — one metric, one contract, one governed path.

I also made a visual case-study page because the architecture tells the story better when you can see the flow:
- metric contract
- proof stack
- month-end ARR trend
- Snowflake validation path

If you want the repo or the architecture notes, I’m happy to share.
