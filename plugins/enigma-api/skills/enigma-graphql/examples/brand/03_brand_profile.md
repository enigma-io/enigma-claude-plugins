# Brand Lookup Examples

## User Intent

Look up a specific company to get its profile, revenue, locations, contacts, and corporate structure.

## Key Concepts

- Use `name` (entity resolution) with `entityType: BRAND`
- `search` returns `[SearchUnion]` — select with `__typename` + inline fragments; never `edges { node }` on `search` itself
- Every nested field is a Relay connection: `field(first: N) { edges { node { ... } } }`
- Brand-level card transactions always require `IS_NULL: ["platformBrandId"]` (dedup)
- Address output fields: `streetAddress1`, `streetAddress2`, `city`, `state`, `zip`, `fullAddress`, `msa` (NOT `street1` — that's input-only)
- Contacts live on `operatingLocations → roles`, NOT `Brand.roles`
- Corporate people path: `legalEntities → registeredEntities → registrations → roles → legalEntities → persons → names`
- `Role` fields: `jobTitle`, `jobFunction`, `managementLevel` (NO `roleType`, NO `fullName`)

---

## Full Brand Profile

```graphql
query BrandProfile($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      names(first: 1) { edges { node { name } } }
      legalNames: legalEntities(first: 1) {
        edges { node { registeredEntities(first: 1) { edges { node { name registeredEntityType formationYear } } } } }
      }
      industries(first: 5) { edges { node { industryDesc industryCode industryType } } }
      websites(first: 3) { edges { node { website domain } } }
      brandCardRevenueAmount: cardTransactions(first: 1, conditions: {
        filter: { AND: [
          { EQ: ["quantityType", "card_revenue_amount"] }
          { EQ: ["period", "12m"] }
          { IS_NULL: ["platformBrandId"] }
        ]}
      }) {
        edges { node { projectedQuantity periodEndDate period quantityType } }
      }
      operatingLocations(first: 5) {
        edges { node {
          names(first: 1) { edges { node { name } } }
          addresses(first: 1) {
            edges { node { fullAddress streetAddress1 streetAddress2 city state zip msa } }
          }
          phoneNumbers(first: 1) { edges { node { phoneNumber } } }
          operatingStatuses(first: 1) { edges { node { operatingStatus } } }
        } }
      }
      peopleConnectedToLegalEntity: legalEntities(first: 1) {
        edges { node {
          registeredEntities(first: 1) { edges { node {
            registrations(first: 1) { edges { node {
              roles(first: 5, conditions: { filter: { NE: ["jobTitle", "registered agent"] } }) {
                edges { node {
                  jobTitle
                  legalEntities(first: 1) { edges { node {
                    persons(first: 1) { edges { node {
                      names(first: 1) { edges { node { firstName lastName fullName } } }
                    } } }
                  } } }
                } }
              }
            } } }
          } } }
        } }
      }
      peopleConnectedToBrand: operatingLocations(first: 3) {
        edges { node {
          roles(first: 5, conditions: { filter: { NE: ["jobTitle", "registered agent"] } }) {
            edges { node {
              jobFunction jobTitle managementLevel
              legalEntities(first: 1) { edges { node {
                persons(first: 1) { edges { node {
                  names(first: 1) { edges { node { firstName lastName fullName } } }
                } } }
              } } }
            } }
          }
        } }
      }
    }
  }
}
```

```json
{
  "searchInput": {
    "conditions": { "limit": 1 },
    "entityType": "BRAND",
    "name": "Tacombi"
  }
}
```

> The corporate-people traversal is expensive. On very large chains (e.g. Starbucks) it can time out; keep `first` values small or query people separately.

---

## Marketing Overview

```graphql
query MarketingBrand($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      id
      names(first: 1) { edges { node { name } } }
      industries(first: 5) { edges { node { industryDesc industryCode industryType } } }
      revenueQualities(first: 5) { edges { node { issueReason issueSeverity issueDescription } } }
      isMarketables(first: 1) { edges { node { isMarketable } } }
      websites(first: 3) { edges { node { website domain } } }
      locationDescriptions(first: 3) { edges { node { locationDescription } } }
      operatingLocations(first: 5) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            addresses(first: 1) { edges { node { fullAddress } } }
            operatingStatuses(first: 1) { edges { node { operatingStatus } } }
          }
        }
      }
    }
  }
}
```

```json
{ "searchInput": { "conditions": { "limit": 1 }, "entityType": "BRAND", "name": "Tacombi" } }
```

---

## Brand Locations by Geography

**NEVER search `OPERATING_LOCATION` by brand name** — returns empty. Search BRAND, filter the brand's locations via the `operatingLocations(conditions:)` arg (type `ConnectionConditions`, filter/orderBy only):

```graphql
query BrandLocations($searchInput: SearchInput!, $conditions: ConnectionConditions) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      id
      names(first: 1) { edges { node { name } } }
      operatingLocations(first: 100, conditions: $conditions) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            id
            names(first: 1) { edges { node { name } } }
            addresses(first: 1) { edges { node { fullAddress state city } } }
            phoneNumbers(first: 1) { edges { node { phoneNumber } } }
            operatingStatuses(first: 1) { edges { node { operatingStatus } } }
          }
        }
      }
    }
  }
}
```

```json
{
  "searchInput": { "conditions": { "limit": 1 }, "entityType": "BRAND", "name": "Sweetgreen" },
  "conditions": { "filter": { "EQ": ["addresses.state", "NY"] } }
}
```

**Filter by city**: `{ "conditions": { "filter": { "IN": ["addresses.city", ["NEW YORK", "BROOKLYN"]] } } }`

---

## Common Mistakes to Avoid

1. **Missing `IS_NULL: ["platformBrandId"]`** on brand card transactions — revenue will be 2x-5x inflated
2. **Selecting `edges { node }` directly on `search`** — `search` is a `[SearchUnion]`; use `__typename` + `... on Brand { }`
3. **Plain `names { name }`** — every nested field is a connection; use `names(first: 1) { edges { node { name } } }`
4. **Searching `OPERATING_LOCATION` by brand name** — always returns empty
5. **Using `Brand.roles`** to find contacts — use `operatingLocations → roles` (brand contacts) or the registeredEntities → registrations → roles path (corporate officers)
6. **Using `street1` in output** — that's input-only; the output field is `streetAddress1`
7. **Franchise/chain confusion** — brand-level revenue is the entire chain. For a single location, use OPERATING_LOCATION search with a street address
