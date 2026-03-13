# Connection Filter Syntax

Connections accept `conditions: { filter: JSON }` for server-side filtering. The filter uses **operator-as-key** syntax with dot-notation field paths.

## Basic Syntax

```json
{ "OPERATOR": ["field.path", value] }
```

## Available Operators

| Operator | Description | Example |
|---|---|---|
| `EQ` | Equals (exact match) | `{ "EQ": ["addresses.state", "NY"] }` |
| `NE` | Not equals | `{ "NE": ["addresses.state", "CA"] }` |
| `GT` | Greater than | `{ "GT": ["cardTransactions.projectedQuantity", 100000] }` |
| `GTE` | Greater than or equal | `{ "GTE": ["reviewSummaries.reviewScoreAvg", 4.0] }` |
| `LT` | Less than | `{ "LT": ["cardTransactions.projectedQuantity", 50000] }` |
| `LTE` | Less than or equal | `{ "LTE": ["reviewSummaries.reviewCount", 100] }` |
| `IN` | In array (multiple values) | `{ "IN": ["addresses.state", ["NY", "CA", "TX"]] }` |
| `LIKE` | Pattern matching (case-sensitive) | `{ "LIKE": ["names.name", "%Coffee%"] }` |
| `ILIKE` | Pattern matching (case-insensitive) | `{ "ILIKE": ["names.name", "%coffee%"] }` |
| `HAS` | Field exists / has value | `{ "HAS": ["phoneNumbers"] }` |

## Logical Operators

| Operator | Description | Example |
|---|---|---|
| `AND` | All conditions must be true | `{ "AND": [{ "EQ": ["addresses.state", "NY"] }, { "EQ": ["operatingStatuses.operatingStatus", "Open"] }] }` |
| `OR` | At least one condition must be true | `{ "OR": [{ "EQ": ["addresses.state", "NY"] }, { "EQ": ["addresses.state", "CA"] }] }` |
| `NOT` | Negates the condition | `{ "NOT": [{ "EQ": ["operatingStatuses.operatingStatus", "Closed"] }] }` |

## Field Path Notation

Field paths use dot notation to traverse from the parent entity into related entities.

**Example**: To filter `operatingLocations` by state, use `addresses.state` (not just `state`, which lives on `Address`, not `OperatingLocation`).

### Common Field Paths

#### On Brand (SearchInput conditions)

| Filter | Field Path | Value Format |
|---|---|---|
| State | `operatingLocations.addresses.state` | 2-letter uppercase (e.g., `"NY"`) |
| City | `operatingLocations.addresses.city` | UPPERCASE (e.g., `"NEW YORK"`) |
| Zip code | `operatingLocations.addresses.zip` | String (e.g., `"10001"`) |
| Operating status | `operatingLocations.operatingStatuses.operatingStatus` | `"Open"` or `"Closed"` |
| Industry code (NAICS) | `industries.industryCode` | 6-digit string (e.g., `"722515"`) |
| Industry type | `industries.industryType` | `"naics_2022_code"` |
| Has phone | `operatingLocations.roles.phoneNumbers` | Use `HAS` operator |
| Has email | `operatingLocations.roles.emailAddresses` | Use `HAS` operator |

#### On OperatingLocation Connection

| Filter | Field Path | Value Format |
|---|---|---|
| State | `addresses.state` | 2-letter uppercase (e.g., `"NY"`) |
| City | `addresses.city` | UPPERCASE (e.g., `"BROOKLYN"`) |
| Zip | `addresses.zip` | String (e.g., `"11201"`) |
| Operating status | `operatingStatuses.operatingStatus` | `"Open"` or `"Closed"` |
| Location type | `locationTypes.locationType` | e.g., `"restaurant"`, `"retail"` |

#### On CardTransaction Connection

| Filter | Field Path | Value Format |
|---|---|---|
| Period | `period` | `"12m"` or `"1m"` |
| Quantity type | `quantityType` | `"card_revenue_amount"`, `"card_transactions_count"`, etc. |
| Rank (time ordering) | `rank` | Integer (0 = most recent) |
| Platform brand ID | `platformBrandId` | UUID string, or use `{ "NOT": [{ "NE": ["platformBrandId"] }] }` for NULL (aggregate) |

## Examples

### Single Value Filter

```json
{ "EQ": ["addresses.state", "NY"] }
```

### Multiple Values (IN)

```json
{ "IN": ["addresses.state", ["NY", "CA", "TX"]] }
```

### Combining Conditions (AND)

```json
{
  "AND": [
    { "EQ": ["addresses.state", "NY"] },
    { "IN": ["addresses.city", ["NEW YORK", "BROOKLYN", "BRONX", "QUEENS", "STATEN ISLAND"]] }
  ]
}
```

### Complex Multi-Level Filter

```json
{
  "AND": [
    { "IN": ["operatingLocations.addresses.zip", ["12983", "12946", "12989"]] },
    { "EQ": ["operatingLocations.operatingStatuses.operatingStatus", "Open"] },
    { "HAS": ["operatingLocations.phoneNumbers"] }
  ]
}
```

### IS NULL Pattern (platformBrandId)

The filter DSL has no `IS_NULL` operator. To filter for NULL values, use:

```json
{ "NOT": [{ "NE": ["platformBrandId"] }] }
```

This means "platformBrandId IS NULL" because:
- `NE` with a single argument means "is not null"
- `NOT` negates it to "is null"

### Pattern Matching (LIKE/ILIKE)

Case-sensitive:
```json
{ "LIKE": ["names.name", "%Coffee%"] }
```

Case-insensitive:
```json
{ "ILIKE": ["names.name", "%coffee%"] }
```

### Field Exists (HAS)

```json
{ "HAS": ["phoneNumbers"] }
```

## Important Notes

- **Field values are UPPERCASE**: Most values in Enigma dataset are uppercase (e.g., `"NY"` not `"ny"`, `"NEW YORK"` not `"New York"`). Use `ILIKE` for case-insensitive matching if unsure.
- **Zip code field**: Use `zip` (NOT `postalCode`) in filter conditions. The `postalCode` field only exists on `AddressInput`, not on the `Address` type used in conditions.
- **City names**: Always uppercase (e.g., `"NEW YORK"`, not `"New York"`).
- **Operating status**: Values are `"Open"` or `"Closed"` (capitalized).

## Usage in GraphQL

### SearchInput Conditions (Brand-level filtering)

```graphql
query DiscoverBrands($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      names { edges { node { name } } }
    }
  }
}
```

```json
{
  "searchInput": {
    "prompt": "coffee shop",
    "entityType": "BRAND",
    "conditions": {
      "filter": {
        "AND": [
          { "IN": ["operatingLocations.addresses.zip", ["12983", "12946"]] },
          { "EQ": ["operatingLocations.operatingStatuses.operatingStatus", "Open"] }
        ]
      },
      "limit": 50
    }
  }
}
```

### Connection-Level Conditions

```graphql
query BrandLocations($searchInput: SearchInput!, $locConditions: ConnectionConditions) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      operatingLocations(first: 100, conditions: $locConditions) {
        edges { node { ... } }
      }
    }
  }
}
```

```json
{
  "searchInput": { "name": "Starbucks", "entityType": "BRAND" },
  "locConditions": {
    "filter": { "EQ": ["addresses.state", "NY"] }
  }
}
```
