# Risk Signals: Revenue Quality, Transactions, Operating Status

## User Intent

Assess risk for a brand by checking revenue quality issues, transaction data, and location operating statuses.

## Key Concepts

- `revenueQualities` connection has `issueReason`, `issueSeverity`, `issueDescription`
- Every nested field is a Relay connection — always request `(first: N) { edges { node { ... } } }`
- Card transactions: use separate conditions for revenue amount vs transaction count
- Brand card transactions are `projectedQuantity` only and REQUIRE `IS_NULL: ["platformBrandId"]`
- Count active vs closed locations by paginating `operatingLocations` and grouping by `operatingStatus`
- Pick the aggregate record (`platformBrandId` = null) for headline numbers

---

## Risk Signals Query

```graphql
query RiskBrand($searchInput: SearchInput!, $revCond: ConnectionConditions!, $txnCond: ConnectionConditions!) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      names(first: 1) { edges { node { name } } }
      revenueQualities(first: 10) { edges { node { issueReason issueSeverity issueDescription } } }
      revenue: cardTransactions(first: 1, conditions: $revCond) {
        edges { node { projectedQuantity periodStartDate periodEndDate } }
      }
      transactions: cardTransactions(first: 1, conditions: $txnCond) {
        edges { node { projectedQuantity } }
      }
      operatingLocations(first: 50) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            operatingStatuses(first: 1) { edges { node { operatingStatus } } }
            addresses(first: 1) { edges { node { fullAddress } } }
          }
        }
      }
    }
  }
}
```

```json
{
  "searchInput": { "name": "Pizza Hut", "entityType": "BRAND", "conditions": { "limit": 1 } },
  "revCond": { "filter": { "AND": [{ "EQ": ["period", "12m"] }, { "EQ": ["quantityType", "card_revenue_amount"] }, { "IS_NULL": ["platformBrandId"] }] } },
  "txnCond": { "filter": { "AND": [{ "EQ": ["period", "12m"] }, { "EQ": ["quantityType", "card_transactions_count"] }, { "IS_NULL": ["platformBrandId"] }] } }
}
```

Live result (Pizza Hut, trailing 12m): revenue `projectedQuantity` ≈ `3,112,627,992`. `revenueQualities` was empty here (no flagged issues) — see below for how to interpret a non-empty result.

> Note: `revenue`/`transactions` request `projectedQuantity` only. There is no `rawQuantity` at the Brand level.

---

## Interpreting Results

### Revenue Quality

`revenueQualities` flags data quality issues. Empty = no known issues. Non-empty = review each:
- `issueSeverity`: how serious (e.g., "warning", "critical")
- `issueReason`: machine-readable reason code
- `issueDescription`: human-readable explanation

### Active vs Closed Locations

Paginate `operatingLocations` (use `pageInfo.endCursor` as the next `after`), then count by status in Python:

```python
statuses = {}
for edge in all_edges:
    status = edge['node']['operatingStatuses']['edges'][0]['node']['operatingStatus']
    statuses[status] = statuses.get(status, 0) + 1
# e.g., {'Open': 1543, 'Closed': 426}
```

### Headline Numbers

Pick the aggregate record (`platformBrandId` = null via the `IS_NULL` filter) for headline revenue and transaction count. Read `projectedQuantity` directly — it's the estimated total.

---

## Single Location Risk Check

For location-level risk, use `OPERATING_LOCATION` search with an `address` (the `street1` AddressInput field aids resolution). At the OL level card transactions expose both `rawQuantity` and `projectedQuantity` and do NOT take `platformBrandId`.

```graphql
query LocationCheck($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      id
      names(first: 1) { edges { node { name } } }
      addresses(first: 1) { edges { node { fullAddress } } }
      phoneNumbers(first: 1) { edges { node { phoneNumber } } }
      operatingStatuses(first: 1) { edges { node { operatingStatus } } }
      locationTypes(first: 3) { edges { node { locationType } } }
      reviewSummaries(first: 1) { edges { node { reviewScoreAvg reviewCount firstReviewDate lastReviewDate } } }
      cardTransactions(first: 1, conditions: { filter: { AND: [{ EQ: ["period", "12m"] }, { EQ: ["quantityType", "card_revenue_amount"] }] } }) {
        edges { node { projectedQuantity rawQuantity } }
      }
    }
  }
}
```

```json
{
  "searchInput": {
    "name": "Walmart",
    "entityType": "OPERATING_LOCATION",
    "address": { "street1": "406 S Walton Blvd", "city": "Bentonville", "state": "AR" }
  }
}
```

Live result (Walmart Supercenter, 406 S Walton Blvd, Bentonville AR): status `Open`, `reviewScoreAvg` "4.10", `reviewCount` "6001".

---

## Common Mistakes to Avoid

1. **Missing `IS_NULL: ["platformBrandId"]`** on brand card transactions — revenue inflated 2x-5x
2. **Requesting `rawQuantity` at the Brand level** — it exists only on OL nodes
3. **Bare connections** (`names { ... }` without `(first: N) { edges { node } }`) — every nested field is a Relay connection
4. **Summing all `cardTransactions` records** — at Brand level use the aggregate record (filtered by `IS_NULL`)
5. **Not paginating locations** — first page is capped; use `pageInfo.endCursor` for full counts
