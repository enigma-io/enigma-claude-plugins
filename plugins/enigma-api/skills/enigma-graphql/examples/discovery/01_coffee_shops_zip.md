# Discovery Example: Coffee Shops in Specific Zip Codes

## User Intent

Find all coffee shops operating in specific zip codes (10001, 10002) that are currently open.

## Key Concepts

- Use `prompt` (NOT `name`) for semantic industry discovery
- Only works with `entityType: BRAND` (prompt + OPERATING_LOCATION → 400)
- Use `conditions.filter` on `SearchInput` to narrow by geography and operating status (this `conditions` is type `Conditions`, which supports `limit`)
- The nested `operatingLocations(conditions:)` arg is type `ConnectionConditions` (filter/orderBy only — NO limit)
- Field path for zip codes: `operatingLocations.addresses.zip`
- Field path for operating status: `operatingLocations.operatingStatuses.operatingStatus`

## Variables

```json
{
  "searchInput": {
    "prompt": "coffee shop",
    "entityType": "BRAND",
    "conditions": {
      "filter": {
        "AND": [
          { "IN": ["operatingLocations.addresses.zip", ["10001", "10002"]] },
          { "EQ": ["operatingLocations.operatingStatuses.operatingStatus", "Open"] }
        ]
      },
      "limit": 25
    }
  },
  "locConditions": {
    "filter": {
      "IN": ["addresses.zip", ["10001", "10002"]]
    }
  }
}
```

## GraphQL Query

`search` returns `[SearchUnion]` — you MUST select with `__typename` + inline fragments. Never use `edges { node }` directly on `search`. Every nested field is a Relay connection (`field(first: N) { edges { node { ... } } }`).

```graphql
query DiscoverCoffeeShops($searchInput: SearchInput!, $locConditions: ConnectionConditions) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      id
      names(first: 1) { edges { node { name } } }
      industries(first: 3) {
        edges {
          node {
            industryDesc
            industryCode
            industryType
          }
        }
      }
      websites(first: 1) { edges { node { website } } }
      operatingLocations(first: 50, conditions: $locConditions) {
        edges {
          node {
            names(first: 1) { edges { node { name } } }
            addresses(first: 1) {
              edges {
                node {
                  fullAddress
                  city
                  zip
                }
              }
            }
            phoneNumbers(first: 1) {
              edges {
                node {
                  phoneNumber
                }
              }
            }
            operatingStatuses(first: 1) {
              edges {
                node {
                  operatingStatus
                }
              }
            }
            reviewSummaries(first: 1) {
              edges {
                node {
                  reviewScoreAvg
                  reviewCount
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

## Expected Output Format

**Markdown table with:**
- Brand name
- Location name (if different)
- Address
- Phone
- Rating (if available)
- Status

**Example:**
```
Found 25 coffee shop brands operating in zip codes 10001, 10002:

| Brand | Location | Address | Phone | Rating | Status |
|---|---|---|---|---|---|
| THE HIGHLINE CAFE | THE HIGHLINE CAFE | ..., New York, 10001 | (212) 555-0100 | 4.2 (150 reviews) | Open |
| ... | ... | ... | ... | ... | ... |
```

## Common Mistakes to Avoid

1. ❌ **Using `name` instead of `prompt`**:
   ```json
   { "name": "coffee shop", "entityType": "BRAND" }  // WRONG - name is entity resolution, not industry
   ```
   ✅ Use:
   ```json
   { "prompt": "coffee shop", "entityType": "BRAND" }  // CORRECT
   ```

2. ❌ **Searching OPERATING_LOCATION by industry prompt**:
   ```json
   { "prompt": "coffee shop", "entityType": "OPERATING_LOCATION" }  // WRONG - 400 "Use entity type BRAND instead"
   ```

3. ❌ **Using `postalCode` in filter**:
   ```json
   { "IN": ["operatingLocations.addresses.postalCode", ["10001"]] }  // WRONG - field is 'zip'
   ```
   ✅ Use:
   ```json
   { "IN": ["operatingLocations.addresses.zip", ["10001"]] }  // CORRECT
   ```

4. ❌ **Lowercase filter values**:
   ```json
   { "EQ": ["operatingLocations.operatingStatuses.operatingStatus", "open"] }  // WRONG
   ```
   ✅ Use:
   ```json
   { "EQ": ["operatingLocations.operatingStatuses.operatingStatus", "Open"] }  // CORRECT
   ```

## Variations

### By State Instead of Zip

```json
{
  "searchInput": {
    "prompt": "coffee shop",
    "entityType": "BRAND",
    "conditions": {
      "filter": {
        "AND": [
          { "EQ": ["operatingLocations.addresses.state", "NY"] },
          { "EQ": ["operatingLocations.operatingStatuses.operatingStatus", "Open"] }
        ]
      },
      "limit": 100
    }
  }
}
```

### By City (Remember: UPPERCASE)

```json
{
  "searchInput": {
    "prompt": "coffee shop",
    "entityType": "BRAND",
    "conditions": {
      "filter": {
        "AND": [
          { "EQ": ["operatingLocations.addresses.city", "NEW YORK"] },
          { "EQ": ["operatingLocations.addresses.state", "NY"] }
        ]
      },
      "limit": 50
    }
  }
}
```

### With Phone Number Requirement

`HAS` operand must be a path to a connection (TYPE), not a scalar leaf — use `operatingLocations.phoneNumbers`, not `...phoneNumber`.

```json
{
  "searchInput": {
    "prompt": "coffee shop",
    "entityType": "BRAND",
    "conditions": {
      "filter": {
        "AND": [
          { "IN": ["operatingLocations.addresses.zip", ["10001", "10002"]] },
          { "HAS": ["operatingLocations.phoneNumbers"] }
        ]
      },
      "limit": 50
    }
  }
}
```

## Python Execution Template

```bash
python3 << 'PYEOF'
import json, urllib.request, os

query = '''query DiscoverCoffeeShops($searchInput: SearchInput!, $locConditions: ConnectionConditions) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      id
      names(first: 1) { edges { node { name } } }
      operatingLocations(first: 50, conditions: $locConditions) {
        edges {
          node {
            names(first: 1) { edges { node { name } } }
            addresses(first: 1) {
              edges { node { fullAddress city zip } }
            }
            phoneNumbers(first: 1) {
              edges { node { phoneNumber } }
            }
            operatingStatuses(first: 1) {
              edges { node { operatingStatus } }
            }
          }
        }
      }
    }
  }
}'''

variables = {
  "searchInput": {
    "prompt": "coffee shop",
    "entityType": "BRAND",
    "conditions": {
      "filter": {
        "AND": [
          { "IN": ["operatingLocations.addresses.zip", ["10001", "10002"]] },
          { "EQ": ["operatingLocations.operatingStatuses.operatingStatus", "Open"] }
        ]
      },
      "limit": 25
    }
  },
  "locConditions": {
    "filter": { "IN": ["addresses.zip", ["10001", "10002"]] }
  }
}

payload = json.dumps({'query': query, 'variables': variables})
req = urllib.request.Request(
    'https://api.enigma.com/graphql',
    data=payload.encode(),
    headers={'content-type': 'application/json', 'x-api-key': os.environ['ENIGMA_API_KEY']}
)
try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    if 'errors' in data:
        for err in data['errors']:
            print(f'GraphQL Error: {err.get("message", err)}')
    else:
        print(json.dumps(data, indent=2))
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.read().decode()}')
except KeyError:
    print('ERROR: ENIGMA_API_KEY not set. Run: export ENIGMA_API_KEY=your_key')
PYEOF
```
