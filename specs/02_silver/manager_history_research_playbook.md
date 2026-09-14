# Spec: Manager History Research Playbook (human process, not code)

## Purpose
Produce `data/manager_history_seed.csv` — the input to `load_manager_history` — using only sources that don't violate any provider's terms of use.

## Single Responsibility
This document specs a manual research procedure, not a piece of code. It exists so the process is reproducible and auditable, not dependent on memory of a conversation.

## Procedure
1. **Screen all 20 trusts** (~2-3 min each): search `"<trust name>" change of investment manager`, or check `investegate.co.uk/company/<TICKER>` for any headline containing "Change of Investment Manager," "Appointment of Investment Manager," or "Portfolio Manager."
2. **Select 6-8 trusts** whose screen turned up a real hit, as the deep-dive set. Two already confirmed from prior research: Scottish Mortgage (James Anderson → Tom Slater, 2022) and Alliance Trust (self-managed → Willis Towers Watson, 2017).
3. **For each deep-dive trust:** read the actual announcement on Investegate for the effective date (often different from the announcement date); cross-check the manager's name/spelling against the trust's AIC profile page; if Investegate doesn't reach far enough back, check the FCA National Storage Mechanism (`data.fca.org.uk`) as a backup.
4. **For the remaining trusts:** just record current manager + management group from their AIC profile page — one lookup, no announcement search needed.
5. **Never automate any of this against AIC or Trustnet** — both explicitly prohibit scraping in their Terms of Use. This step is manual by requirement, not by convenience.

## Output format
See `load_manager_history.md` for the exact CSV schema this procedure must produce.

## Open questions
None — procedure is settled; execution (actually doing the research) is still pending.
