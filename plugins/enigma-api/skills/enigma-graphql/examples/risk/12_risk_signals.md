# Risk Signals: Revenue Quality, Transactions, Operating Status

## User Intent

Assess risk for a brand by checking revenue quality issues, transaction data, and location operating statuses.

## Key Concepts

- `revenueQualities` connection has `issueReason`, `issueSeverity`, `issueDescription`
- Card transactions: use separate conditions for revenue amount vs transaction count
- Count active vs closed locations by paginating `operatingLocations` and grouping by `operatingStatus`
- Pick the aggregate record (`platformBrandId` = null) for headline numbers

---

## Risk Signals Query

```graphql
query RiskBrand($searchInput: SearchInput!, $revCond: ConnectionConditions!, $txnCond: ConnectionConditions!) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      names { edges { node { name } } }
      revenueQualities { edges { node { issueReason issueSeverity issueDescription } } }
      revenue: cardTransactions(first: 1, conditions: $revCond) {
        edges { node { projectedQuantity rawQuantity periodStartDate periodEndDate } }
      }
      transactions: cardTransactions(first: 1, conditions: $txnCond) {
        edges { node { projectedQuantity } }
      }
      operatingLocations(first: 100) {
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
  "searchInput": { "name": "Pizza Hut", "entityType": "BRAND" },
  "revCond": { "filter": { "AND": [{ "EQ": ["period", "12m"] }, { "EQ": ["quantityType", "card_revenue_amount"] }, { "EQ": ["rank", 0] }, { "IS_NULL": ["platformBrandId"] }] } },
  "txnCond": { "filter": { "AND": [{ "EQ": ["period", "12m"] }, { "EQ": ["quantityType", "card_transactions_count"] }, { "EQ": ["rank", 0] }, { "IS_NULL": ["platformBrandId"] }] } }
}
```

---

## Interpreting Results

### Revenue Quality

`revenueQualities` flags data quality issues. Empty = no known issues. Non-empty = review each:
- `issueSeverity`: how serious (e.g., "warning", "critical")
- `issueReason`: machine-readable reason code
- `issueDescription`: human-readable explanation

### Active vs Closed Locations

Paginate `operatingLocations` (max 3 pages), then count by status in Python:

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

For location-level risk, use `OPERATING_LOCATION` search:

```graphql
query LocationCheck($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      id
      names { edges { node { name } } }
      addresses { edges { node { fullAddress } } }
      phoneNumbers { edges { node { phoneNumber } } }
      operatingStatuses { edges { node { operatingStatus } } }
      locationTypes { edges { node { locationType } } }
      reviewSummaries { edges { node { reviewScoreAvg reviewCount firstReviewDate lastReviewDate } } }
    }
  }
}
```

```json
{
  "searchInput": {
    "name": "Walmart",
    "entityType": "OPERATING_LOCATION",
    "address": { "street1": "702 SW 8th St", "city": "Bentonville", "state": "AR" }
  }
}
```

---

## Common Mistakes to Avoid

1. **Missing `IS_NULL: ["platformBrandId"]`** — without this, revenue is inflated 2x-5x
2. **Summing all `cardTransactions` records** — only use the aggregate record (filtered by `IS_NULL`)
3. **Not paginating locations** — first page only shows up to 100; use pagination template for full count
