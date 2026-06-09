# Revenue Examples

For card transaction field reference, see `references/card_transactions.md`.

## Key Concepts

- Brand-level card transactions ALWAYS require `IS_NULL: ["platformBrandId"]`
- Brand-level nodes expose `projectedQuantity` only — there is **no** `rawQuantity` at the Brand level
- OL-level card transactions expose BOTH `rawQuantity` and `projectedQuantity`, and do NOT use `platformBrandId` (field doesn't exist)
- Franchise/chain warning: brand-level revenue = entire chain, not single location
- Records come back `periodEndDate`-descending; `first: 1` = latest snapshot, `first: 12` = last 12 periods
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
        edges { node { projectedQuantity periodStartDate periodEndDate } }
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
  "searchInput": { "name": "Sweetgreen", "entityType": "BRAND", "conditions": { "limit": 1 } },
  "revCond": {
    "filter": { "AND": [
      { "EQ": ["period", "12m"] },
      { "EQ": ["quantityType", "card_revenue_amount"] },
      { "IS_NULL": ["platformBrandId"] }
    ]}
  },
  "txnCond": {
    "filter": { "AND": [
      { "EQ": ["period", "12m"] },
      { "EQ": ["quantityType", "card_transactions_count"] },
      { "IS_NULL": ["platformBrandId"] }
    ]}
  }
}
```

Live result (Sweetgreen, trailing 12m): `projectedQuantity` ≈ `480,460,870` revenue, `20,445,869` transactions.

> Note: there is **no** `rawQuantity` field at the Brand level — requesting it returns a validation error. Use `projectedQuantity` (the estimated total).

---

## Brand Revenue Time Series (for charts)

Monthly revenue over time — use `period: "1m"`:

```graphql
query BrandRevenueSeries($searchInput: SearchInput!, $seriesCond: ConnectionConditions!) {
  search(searchInput: $searchInput) {
    ... on Brand {
      names(first: 1) { edges { node { name } } }
      series: cardTransactions(first: 60, conditions: $seriesCond) {
        edges { node { projectedQuantity periodStartDate periodEndDate } }
      }
    }
  }
}
```

```json
{
  "searchInput": { "name": "Sweetgreen", "entityType": "BRAND", "conditions": { "limit": 1 } },
  "seriesCond": {
    "filter": { "AND": [
      { "EQ": ["period", "1m"] },
      { "EQ": ["quantityType", "card_revenue_amount"] },
      { "IS_NULL": ["platformBrandId"] }
    ]}
  }
}
```

Use `first: 60` for up to 5 years of monthly data. Records are newest-first; each has `periodStartDate`/`periodEndDate` for the x-axis. (Sweetgreen Feb 2026 ≈ `34,515,305`.)

---

## Operating Location Revenue

OPERATING_LOCATION searches take an `address` with `street1` (an `AddressInput` field) for reliable hits. Note the output address fields are `streetAddress1`/`city`/`state`/`zip`/`fullAddress`.

```graphql
query LocationRevenue($searchInput: SearchInput!, $revCond: ConnectionConditions!, $txnCond: ConnectionConditions!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      id
      names(first: 1) { edges { node { name } } }
      addresses(first: 1) { edges { node { fullAddress city state zip } } }
      operatingStatuses(first: 1) { edges { node { operatingStatus } } }
      revenue: cardTransactions(first: 1, conditions: $revCond) {
        edges { node { projectedQuantity rawQuantity periodStartDate periodEndDate } }
      }
      transactions: cardTransactions(first: 1, conditions: $txnCond) {
        edges { node { projectedQuantity rawQuantity } }
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
    "name": "Starbucks",
    "entityType": "OPERATING_LOCATION",
    "address": { "street1": "1912 Pike Pl", "city": "Seattle", "state": "WA" }
  },
  "revCond": { "filter": { "AND": [{ "EQ": ["period", "12m"] }, { "EQ": ["quantityType", "card_revenue_amount"] }] } },
  "txnCond": { "filter": { "AND": [{ "EQ": ["period", "12m"] }, { "EQ": ["quantityType", "card_transactions_count"] }] } }
}
```

Live result (Starbucks, 1912 Pike Pl, Seattle WA, trailing 12m): `projectedQuantity` ≈ `166,927`, `rawQuantity` ≈ `51,542`. At the OL level both fields are present.

---

## Per-Location Revenue from Brand Search

Revenue for each location of a brand (e.g., "revenue for each Chipotle in WA"):

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
  "searchInput": { "name": "Chipotle", "entityType": "BRAND", "conditions": { "limit": 1 } },
  "locConditions": { "filter": { "AND": [{ "EQ": ["addresses.state", "WA"] }, { "EQ": ["operatingStatuses.operatingStatus", "Open"] }] } },
  "revCond": { "filter": { "AND": [{ "EQ": ["period", "12m"] }, { "EQ": ["quantityType", "card_revenue_amount"] }] } }
}
```

Note: `operatingLocations(...)` resolves to OL nodes, so the nested `cardTransactions` is OL-level — both `projectedQuantity` and `rawQuantity` are valid here, and you must NOT filter `platformBrandId`. Live result (first Chipotle in WA, 1827 15th Ave W, Seattle): `projectedQuantity` ≈ `2,329,752`.

**Keep `operatingLocations(first: 5)` with nested card data.** Higher counts risk 504 timeouts.

---

## OL Time Series (Monthly/Quarterly)

```graphql
query LocationRevenueSeries($searchInput: SearchInput!, $seriesCond: ConnectionConditions!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      names(first: 1) { edges { node { name } } }
      series: cardTransactions(first: 24, conditions: $seriesCond) {
        edges { node { projectedQuantity rawQuantity periodStartDate periodEndDate } }
      }
    }
  }
}
```

```json
{
  "searchInput": {
    "name": "Starbucks",
    "entityType": "OPERATING_LOCATION",
    "address": { "street1": "1912 Pike Pl", "city": "Seattle", "state": "WA" }
  },
  "seriesCond": { "filter": { "AND": [{ "EQ": ["period", "1m"] }, { "EQ": ["quantityType", "card_revenue_amount"] }] } }
}
```

Use `first: 24` for 2 years of monthly data. `period: "3m"` is available at the OL level (e.g., quarterly trend) in addition to `"1m"` and `"12m"`.

---

## Common Mistakes to Avoid

1. **Missing `IS_NULL: ["platformBrandId"]`** on brand card transactions — revenue 2x-5x inflated
2. **Requesting `rawQuantity` at the Brand level** — that field exists only on OL nodes; Brand has `projectedQuantity` only
3. **Using `platformBrandId` filter at OL level** — field doesn't exist there
4. **Confusing brand vs location revenue** for franchises — brand = entire chain
5. **Requesting `card_not_present_revenue_amount` at the OL level** — Brand-only metric (full `12m` multi-period history available)
