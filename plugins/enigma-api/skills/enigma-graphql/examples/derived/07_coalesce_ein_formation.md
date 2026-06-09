# Derived Attributes: @coalesce and @skip

The V2 API supports derived attributes — virtual fields computed from multiple traversal paths.

## Key Concepts

| Directive | Purpose |
|---|---|
| `_fn @coalesce(refs: [...])` | Returns the **first non-null value** from an ordered list of traversal paths |
| `@skip(if: true)` | Declares a traversal path for `@coalesce` without returning it in the response |

**How it works:**
1. `_fn @coalesce(refs: ["path1", "path2"])` — try path1 first, if null try path2
2. Each `ref` is a dot-delimited path using the FULL Relay form, including `edges.0.node.` segments — e.g. `"legalEntities.edges.0.node.tins.edges.0.node.tin"` (live-verified; the abbreviated `.0.` form resolves null)
3. Every path referenced must also be present in the query body so it is traversed — annotate it with `@skip(if: true)` to keep it out of the response
4. `conditions` / `orderBy` on `@skip`-annotated fields DO affect what `@coalesce` resolves
5. Every connection in the backing paths still needs `(first: N) { edges { node { ... } } }`

---

## EIN / TIN Lookup

Resolves EIN for an operating location — tries the direct legal entity first, falls back to the brand's legal entity:

```graphql
query EINLookup($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      EIN: _fn @coalesce(refs: [
        "legalEntities.edges.0.node.tins.edges.0.node.tin"
        "brands.edges.0.node.legalEntities.edges.0.node.tins.edges.0.node.tin"
      ])
      legalEntities(first: 1, conditions: { filter: { HAS: ["tins"] } }) @skip(if: true) {
        edges { node { tins(first: 1) { edges { node { tin } } } } }
      }
      brands(first: 1) @skip(if: true) {
        edges { node {
          legalEntities(first: 1, conditions: { filter: { HAS: ["tins"] } }) {
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

**Live response**: `{ "data": { "search": [{ "EIN": "833173853" }] } }` — the location's own `legalEntities` is empty, so `@coalesce` falls through to the brand's legal entity.

> Note: `AddressInput` uses `street1` and `postalCode` (NOT `zip`, which is an OUTPUT field). Passing `zip` to `searchInput.address` returns a 400.

---

## Formation Year

Resolves formation year — tries the direct legal entity first, falls back to the **earliest** across the brand's entities (via `orderBy ... ASC` on the `@skip` backing paths):

```graphql
query FormationYearLookup($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      formationYear: _fn @coalesce(refs: [
        "legalEntities.edges.0.node.registeredEntities.edges.0.node.formationYear"
        "brands.edges.0.node.legalEntities.edges.0.node.registeredEntities.edges.0.node.formationYear"
      ])
      legalEntities(first: 1) @skip(if: true) {
        edges { node { registeredEntities(first: 1) { edges { node { formationYear } } } } }
      }
      brands(first: 1) @skip(if: true) {
        edges { node {
          legalEntities(first: 1, conditions: { orderBy: ["registeredEntities.formationYear ASC"] }) {
            edges { node {
              registeredEntities(first: 1, conditions: { orderBy: ["formationYear ASC"] }) {
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

```json
{
  "searchInput": {
    "name": "D & D DRYWALL",
    "entityType": "OPERATING_LOCATION",
    "address": { "street1": "2071 WOOD RD", "city": "FULTON", "state": "CA", "postalCode": "95439" }
  }
}
```

**Live response**: `{ "data": { "search": [{ "formationYear": 2019 }] } }`. (`RegisteredEntity` exposes both `formationYear` (Int) and `formationDate` (Date).)

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
        edges { node { projectedQuantity rawQuantity periodStartDate periodEndDate } }
      }

      legalEntities(first: 1, conditions: { filter: { HAS: ["tins"] } }) @skip(if: true) {
        edges {
          node {
            tins(first: 1) { edges { node { tin } } }
            registeredEntities(first: 1) { edges { node { formationYear } } }
          }
        }
      }
      brands(first: 1) @skip(if: true) {
        edges {
          node {
            legalEntities(first: 1, conditions: { filter: { HAS: ["tins"] }, orderBy: ["registeredEntities.formationYear ASC"] }) {
              edges {
                node {
                  tins(first: 1) { edges { node { tin } } }
                  registeredEntities(first: 1, conditions: { orderBy: ["formationYear ASC"] }) {
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

```json
{
  "searchInput": {
    "name": "D & D DRYWALL",
    "entityType": "OPERATING_LOCATION",
    "address": { "street1": "2071 WOOD RD", "city": "FULTON", "state": "CA", "postalCode": "95439" }
  },
  "revCond": { "filter": { "AND": [{ "EQ": ["period", "12m"] }, { "EQ": ["quantityType", "card_revenue_amount"] }] } }
}
```

Live result: flat response with `EIN` = `833173853`, `formationYear` = `2019`, plus name/address/status. (This small contractor has no card revenue, so `revenue.edges` is empty — at the OL level `cardTransactions` has both `projectedQuantity` and `rawQuantity` and takes no `platformBrandId` filter.)

Returns a flat response: name, address, status, EIN, formation year, and revenue from a single query.
