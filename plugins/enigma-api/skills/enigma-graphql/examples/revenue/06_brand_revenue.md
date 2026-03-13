# Revenue Examples

For card transaction field reference, see `references/card_transactions.md`.

## Key Concepts

- Brand-level card transactions ALWAYS require `IS_NULL: ["platformBrandId"]`
- OL-level card transactions do NOT use `platformBrandId` (field doesn't exist)
- Franchise/chain warning: brand-level revenue = entire chain, not single location
- For 2+ metrics, use explicit `periodEndDate` instead of `rank=0` for temporal consistency
- `has_transactions` (OL only) is the only metric guaranteed non-null

---

## Brand Revenue

**Chain warning**: For franchises/chains, this represents the **entire chain**.

```graphql
query BrandRevenue($searchInput: SearchInput!, $revCond: ConnectionConditions!, $txnCond: ConnectionConditions!) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      names(first: 1) { edges { node { name } } }
      revenue: cardTransactions(first: 1, conditions: $revCond) {
        edges { node { projectedQuantity rawQuantity periodStartDate periodEndDate } }
      }
      transactions: cardTransactions(first: 1, conditions: $txnCond) {
        edges { node { projectedQuantity } }
      }
    }
  }
}
```

```json
{
  "searchInput": { "name": "Tacombi", "entityType": "BRAND", "conditions": { "limit": 1 } },
  "revCond": {
    "filter": { "AND": [
      { "EQ": ["period", "12m"] },
      { "EQ": ["quantityType", "card_revenue_amount"] },
      { "EQ": ["rank", 0] },
      { "IS_NULL": ["platformBrandId"] }
    ]}
  },
  "txnCond": {
    "filter": { "AND": [
      { "EQ": ["period", "12m"] },
      { "EQ": ["quantityType", "card_transactions_count"] },
      { "EQ": ["rank", 0] },
      { "IS_NULL": ["platformBrandId"] }
    ]}
  }
}
```

---

## Brand Revenue Time Series (for charts)

Monthly revenue over time — use `period: "1m"` without rank filter:

```json
{
  "filter": { "AND": [
    { "EQ": ["period", "1m"] },
    { "EQ": ["quantityType", "card_revenue_amount"] },
    { "IS_NULL": ["platformBrandId"] }
  ]}
}
```

Use `first: 60` for 5 years of monthly data. Each record has `periodStartDate`/`periodEndDate` for the x-axis.

---

## Operating Location Revenue

**`street1` required** for OPERATING_LOCATION searches.

```graphql
query LocationRevenue($searchInput: SearchInput!, $revCond: ConnectionConditions!, $txnCond: ConnectionConditions!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      id
      names(first: 1) { edges { node { name } } }
      addresses(first: 1) { edges { node { fullAddress city state zip } } }
      operatingStatuses(first: 1) { edges { node { operatingStatus } } }
      revenue: cardTransactions(first: 1, conditions: $revCond) {
        edges { node { projectedQuantity rawQuantity periodStartDate periodEndDate firstObservedDate lastObservedDate } }
      }
      transactions: cardTransactions(first: 1, conditions: $txnCond) {
        edges { node { projectedQuantity } }
      }
      hasTransactions: cardTransactions(first: 1, conditions: { filter: { AND: [{ EQ: ["period", "12m"] }, { EQ: ["quantityType", "has_transactions"] }] } }) {
        edges { node { projectedQuantity } }
      }
    }
  }
}
```

```json
{
  "searchInput": {
    "name": "Tacombi",
    "entityType": "OPERATING_LOCATION",
    "address": { "street1": "255 Church St", "city": "New York", "state": "NY" }
  },
  "revCond": { "filter": { "AND": [{ "EQ": ["period", "12m"] }, { "EQ": ["quantityType", "card_revenue_amount"] }, { "EQ": ["rank", 0] }] } },
  "txnCond": { "filter": { "AND": [{ "EQ": ["period", "12m"] }, { "EQ": ["quantityType", "card_transactions_count"] }, { "EQ": ["rank", 0] }] } }
}
```

---

## Per-Location Revenue from Brand Search

Revenue for each location of a brand (e.g., "revenue for each Tacombi in NY"):

```graphql
query BrandLocationRevenue($searchInput: SearchInput!, $locConditions: ConnectionConditions, $revCond: ConnectionConditions!) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      names(first: 1) { edges { node { name } } }
      operatingLocations(first: 5, conditions: $locConditions) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            names(first: 1) { edges { node { name } } }
            addresses(first: 1) { edges { node { fullAddress state city zip } } }
            operatingStatuses(first: 1) { edges { node { operatingStatus } } }
            revenue: cardTransactions(first: 1, conditions: $revCond) {
              edges { node { projectedQuantity rawQuantity periodStartDate periodEndDate } }
            }
          }
        }
      }
    }
  }
}
```

```json
{
  "searchInput": { "name": "Tacombi", "entityType": "BRAND", "conditions": { "limit": 1 } },
  "locConditions": { "filter": { "AND": [{ "EQ": ["addresses.state", "NY"] }, { "EQ": ["operatingStatuses.operatingStatus", "Open"] }] } },
  "revCond": { "filter": { "AND": [{ "EQ": ["period", "12m"] }, { "EQ": ["quantityType", "card_revenue_amount"] }, { "EQ": ["rank", 0] }] } }
}
```

**Keep `operatingLocations(first: 5)` with nested card data.** Higher counts risk 504 timeouts.

---

## OL Time Series (Monthly/Quarterly)

```json
{
  "filter": { "AND": [{ "EQ": ["period", "1m"] }, { "EQ": ["quantityType", "card_revenue_amount"] }] }
}
```

Use `first: 24` for 2 years of monthly data. `period: "3m"` available at OL level only (not Brand).

---

## Common Mistakes to Avoid

1. **Missing `IS_NULL: ["platformBrandId"]`** on brand card transactions — revenue 2x-5x inflated
2. **Using `platformBrandId` filter at OL level** — field doesn't exist
3. **Confusing brand vs location revenue** for franchises — brand = entire chain
4. **Requesting `card_not_present_revenue_amount`** for historical dates — only 1-3 months available, Brand-level only
5. **Using `rank=0` with multiple metrics** — use explicit `periodEndDate` for temporal consistency
