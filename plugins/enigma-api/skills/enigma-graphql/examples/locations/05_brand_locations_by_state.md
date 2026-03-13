# Location Lookup Examples

## User Intent

Look up a specific operating location by name and address, or find brand locations filtered by geography.

## Key Concepts

- `OPERATING_LOCATION` searches require `street1` for reliable results
- Location-level card transactions do NOT use `platformBrandId` filter
- `@coalesce` can resolve legal name from multiple paths
- Dual revenue: location-level (per-store) vs brand-level (entire chain)

---

## Operating Location Full Profile

```graphql
query LocationProfile($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      locationName: names(first: 1) { edges { node { name } } }
      brandNames: brands(first: 1) {
        edges { node { names { edges { node { name } } } } }
      }
      locationAddress: addresses(first: 1) { edges { node { fullAddress } } }
      legalName: _fn @coalesce(refs: [
        "legalEntities.edges.0.node.registeredEntities.edges.0.node.name",
        "brands.edges.0.node.legalEntities.edges.0.node.registeredEntities.edges.0.node.name"
      ])
      legalEntities @skip(if: true) {
        edges { node { registeredEntities(first: 1) { edges { node { name } } } } }
      }
      brands @skip(if: true) {
        edges { node { legalEntities(first: 1) { edges { node {
          registeredEntities(first: 1) { edges { node { name } } }
        } } } } }
      }
      locationCardRevenueAmount: cardTransactions(first: 1, conditions: {
        filter: { AND: [
          { EQ: ["period", "12m"] }
          { EQ: ["quantityType", "card_revenue_amount"] }
          { EQ: ["rank", 0] }
        ]}
      }) {
        edges { node { projectedQuantity periodEndDate period quantityType } }
      }
      brandCardRevenueAmount: brands(first: 1) {
        edges { node {
          cardTransactions(first: 1, conditions: {
            filter: { AND: [
              { EQ: ["period", "12m"] }
              { EQ: ["quantityType", "card_revenue_amount"] }
              { EQ: ["rank", 0] }
              { IS_NULL: ["platformBrandId"] }
            ]}
          }) {
            edges { node { projectedQuantity periodEndDate period quantityType } }
          }
        } }
      }
      locationOperatingStatus: operatingStatuses(first: 1) {
        edges { node { operatingStatus lastObservedDate } }
      }
      locationWebsites: websites { edges { node { website } } }
      locationPhones: phoneNumbers { edges { node { phoneNumber } } }
    }
  }
}
```

```json
{
  "searchInput": {
    "conditions": { "limit": 1 },
    "entityType": "OPERATING_LOCATION",
    "name": "Consignment Brooklyn",
    "address": { "street1": "223 Bedford Ave", "city": "Brooklyn", "state": "NY" }
  }
}
```

---

## Simple Location Check

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

1. **Searching `OPERATING_LOCATION` by brand name without address** — returns empty
2. **Using `platformBrandId` filter on OL card transactions** — field doesn't exist at OL level
3. **Using `postalCode` in filters** — correct field is `zip`
4. **Missing `street1`** — most OL searches require it for reliable results
