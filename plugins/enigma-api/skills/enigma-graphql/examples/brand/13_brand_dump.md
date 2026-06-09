# Data Engineering: Comprehensive Brand Dump

## User Intent

Fetch ALL available connections and scalar fields for a brand — a complete data dump for analysis.

## Key Concepts

- `search` returns `[SearchUnion]` — select with `__typename` + `... on Brand { }`, never `edges { node }` on `search` itself
- Every nested field is a Relay connection: `field(first: N) { edges { node { ... } } }` — always give `first`
- Includes `activities`, `isMarketables`, `locationDescriptions`, `revenueQualities` (often-overlooked connections)
- Brand-level card transactions always need `IS_NULL: ["platformBrandId"]` and have NO `rawQuantity` (only OL-level card transactions expose `rawQuantity`)
- `LegalEntity.types` node field is `legalEntityType` (not `type`); `Tin` fields are `tin`, `tinType`, `validity`
- Use the Pagination Template to fetch more of any connection

---

## Full Brand Dump Query

```graphql
query FullBrand($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      id
      names(first: 5) { edges { node { name } } }
      websites(first: 5) { edges { node { website domain } } }
      industries(first: 10) { edges { node { industryDesc industryCode industryType } } }
      revenueQualities(first: 5) { edges { node { issueReason issueSeverity issueDescription } } }
      isMarketables(first: 1) { edges { node { isMarketable } } }
      locationDescriptions(first: 5) { edges { node { locationDescription } } }
      activities(first: 5) { edges { node { activityType } } }
      cardTransactions(first: 1, conditions: { filter: { AND: [
        { EQ: ["period", "12m"] }
        { EQ: ["quantityType", "card_revenue_amount"] }
        { IS_NULL: ["platformBrandId"] }
      ] } }) {
        edges { node { projectedQuantity periodStartDate periodEndDate } }
      }
      legalEntities(first: 10) {
        edges {
          node {
            names(first: 1) { edges { node { name } } }
            types(first: 3) { edges { node { legalEntityType } } }
            tins(first: 3) { edges { node { tin tinType validity } } }
            registeredEntities(first: 1) { edges { node { name registeredEntityType formationYear } } }
            bankruptcies(first: 1) { edges { node { caseNumber chapterType filingDate } } }
          }
        }
      }
      operatingLocations(first: 10) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            names(first: 1) { edges { node { name } } }
            addresses(first: 1) { edges { node { fullAddress } } }
            operatingStatuses(first: 1) { edges { node { operatingStatus } } }
            phoneNumbers(first: 1) { edges { node { phoneNumber } } }
            cardTransactions(first: 1, conditions: { filter: { AND: [
              { EQ: ["period", "12m"] }
              { EQ: ["quantityType", "card_revenue_amount"] }
            ] } }) {
              edges { node { projectedQuantity rawQuantity periodEndDate } }
            }
            reviewSummaries(first: 1) { edges { node { reviewScoreAvg reviewCount } } }
          }
        }
      }
    }
  }
}
```

```json
{
  "searchInput": { "name": "Chipotle", "entityType": "BRAND", "conditions": { "limit": 1 } }
}
```

> Note: OL-level `cardTransactions` expose both `rawQuantity` and `projectedQuantity` and do NOT need the `platformBrandId` filter. Brand-level `cardTransactions` expose only `projectedQuantity` and REQUIRE `IS_NULL: ["platformBrandId"]`.

---

## Extending the Dump

Use the **Pagination Template** (`references/pagination_template.py`) to fetch more of any connection. For example, to get all operating locations:

1. Run the query above to get the first page
2. Check `operatingLocations.pageInfo.hasNextPage`
3. If true, re-query with `operatingLocations(first: 100, after: $cursor)`

### Additional Fields You Can Add

| Connection | Useful Fields |
|---|---|
| `operatingLocations → cardTransactions` | Per-location revenue: `rawQuantity`, `projectedQuantity` (no `platformBrandId` filter at OL level) |
| `operatingLocations → reviewSummaries` | `reviewScoreAvg`, `reviewCount`, `firstReviewDate`, `lastReviewDate` |
| `operatingLocations → roles` | Contacts: `jobTitle`, `jobFunction`, `managementLevel` |
| `legalEntities → registeredEntities` | `formationYear`, `registeredEntityType`, plus `registrations` |
| `legalEntities → bankruptcies` | `caseNumber`, `chapterType`, `filingDate`, `debtorName` |

---

## Common Mistakes to Avoid

1. **Forgetting `IS_NULL: ["platformBrandId"]`** on brand card transactions — revenue inflated 2x-5x
2. **Requesting `rawQuantity` on brand-level `cardTransactions`** — 400; only OL-level card transactions have it
3. **Using `type` on `LegalEntity.types`** — the field is `legalEntityType`
4. **Requesting `totalCount`** on connections — causes HTTP 400. Use `pageInfo { hasNextPage }` instead
5. **Querying `cardTransactions` without filters** — returns hundreds of records. Always filter by `period` and `quantityType` (and `platformBrandId` at brand level)
6. **Plain `names { name }`** — every nested field is a connection: `names(first: 1) { edges { node { name } } }`
