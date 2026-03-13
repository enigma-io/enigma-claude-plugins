# Brand Lookup Examples

## User Intent

Look up a specific company to get its profile, revenue, locations, contacts, and corporate structure.

## Key Concepts

- Use `name` (entity resolution) with `entityType: BRAND`
- Brand-level card transactions always require `IS_NULL: ["platformBrandId"]`
- Contacts live on `operatingLocations → roles`, NOT `Brand.roles` (which is empty)
- Two paths for people: brand contacts (via OL roles) and legal entity contacts (via registrations)

---

## Full Brand Profile

```graphql
query BrandProfile($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on Brand {
      names(first: 1) { edges { node { name } } }
      legalNames: legalEntities(first: 1) {
        edges { node { registeredEntities(first: 1) { edges { node { name } } } } }
      }
      brandCardRevenueAmount: cardTransactions(first: 1, conditions: {
        filter: { AND: [
          { EQ: ["quantityType", "card_revenue_amount"] }
          { EQ: ["rank", 0] }
          { EQ: ["period", "12m"] }
          { IS_NULL: ["platformBrandId"] }
        ]}
      }) {
        edges { node { projectedQuantity periodEndDate period quantityType } }
      }
      websites(first: 1) { edges { node { website } } }
      primaryPhone: operatingLocations(first: 1, conditions: { filter: { HAS: ["phoneNumbers"] } }) {
        edges { node { phoneNumbers(first: 1) { edges { node { phoneNumber } } } } }
      }
      hqAddress: operatingLocations(first: 1) {
        edges { node {
          addresses(first: 1) { edges { node { fullAddress streetAddress1 streetAddress2 zip city state msa } } }
        } }
      }
      peopleConnectedToLegalEntity: legalEntities {
        edges { node {
          registeredEntities { edges { node {
            registrations { edges { node {
              roles(first: 5, conditions: { filter: { NE: ["jobTitle", "registered agent"] } }) {
                edges { node {
                  jobTitle
                  legalEntities { edges { node {
                    persons(first: 1) { edges { node {
                      names(first: 1) { edges { node { firstName lastName } } }
                    } } }
                  } } }
                } }
              }
            } } }
          } } }
        } }
      }
      peopleConnectedToBrand: operatingLocations(first: 1) {
        edges { node {
          roles(first: 10, conditions: { filter: { NE: ["jobTitle", "registered agent"] } }) {
            edges { node {
              jobFunction jobTitle
              legalEntities { edges { node {
                persons(first: 1) { edges { node {
                  names(first: 1) { edges { node { firstName lastName } } }
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
    "name": "CONSIGNMENT BROOKLYN",
    "website": "https://www.consignmentbrooklyn.com/"
  }
}
```

---

## Marketing Overview

```graphql
query MarketingBrand($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      names { edges { node { name } } }
      industries { edges { node { industryDesc industryCode industryType } } }
      revenueQualities { edges { node { issueReason issueSeverity issueDescription } } }
      isMarketables { edges { node { isMarketable } } }
      websites { edges { node { website domain } } }
      locationDescriptions { edges { node { locationDescription } } }
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

---

## Brand Locations by Geography

**NEVER search `OPERATING_LOCATION` by brand name** — returns empty. Search BRAND, filter locations:

```graphql
query BrandLocations($searchInput: SearchInput!, $conditions: ConnectionConditions) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      names { edges { node { name } } }
      operatingLocations(first: 100, conditions: $conditions) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            id
            names { edges { node { name } } }
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

**Filter by state**: `{ "conditions": { "filter": { "EQ": ["addresses.state", "NY"] } } }`

**Filter by city**: `{ "conditions": { "filter": { "IN": ["addresses.city", ["NEW YORK", "BROOKLYN"]] } } }`

---

## Common Mistakes to Avoid

1. **Missing `IS_NULL: ["platformBrandId"]`** on brand card transactions — revenue will be 2x-5x inflated
2. **Searching `OPERATING_LOCATION` by brand name** — always returns empty
3. **Using `Brand.roles`** to find contacts — always empty. Use `operatingLocations → roles`
4. **Franchise/chain confusion** — brand-level revenue is the entire chain. For single-location, use OPERATING_LOCATION search with street address
