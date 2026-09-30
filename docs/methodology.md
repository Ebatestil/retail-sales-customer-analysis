# Methodology and KPI definitions

## Business problem

A retail manager needs to understand sales performance, customer purchasing patterns, product and store contributions, and returns. The analyst must first decide which measures the available records support. The portfolio demonstrates this process from source profiling through business interpretation.

### Questions and decisions

| Question | Analysis | Decision supported |
|---|---|---|
| How are sales changing? | Monthly sales and full-year growth | Establish a baseline for planning |
| Which categories and products contribute most? | Sales share, units, returned-line rate | Identify candidates for assortment review |
| Which stores perform well? | Sales, sales-backed orders, AOV, returns | Select stores for operational investigation |
| Who purchases repeatedly and contributes most? | Observed sales, frequency, recency, top-decile share | Define groups for a retention experiment |
| Where do returns concentrate? | Distinct returned items and orders, exposure, refund exceptions | Prioritize return-policy and data checks |
| Do promotions explain prices and payments? | Reconciliation scenarios and promotion summaries | Determine whether discount measures are usable |
| What can we say about shipping? | Distribution of recorded status labels | Identify what operational data to request |

## Sources and scope

The source is the 12 CSVs in `data/`. The original README says Kaggle but supplies no dataset URL, author, license, currency, or generator documentation. Those details remain unverified. No external statistics are used. Currency is expressed as **currency units (CU)**. Indian city names do not establish the currency. Anonymous `Cat_1` labels are retained, not replaced with invented merchandise names.

The source profile and SHA-256 manifest in `outputs/quality/` identify the exact analyzed inputs. The observed period is 2020-01-01 to 2024-01-01. Headline totals include all records. Full-year comparisons use 2020–2023; January 2024 is partial. Coverage means dates observed in this extract, not certification that every source-system transaction is present.

## Grain and join rules

- Orders: one row per `order_id`. An order header does not prove an item purchase exists.
- Order items: one row per `order_item_id`. Quantity may exceed one; an item row is not a unit.
- Payments and shipments: separate facts linked by `order_id`. Both have one record per order in this snapshot; the preparation aggregates payments defensively.
- Returns: one row per `return_id`. Several valid IDs may reference the same item. Sum refunds and count returns per item before joining to items. Then aggregate items and payments per order before joining to orders.
- Dimension joins are validated as many-to-one. Never join raw items, payments, shipments, and returns together and then sum amounts.

## Data quality and preparation decisions

1. Check every column for null/blank values and every primary key for duplicates. Validate all 11 foreign-key relationships, numeric domains, date parsing, category variants, and univariate IQR extremes. Structural failures stop the build.
2. Trim text, parse dates, normalize shipment status case, and derive item sales and explicit flags. The transformation log records how many source values changed. No raw CSV is overwritten.
3. Retain order headers without items. Their derived observed item sales are zero and `has_items=0` records the absence. This does not assert their true business value is zero.
4. Retain orders before signup. Their sales remain in the descriptive analysis, but signup-based cohorts, customer tenure, and acquisition conversion are withheld.
5. Keep distinct return IDs, even if an item repeats. Do not cap excessive refunds or erase their evidence. An adjustment requires a documented source correction.
6. Keep transaction prices as recorded. Catalog prices have no history, and promotions lack effective dates or documented units. Do not subtract discounts a second time. The percentage-discount calculation is a diagnostic scenario only.
7. Treat high values as review candidates, not automatic errors. An IQR check cannot establish business validity. Narrow numeric ranges and near-zero correlations are consistent with generated data but do not prove its provenance.

## KPI dictionary

| Metric | Definition and population |
|---|---|
| Recorded item sales | Sum of `qty × order_items.price` across all item rows. Assumes price is a unit price. Analytical sales proxy; pre/post-discount and tax treatment are unknown. |
| Order headers | Distinct order IDs in orders, including headers with no items. |
| Sales-backed orders | Distinct orders with at least one valid item row. |
| Sales-backed AOV | Recorded item sales / sales-backed orders. Primary AOV. |
| Sales per order header | Recorded item sales / all order headers. Separate sensitivity measure. |
| Ordering customers | Distinct customer IDs in order headers. |
| Sales-backed customers | Distinct customers with at least one item-backed order. |
| Items / units | Items count item rows; units sum quantities. |
| Returned-item rate | Distinct item IDs with at least one return / all item rows. Not a unit return rate. |
| Returned-order rate | Distinct orders with at least one returned item / sales-backed orders. |
| Repeat-buyer rate | Customers with at least two sales-backed orders / sales-backed customers, over the full observed period. Not retention or loyalty. |
| Sales per customer | Recorded item sales / sales-backed customers. Not customer lifetime value. |
| Recency | Days from the last sales-backed order to 2024-01-02, the day after the last observed order. Customers without one have missing recency. |
| Top customer decile | Top `ceil(0.10 × sales-backed customers)` by recorded sales, with customer ID breaking ties. Includes the entire historical window. |
| Payments / refunds | Sums of their own recorded amounts. Refunds inherit the original order date for grouping because return dates are absent. |
| Sales less recorded refunds | Arithmetic scenario only; not verified net revenue. |
| Promotion discount | Raw order-weighted average of the `discount` field. Unit and realization unknown, so no confirmed average discount KPI. |
| Late-label share | Shipments labeled `late` / all shipments. No claim about SLA compliance without event and promised dates. |

## Limitations that change interpretation

- Payments fail to reconcile with item sales. An illustrative percentage-discount scenario also fails. Missing tax/shipping fees or alternative price semantics cannot be resolved from these fields.
- There are no cost-of-goods data, transaction-level operating expenses, payment methods, return reasons/quantities/dates, shipment timestamps, or promised-delivery dates. Profit/margin, method analysis, unit return rate, refund timing, return causes, and delivery duration cannot be calculated.
- Every order references a promotion, so there is no unpromoted control. Descriptive differences do not establish incremental promotion lift.
- Store revenue cannot establish efficiency without store size, opening dates, traffic, and costs. Employee salaries lack a defined payment period and must not be treated as COGS.
- Annual repeat rates are not inferred from a four-year repeat-buyer count. Customer segments and rankings are descriptive. Small product samples and multiple comparisons can exaggerate apparent return problems.
- Future forecasts, causal claims, and precise profit-improvement promises are deliberately withheld because the source does not support them.

## Reproduction and verification

Run `python scripts/analyze.py`, then `python scripts/build_report.py` from the project root after installing `requirements.txt`. The analysis uses pandas and executes the shared preparation and business SQL against a generated SQLite database. It verifies fact grain, rollup totals, distinct return counts, and independent SQL sales/order/refund totals.

The new SQL uses syntax shared by MySQL 8+ and SQLite. MySQL execution has not been verified in a running MySQL server. The original exploration script retains its MySQL database selection. The generated database is disposable and ignored by Git. Original exploration notes are preserved as a historical record; use the final report for revised definitions.
