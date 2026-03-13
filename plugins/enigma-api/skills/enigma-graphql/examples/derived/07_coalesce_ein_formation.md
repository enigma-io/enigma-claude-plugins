# Derived Attributes: @coalesce and @skip

The V2 API supports derived attributes — virtual fields computed from multiple traversal paths.

## Key Concepts

| Directive | Purpose |
|---|---|
| `_fn @coalesce(refs: [...])` | Returns the **first non-null value** from an ordered list of traversal paths |
| `@skip(if: true)` | Declares a traversal path for `@coalesce` without returning it in the response |

**How it works:**
1. `_fn @coalesce(refs: ["path1", "path2"])` — try path1 first, if null try path2
2. Each `ref` is a dot-delimited path (e.g., `"legalEntities.edges.0.node.tins.edges.0.node.tin"`)
3. Corresponding traversal fields must be in the query — use `@skip(if: true)` to include without cluttering response
4. `conditions` and `orderBy` on `@skip`-annotated fields DO affect what `@coalesce` resolves

---

## EIN / TIN Lookup

Resolves EIN for an operating location — tries direct legal entity first, falls back to brand's legal entity:

```graphql
query EINLookup($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      EIN: _fn @coalesce(refs: [
        "legalEntities.edges.0.node.tins.edges.0.node.tin"
        "brands.edges.0.node.legalEntities.edges.0.node.tins.edges.0.node.tin"
      ])
      legalEntities(conditions: { filter: { HAS: ["tins"] } }) @skip(if: true) {
        edges { node { tins(first: 1) { edges { node { tin } } } } }
      }
      brands @skip(if: true) {
        edges { node {
          legalEntities(conditions: { filter: { HAS: ["tins"] } }) {
            edges { node { tins(first: 1) { edges { node { tin } } } } }
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
    "name": "D & D DRYWALL",
    "entityType": "OPERATING_LOCATION",
    "address": { "street1": "2071 WOOD RD", "city": "FULTON", "state": "CA", "postalCode": "95439" }
  }
}
```

**Response**: `{ "data": { "search": [{ "EIN": "12-3456789" }] } }`

---

## Formation Year

Resolves formation year — tries direct legal entity first, falls back to **earliest** across brand's entities:

```graphql
query FormationYearLookup($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      formationYear: _fn @coalesce(refs: [
        "legalEntities.edges.0.node.registeredEntities.edges.0.node.formationYear"
        "brands.edges.0.node.legalEntities.edges.0.node.registeredEntities.edges.0.node.formationYear"
      ])
      legalEntities @skip(if: true) {
        edges { node { registeredEntities { edges { node { formationYear } } } } }
      }
      brands @skip(if: true) {
        edges { node {
          legalEntities(conditions: { orderBy: ["registeredEntities.formationYear ASC"] }) {
            edges { node {
              registeredEntities(conditions: { orderBy: ["formationYear ASC"] }) {
                edges { node { formationYear } }
              }
            } }
          }
        } }
      }
    }
  }
}
```

---

## Combined: EIN + Formation Year + Revenue

```graphql
query LocationProfile($searchInput: SearchInput!, $revCond: ConnectionConditions!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      names(first: 1) { edges { node { name } } }
      addresses(first: 1) { edges { node { fullAddress city state zip } } }
      operatingStatuses(first: 1) { edges { node { operatingStatus } } }

      EIN: _fn @coalesce(refs: [
        "legalEntities.edges.0.node.tins.edges.0.node.tin"
        "brands.edges.0.node.legalEntities.edges.0.node.tins.edges.0.node.tin"
      ])
      formationYear: _fn @coalesce(refs: [
        "legalEntities.edges.0.node.registeredEntities.edges.0.node.formationYear"
        "brands.edges.0.node.legalEntities.edges.0.node.registeredEntities.edges.0.node.formationYear"
      ])

      revenue: cardTransactions(first: 1, conditions: $revCond) {
        edges { node { projectedQuantity periodStartDate periodEndDate } }
      }

      legalEntities(conditions: { filter: { HAS: ["tins"] } }) @skip(if: true) {
        edges {
          node {
            tins(first: 1) { edges { node { tin } } }
            registeredEntities { edges { node { formationYear } } }
          }
        }
      }
      brands @skip(if: true) {
        edges {
          node {
            legalEntities(conditions: { filter: { HAS: ["tins"] }, orderBy: ["registeredEntities.formationYear ASC"] }) {
              edges {
                node {
                  tins(first: 1) { edges { node { tin } } }
                  registeredEntities(conditions: { orderBy: ["formationYear ASC"] }) {
                    edges { node { formationYear } }
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

Returns flat response: name, address, status, EIN, formation year, and revenue from a single query.
