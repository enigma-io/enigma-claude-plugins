# Person Search: Find a Person and Their Companies

## User Intent

Find a specific person and discover all companies they're associated with.

## Key Concepts

- Use `entityType: PERSON` with `person: { firstName, lastName }`
- Two data paths for companies: registered entities (legal filings) and brands (consumer-facing)
- Always deduplicate by registeredEntity ID — same person often appears on multiple state registrations for the same company
- `Brand.roles` is EMPTY — contacts live on `operatingLocations → roles`
- High-profile persons (e.g., Elon Musk) may have hundreds of role edges — response is deeply nested but consistent in structure

---

## Person Search

```graphql
query PersonSearch($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on Person {
      id
      names(first: 3) {
        edges {
          node {
            firstName
            lastName
            fullName
            dateOfBirth
          }
        }
      }
      registeredEntitiesNames: legalEntities(first: 5) {
        edges { node {
          id
          names(first: 1) { edges { node { name } } }
          types(first: 1) { edges { node { legalEntityType } } }
          roles(first: 30, conditions: { filter: { HAS: ["registrations"] } }) {
            edges { node {
              jobTitle
              registrations(first: 5) {
                edges { node {
                  registeredName
                  registrationState
                  status
                  registeredEntities(first: 3) {
                    edges {
                      node {
                        id
                        name
                        registeredEntityType
                      }
                    }
                  }
                } }
              }
            } }
          }
        } }
      }
      brandNames: legalEntities(first: 10) {
        edges { node {
          roles(first: 30) { edges { node {
            registrations(first: 5) { edges { node {
              registeredEntities(first: 1) { edges { node {
                legalEntities(first: 1) { edges { node {
                  brands(first: 1) { edges { node {
                    names(first: 1) { edges { node { name } } }
                  } } }
                } } }
              } } }
            } } }
          } } }
        } }
      }
    }
  }
}
```

```json
{
  "searchInput": {
    "entityType": "PERSON",
    "person": { "firstName": "ELON", "lastName": "MUSK" },
    "conditions": { "limit": 1 }
  }
}
```

**PersonInput fields**: `firstName` (required), `lastName` (required), `dateOfBirth` (optional), `address` (optional AddressInput), `tin` (optional TinInput)

### Extracting Companies from the Response

Deduplicate by registeredEntity ID. Each role → registration → registeredEntity path gives you one company association. Collect the `jobTitle` from the role edge to show what role the person holds.

**Note**: For high-profile persons (e.g., Elon Musk), there may be hundreds of role edges. The response is deeply nested but consistent in structure — extract all `registeredEntities.name` values from `registeredEntitiesNames` and all non-empty `brands.names` from `brandNames`.

---

## Brand Contacts

```graphql
query BrandContacts($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      id
      names(first: 1) { edges { node { name } } }
      operatingLocations(first: 1) {
        edges {
          node {
            roles(first: 20) {
              edges {
                node {
                  jobTitle
                  jobFunction
                  managementLevel
                  emailAddresses(first: 3) { edges { node { emailAddress } } }
                  phoneNumbers(first: 3) { edges { node { phoneNumber } } }
                  legalEntities(first: 3) {
                    edges { node { names(first: 1) { edges { node { name } } } } }
                  }
                }
              }
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
  "searchInput": { "name": "Chipotle", "entityType": "BRAND" }
}
```

### Extracting Contacts from the Response

1. Navigate to `data.search[0].operatingLocations.edges[0].node.roles.edges`
2. Each role edge contains one contact with `jobTitle`, `emailAddresses`, `phoneNumbers`, and `legalEntities` (person name)
3. Filter by `jobTitle` to distinguish officers (`ceo`, `president`, `cfo`) from service providers (`registered agent`)
4. Deduplicate by person name if the same person appears in multiple roles

**Filtering contacts**: Officers: `ceo`, `president`, `cfo`, `director`, `secretary`. Skip: `registered agent`, `applicant`, `unknown`.

**Alternative: Get contacts from multiple locations** — If you need comprehensive contact coverage, increase `operatingLocations(first: 10)` and collect roles from multiple locations. This is useful for large brands where different locations may have different contact information.

---

## Common Mistakes to Avoid

1. **Using `LegalEntity.persons`** to find officers — usually EMPTY
2. **Using `Role.title`** — correct field is `jobTitle`
3. **Using `Person.fullName` directly** — must traverse `names → edges → node → fullName`
4. **Using `Brand.roles`** for contacts — always empty. Use `operatingLocations → roles`
5. **Not deduplicating** — same person appears on multiple state registrations for the same company
