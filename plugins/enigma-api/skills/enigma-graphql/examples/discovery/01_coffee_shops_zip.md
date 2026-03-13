# Discovery Example: Coffee Shops in Specific Zip Codes

## User Intent

Find all coffee shops operating in specific zip codes (12983, 12946, 12989) that are currently open.

## Key Concepts

- Use `prompt` (NOT `name`) for semantic industry discovery
- Only works with `entityType: BRAND`
- Use `conditions.filter` on `SearchInput` to narrow by geography and operating status
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
          { "IN": ["operatingLocations.addresses.zip", ["12983", "12946", "12989"]] },
          { "EQ": ["operatingLocations.operatingStatuses.operatingStatus", "Open"] }
        ]
      },
      "limit": 50
    }
  },
  "locConditions": {
    "filter": {
      "IN": ["addresses.zip", ["12983", "12946", "12989"]]
    }
  }
}
```

## GraphQL Query

```graphql
query DiscoverCoffeeShops($searchInput: SearchInput!, $locConditions: ConnectionConditions) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      names: names(first: 1) { edges { node { name } } }
      industries: industries(first: 3) {
        edges {
          node {
            industryDesc
            industryCode
            industryType
          }
        }
      }
      websites: websites(first: 1) { edges { node { website } } }
      operatingLocations(first: 50, conditions: $locConditions) {
        edges {
          node {
            names: names(first: 1) { edges { node { name } } }
            addresses: addresses(first: 1) {
              edges {
                node {
                  fullAddress
                  city
                  zip
                }
              }
            }
            phoneNumbers: phoneNumbers(first: 1) {
              edges {
                node {
                  phoneNumber
                }
              }
            }
            operatingStatuses: operatingStatuses(first: 1) {
              edges {
                node {
                  operatingStatus
                }
              }
            }
            reviewSummaries: reviewSummaries(first: 1) {
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
Found 8 coffee shop brands operating in zip codes 12983, 12946, 12989:

| Brand | Location | Address | Phone | Rating | Status |
|---|---|---|---|---|---|
| Starbucks | Starbucks - Lake Placid | 123 Main St, Lake Placid, 12946 | (518) 555-0100 | 4.2 (150 reviews) | Open |
| Dunkin' | Dunkin' - Saranac Lake | 456 Broadway, Saranac Lake, 12983 | (518) 555-0200 | 4.0 (89 reviews) | Open |
| ... | ... | ... | ... | ... | ... |
```

## Common Mistakes to Avoid

1. ❌ **Using `name` instead of `prompt`**:
   ```json
   { "name": "coffee shop", "entityType": "BRAND" }  // WRONG - returns nothing
   ```
   ✅ Use:
   ```json
   { "prompt": "coffee shop", "entityType": "BRAND" }  // CORRECT
   ```

2. ❌ **Searching OPERATING_LOCATION by industry**:
   ```json
   { "prompt": "coffee shop", "entityType": "OPERATING_LOCATION" }  // WRONG - prompt only works with BRAND
   ```

3. ❌ **Using `postalCode` in filter**:
   ```json
   { "IN": ["operatingLocations.addresses.postalCode", ["12983"]] }  // WRONG - field is 'zip'
   ```
   ✅ Use:
   ```json
   { "IN": ["operatingLocations.addresses.zip", ["12983"]] }  // CORRECT
   ```

4. ❌ **Lowercase values**:
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
          { "EQ": ["operatingLocations.addresses.city", "LAKE PLACID"] },
          { "EQ": ["operatingLocations.addresses.state", "NY"] }
        ]
      },
      "limit": 50
    }
  }
}
```

### With Phone Number Requirement

```json
{
  "searchInput": {
    "prompt": "coffee shop",
    "entityType": "BRAND",
    "conditions": {
      "filter": {
        "AND": [
          { "IN": ["operatingLocations.addresses.zip", ["12983", "12946"]] },
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
    ... on Brand {
      id
      names: names(first: 1) { edges { node { name } } }
      operatingLocations(first: 50, conditions: $locConditions) {
        edges {
          node {
            names: names(first: 1) { edges { node { name } } }
            addresses: addresses(first: 1) {
              edges { node { fullAddress city zip } }
            }
            phoneNumbers: phoneNumbers(first: 1) {
              edges { node { phoneNumber } }
            }
            operatingStatuses: operatingStatuses(first: 1) {
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
          { "IN": ["operatingLocations.addresses.zip", ["12983", "12946", "12989"]] },
          { "EQ": ["operatingLocations.operatingStatuses.operatingStatus", "Open"] }
        ]
      },
      "limit": 50
    }
  },
  "locConditions": {
    "filter": { "IN": ["addresses.zip", ["12983", "12946", "12989"]] }
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
