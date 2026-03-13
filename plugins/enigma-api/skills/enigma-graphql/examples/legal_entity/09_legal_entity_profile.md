# Legal Entity Profile: Formation, Registration Address, Linked Brand

## User Intent

Look up a legal entity to get formation info, registration address, entity type, and linked brand details.

## Key Concepts

- Use `entityType: LEGAL_ENTITY` with `name` (entity resolution)
- `formationYear` (Int) and `registeredEntityType` are on `RegisteredEntity`
- `addressType` ("registered", "principal", etc.) is on the **edge** of `Registration.addresses`, NOT on the address node
- Filter registrations by `status: "active"` to get current registration address

---

## Legal Entity Profile Query

```graphql
{
  search(searchInput: {
    conditions: { limit: 1 }
    entityType: LEGAL_ENTITY
    name: "45 Mercer Restaurant LLC"
  }) {
    ... on LegalEntity {
      legalEntityNames: registeredEntities(first: 1) {
        edges { node { name } }
      }
      formationYearAndType: registeredEntities(first: 1) {
        edges { node { formationYear registeredEntityType } }
      }
      registrationAddress: registeredEntities(first: 1) {
        edges { node {
          registrations(first: 1, conditions: { filter: { EQ: ["status", "active"] } }) {
            edges { node {
              addresses(first: 1) {
                edges {
                  addressType
                  node { fullAddress }
                }
              }
            } }
          }
        } }
      }
      brandNames: brands(first: 1) {
        edges { node { names(first: 1) { edges { node { name } } } } }
      }
      brandWebsites: brands(first: 1) {
        edges { node { websites(first: 1) { edges { node { website } } } } }
      }
      brandHQAddress: brands(first: 1) {
        edges { node { operatingLocations(first: 1) {
          edges { node { addresses(first: 1) { edges { node {
            streetAddress1 streetAddress2 city state zip msa
          } } } } }
        } } }
      }
    }
  }
}
```

**Variables**: None (inline query). Change the `name` value for different entities.

---

## Expected Output Format

```
## 45 Mercer Restaurant LLC

**Entity Type**: Limited Liability Company
**Formation Year**: 2015
**Registration Address** (registered): 123 Main St, New York, NY 10001

### Linked Brand
**Brand Name**: 45 Mercer Restaurant
**Website**: https://www.example.com
**HQ Address**: 45 Mercer St, New York, NY 10013
```

---

## Key Fields

| Field | Type | Location | Notes |
|---|---|---|---|
| `formationYear` | Int | `RegisteredEntity` | NOT `formationDate` — this is an integer year |
| `registeredEntityType` | String | `RegisteredEntity` | e.g., "Limited Liability Company", "Corporation" |
| `addressType` | String | Edge of `Registration.addresses` | e.g., "registered", "principal", "mailing" — on the EDGE, not node |

## Common Mistakes to Avoid

1. **Using `formationDate` instead of `formationYear`** — the field is `formationYear` (Int), not a Date
2. **Looking for `addressType` on the address node** — it's on the EDGE: `edges { addressType node { fullAddress } }`
3. **Not filtering by active registration** — without `status: "active"`, you may get historical addresses
