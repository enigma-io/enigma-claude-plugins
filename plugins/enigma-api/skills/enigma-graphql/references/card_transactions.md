# Card Transactions Reference

Card transactions are on both `Brand` and `OperatingLocation` entities. Brand-level includes ALL transactions across all locations. OL-level is per-location only.

## BrandCardTransaction Fields

| Field | Type | Description |
|---|---|---|
| `quantityType` | String | Metric type (see below) |
| `period` | String | `"12m"` (rolling 12-month) or `"1m"` (monthly) |
| `projectedQuantity` | Float | Projected/estimated total — **primary display value** |
| `platformBrandId` | UUID | Specific data platform UUID, or `null` for the **aggregate** |
| `periodStartDate` | Date | Start of the rolling measurement period |
| `periodEndDate` | Date | End of the rolling measurement period |

> **`rawQuantity` does NOT exist on `BrandCardTransaction`** (it's `OperatingLocationCardTransaction`-only) — querying it is HTTP 400. `rank` is a valid **filter** path (0 = most recent) but is not a returned scalar; do not select it.

## quantityType Values

| quantityType | Description | Availability |
|---|---|---|
| `card_revenue_amount` | Total card revenue in dollars | Brand + OL |
| `card_transactions_count` | Number of card transactions | Brand + OL |
| `card_revenue_yoy_growth` | Year-over-year revenue growth (percentage) | Brand + OL |
| `card_revenue_prior_period_growth` | Prior period growth (percentage) | Brand + OL |
| `card_customers_average_daily_count` | Average daily unique card customers | Brand + OL |
| `avg_transaction_size` | Average transaction amount in dollars | Brand + OL |
| `refunds_amount` | Total refund amount in dollars | Brand + OL |
| `card_not_present_revenue_amount` | Card-not-present revenue (online/phone) | **Brand only** — `period: "12m"` only, multi-period history available |
| `has_transactions` | `1` if active, `0` otherwise | **OL only** — always populated (never null) |

## Aggregate vs Per-Platform Records

For each metric and period, the API stores multiple records:
- **Per-platform** (`platformBrandId` = a UUID): data from one card data provider
- **Aggregate** (`platformBrandId` = null): total across ALL providers — **this is the headline number**

**ALWAYS filter for aggregate** at Brand level:
```json
{ "IS_NULL": ["platformBrandId"] }
```

Without this filter, revenue appears **2x-5x higher** due to double-counting (aggregate + per-platform records summed).

**At OL level**: `platformBrandId` does not exist — omit this filter entirely.

## Standard Filters

**Brand-level — most recent aggregate for a metric:**
```json
{
  "filter": { "AND": [
    { "EQ": ["period", "12m"] },
    { "EQ": ["quantityType", "card_revenue_amount"] },
    { "EQ": ["rank", 0] },
    { "IS_NULL": ["platformBrandId"] }
  ]}
}
```

**OL-level — most recent for a metric (no platformBrandId):**
```json
{
  "filter": { "AND": [
    { "EQ": ["period", "12m"] },
    { "EQ": ["quantityType", "card_revenue_amount"] },
    { "EQ": ["rank", 0] }
  ]}
}
```

## Brand vs OL Differences

| Aspect | Brand | Operating Location |
|---|---|---|
| `platformBrandId` filter | **Required** (IS_NULL for aggregate) | **Do NOT use** (field doesn't exist) |
| `period` values | `"12m"`, `"1m"` | `"12m"`, `"3m"`, `"1m"` (quarterly available) |
| `has_transactions` metric | Not available | Available (binary, never null) |
| `card_not_present_revenue_amount` | Available (`12m` only, multi-period history) | Not available |
| `rawQuantity` field | **Not present** (projectedQuantity only) | Present (rawQuantity + projectedQuantity) |
| `firstObservedDate` / `lastObservedDate` | Not available | Available (data coverage dates) |
| Null handling | N/A | `projectedQuantity`/`rawQuantity` may be null below compliance threshold |

## Temporal Ordering

Card-transaction records come back in `periodEndDate`-descending order, so:
- Latest snapshot: `first: 1`
- Latest 12 monthly/rolling periods: `first: 12`
- A specific historical period: `{ "EQ": ["periodEndDate", "2024-12-31"] }`

`{ "EQ": ["rank", 0] }` (most-recent) is also a valid filter and is interchangeable with `first: 1`. All metrics including `card_not_present_revenue_amount` carry multi-period history at `period: "12m"`.
