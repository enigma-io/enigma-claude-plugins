# Data Engineering: Comprehensive Brand Dump

## User Intent

Fetch ALL available connections and scalar fields for a brand — a complete data dump for analysis.

## Key Concepts

- Includes `activities`, `isMarketables`, `locationDescriptions` (often overlooked scalar connections)
- Use the Pagination Template to fetch more of any connection
- Brand-level card transactions always need `IS_NULL: ["platformBrandId"]`

---

## Full Brand Dump Query

```graphql
query FullBrand($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      names { edges { node { name } } }
      websites { edges { node { website domain } } }
      industries { edges { node { industryDesc industryCode industryType } } }
      revenueQualities { edges { node { issueReason issueSeverity issueDescription } } }
      isMarketables { edges { node { isMarketable } } }
      locationDescriptions { edges { node { locationDescription } } }
      activities { edges { node { activityType } } }
      cardTransactions(first: 1, conditions: { filter: { AND: [
        { EQ: ["period", "12m"] }
        { EQ: ["quantityType", "card_revenue_amount"] }
        { EQ: ["rank", 0] }
        { IS_NULL: ["platformBrandId"] }
      ] } }) {
        edges { node { projectedQuantity rawQuantity periodStartDate periodEndDate } }
      }
      legalEntities(first: 10) {
        edges {
          node {
            names { edges { node { name } } }
            types { edges { node { type } } }
            tins { edges { node { tin } } }
          }
        }
      }
      operatingLocations(first: 10) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            names { edges { node { name } } }
            addresses(first: 1) { edges { node { fullAddress } } }
            operatingStatuses(first: 1) { edges { node { operatingStatus } } }
            phoneNumbers(first: 1) { edges { node { phoneNumber } } }
          }
        }
      }
    }
  }
}
```

```json
{
  "searchInput": { "name": "Warby Parker", "entityType": "BRAND" }
}
```

---

## Extending the Dump

Use the **Pagination Template** (`references/pagination_template.py`) to fetch more of any connection. For example, to get all operating locations:

1. Run the query above to get the first page
2. Check `operatingLocations.pageInfo.hasNextPage`
3. If true, use the pagination template with `operatingLocations(first: 100, after: $cursor)`

### Additional Fields You Can Add

| Connection | Useful Fields |
|---|---|
| `operatingLocations → cardTransactions` | Per-location revenue (no `platformBrandId` filter needed at OL level) |
| `operatingLocations → reviewSummaries` | `reviewScoreAvg`, `reviewCount` |
| `operatingLocations → technologiesUseds` | Technology stack |
| `operatingLocations → ranks` | Ranking data |
| `legalEntities → registeredEntities` | Formation year, entity type, registrations |
| `legalEntities → bankruptcies` | Bankruptcy records |

---

## Common Mistakes to Avoid

1. **Forgetting `IS_NULL: ["platformBrandId"]`** on brand card transactions — revenue inflated 2x-5x
2. **Requesting `totalCount`** on connections — causes HTTP 400. Use `hasNextPage` instead
3. **Querying `cardTransactions` without filters** — returns hundreds of records. Always filter by `period`, `quantityType`, and `rank`
