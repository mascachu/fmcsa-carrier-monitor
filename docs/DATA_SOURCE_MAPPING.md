# FMCSA Source Mapping Notes

## Official daily-difference feeds configured

The official FMCSA Open Data Program lists these modern MOTUS daily-difference datasets:

| Source | Dataset ID | Prototype use |
|---|---|---|
| Motus Carrier | `nakq-58th` | Current authority/carrier record changes; fields include `USDOT_NUMBER`, `DOCKET_NUMBER`, `OP_AUTH_TYPE`, `OP_AUTH_STATUS`, `BIPD_FILE`, `CARGO_FILE`, `BOND_FILE` and related census fields. |
| Motus InsHist | `xe5s-wca7` | Insurance cancellation/replacement/history; key fields include `FILING_STATUS_REASON`, `POLICY_NO`, `CANCL_EFFECTIVE_DATE`, `INSURANCE_COMPANY_NAME`, USDOT and docket. |
| Motus AuthHist | `dm5j-zc6c` | Authority history; fields include `OP_AUTH_TYPE`, `OP_AUTH_STATUS`, `REASON`, `STATUS_CHANGE_DATE`, USDOT and docket. |
| Motus Insur | `x96h-evps` | Daily active/pending insurance-policy adjustments. |
| Motus RevokeSuspend | `e67p-xyd5` | Daily suspension/revocation action feed. |

API URL shape:

`https://data.transportation.gov/resource/{dataset-id}.json?$limit=50000&$offset=0&$order=:id`

The code pages through the current public feed. An optional Socrata app token can be configured for rate-limit control. Before production, re-check the live data dictionary for every field used by `row_identifiers()` and `event_type_and_summary()`; source schemas can change.

## Event handling rules in the prototype

- **InsHist:** the source's filing-status reason is mapped to cancellation, replacement, transfer, or name-change event types. The feed concerns a previous policy; it should not be treated as proof that a replacement policy is active.
- **AuthHist:** a new history row becomes an authority status change event.
- **RevokeSuspend:** a new matching row becomes a high-severity suspension/revocation event.
- **Carrier / Insur:** a first-seen or changed daily-difference row becomes a record-change event. This initial heuristic should be narrowed to the client-approved monitored fields after test rows are reviewed.
- **Blank strings:** FMCSA says modern daily-difference feeds can use blank strings to signal downstream field drops/deletions. The parser preserves blanks so `old` vs `new` comparisons can detect them; it does not interpret all blanks as a cancellation.
- **Multiple dockets per USDOT:** the database stores one company plus one-or-more normalized identifiers, and source snapshots are keyed by dataset-specific row identity, not only USDOT.

## Required validation before production

1. Review the current attached MOTUS data dictionary PDF for each feed.
2. Validate whether the daily delta endpoint represents all important field changes, and define which events should be actionable.
3. Run against synthetic/test rows and compare a small set of results with FMCSA Licensing & Insurance records.
4. Verify source freshness and counts daily; if a feed is unexpectedly empty or stale, flag the run rather than assuming there were no changes.
5. Establish a safe initial-state/baseline process before customer notifications are enabled.
