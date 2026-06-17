# Executive Semantic Layer Interview Deck — review copy

This file is the slide-by-slide text version of the presentation so you can review the narrative without opening the PPTX.

## Slide 1 — One trusted ARR answer, ready for humans and AI
A semantic layer on top of the existing data platform
Use ARR as the end-to-end example

## Slide 2 — Current State
Snowflake, dbt, Fivetran, Python ingestion, Metabase, reverse ETL.
The platform is strong. The missing piece is a shared meaning layer.

## Slide 3 — The Missing Layer
Sources → dbt models → marts → semantic layer → Metabase / AI agents / reverse ETL

## Slide 4 — Why This Matters
If metric definitions stay trapped in SQL, every dashboard, report, and AI agent can give a different answer.
That creates business risk, not just technical debt.

## Slide 5 — My Recommendation
Keep dbt as the governed source of truth.
Publish the certified metric through Snowflake for easy consumption.
One definition, two ways to serve it.

## Slide 6 — One Metric End-to-End
Raw seed → Stage → Intermediate → Mart → Semantic definition → Metabase → AI agent

## Slide 7 — Ownership Creates Trust
RevOps owns meaning.
Data owns implementation.
Certification is shared and documented.

## Slide 8 — Trust Before AI
Define the metric → validate the data → reconcile to finance → certify it → publish it.
AI reads the certified layer, never a parallel truth.

## Slide 9 — ARR Example
Salesforce = booked ARR
JustOn = recognized ARR → one certified ARR with traceable exceptions

## Slide 10 — AI Guardrails
Certified metrics only.
Approved dimensions, synonyms, lineage, access controls, and verified queries.

## Slide 11 — First 90 Days
Month 1: certify ARR and lock ownership
Month 2: extend to GTM metrics
Month 3: add product metrics and AI-ready access

## Slide 12 — Success Criteria
Metabase, board reporting, Salesforce, and AI should all return the same ARR.
If the answer changes by surface, trust has not yet been established.

## Slide 13 — Closing Thought
The goal is not another abstraction.
The goal is a shared business vocabulary that humans trust and AI can safely use.
