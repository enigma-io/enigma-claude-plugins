# KYB Example: Corporate Officers & Structure Lookup

## User Intent

Look up the corporate structure of a business and find all officers, directors, and registered agents.

## Key Concepts

- Start with `BRAND` entity type using `name` (entity resolution)
- Traverse: `BRAND → legalEntities → registeredEntities → registrations → roles → legalEntities`
- **CRITICAL**: Officers are on `Registration.roles`, NOT `LegalEntity.persons` (which is usually empty)
- People are modeled as `LegalEntity` nodes (use the `names` connection, field `name`) and can also be resolved to `persons` (with `firstName`/`lastName`/`fullName`)
- `Role` has `jobTitle`, `jobFunction`, `managementLevel` fields — NO `title`, NO `names`
- `search` returns `[SearchUnion]` — select with `__typename` + inline fragments, never `edges { node }` on `search` itself
- Every nested field is a Relay connection: `field(first: N) { edges { node { ... } } }`

## Variables

```json
{
  "searchInput": {
    "name": "Tacombi",
    "entityType": "BRAND"
  }
}
```

## GraphQL Query

```graphql
query CorporateStructure($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      id
      names(first: 1) { edges { node { name } } }
      websites(first: 1) { edges { node { website } } }
      legalEntities(first: 10) {
        edges {
          node {
            names(first: 1) { edges { node { name } } }
            types(first: 1) { edges { node { legalEntityType } } }
            tins(first: 1) { edges { node { tin } } }
            addresses(first: 1) {
              edges {
                node {
                  fullAddress
                  city
                  state
                }
              }
            }
            registeredEntities(first: 5) {
              edges {
                node {
                  name
                  registeredEntityType
                  formationYear
                  registrations(first: 5) {
                    edges {
                      node {
                        registrationState
                        status
                        jurisdictionType
                        fileNumber
                        roles(first: 20) {
                          edges {
                            node {
                              jobTitle
                              jobFunction
                              managementLevel
                              legalEntities(first: 3) {
                                edges {
                                  node {
                                    names(first: 1) {
                                      edges { node { name } }
                                    }
                                    persons(first: 1) {
                                      edges {
                                        node {
                                          names(first: 1) {
                                            edges { node { firstName lastName fullName } }
                                          }
                                        }
                                      }
                                    }
                                    addresses(first: 1) {
                                      edges { node { fullAddress } }
                                    }
                                  }
                                }
                              }
                              emailAddresses(first: 1) {
                                edges { node { emailAddress } }
                              }
                              phoneNumbers(first: 1) {
                                edges { node { phoneNumber } }
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
          }
        }
      }
    }
  }
}
```

## Expected Output Format

**Structured summary with:**
1. Brand overview (name, website)
2. Legal entities table (name, type, TIN, formation year)
3. Officers/roles table per registration (name, title, function, contact info)

**Example:**

```
## Tacombi Corporate Structure

**Brand**: Tacombi
**Website**: https://www.tacombi.com

### Legal Entities

| Legal Entity | Type | TIN | Address | Formation Year |
|---|---|---|---|---|
| TACOS ESPECIALES DEL MERCADO DE FULTON LLC | LLC | XX-XXXXXXX | New York, NY | 2015 |

### Officers & Registered Agents

**Registration (New York, Active)**

| Name | Title | Function | Management Level | Contact |
|---|---|---|---|---|
| JOSHUA OMIN | manager | - | - | - |
| JOHN D WOLOS | manager | - | - | - |
| DIETER WIECHMANN | manager | - | - | - |
| NATIONAL REGISTERED AGENTS, INC | registered agent | - | - | - |
```

## Common Mistakes to Avoid

1. ❌ **Using `LegalEntity.persons` directly on the searched entity to find officers**:
   ```graphql
   legalEntities {
     persons { edges { node { names } } }  // WRONG - usually empty at the top level
   }
   ```
   ✅ Use the registration-roles path; the role's `legalEntities` node carries the person:
   ```graphql
   legalEntities {
     registeredEntities {
       registrations {
         roles {
           legalEntities {
             names { edges { node { name } } }            // person name as LegalEntityName
             persons { edges { node { names { edges { node { firstName lastName fullName } } } } } }
           }
         }
       }
     }
   }
   ```

2. ❌ **Using `Role.title` field**:
   ```graphql
   roles { edges { node { title } } }  // WRONG - field doesn't exist
   ```
   ✅ Use:
   ```graphql
   roles { edges { node { jobTitle } } }  // CORRECT
   ```

3. ❌ **Selecting `type` on the `types` connection node**:
   ```graphql
   types { edges { node { type } } }  // WRONG - field is legalEntityType
   ```
   ✅ Use:
   ```graphql
   types { edges { node { legalEntityType } } }  // CORRECT
   ```

4. ❌ **Expecting `jurisdiction` / `jurisdictionCode` on `Registration`**:
   ```graphql
   registrations { edges { node { jurisdictionCode } } }  // WRONG
   ```
   ✅ Use `registrationState` and `jurisdictionType`:
   ```graphql
   registrations { edges { node { registrationState jurisdictionType } } }  // CORRECT
   ```

## Variations

### Focus on Specific Registration State

```graphql
query ByState($searchInput: SearchInput!, $regConditions: ConnectionConditions) {
  search(searchInput: $searchInput) {
    ... on Brand {
      legalEntities(first: 10) {
        edges {
          node {
            registeredEntities(first: 5) {
              edges {
                node {
                  registrations(first: 5, conditions: $regConditions) {
                    edges { node { registrationState status jurisdictionType fileNumber } }
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
  "searchInput": { "name": "Tacombi", "entityType": "BRAND" },
  "regConditions": {
    "filter": { "EQ": ["registrationState", "NY"] }
  }
}
```

> Note: `registrations` connection conditions use type `ConnectionConditions` ( `{ filter, orderBy }` — no `limit`/`pageToken` ).

### Include Watchlist Screening

```graphql
legalEntities(first: 5) {
  edges {
    node {
      names(first: 1) { edges { node { name } } }
      isFlaggedByWatchlistEntries(first: 5) {
        edges {
          node { watchlistName }
        }
      }
      appearsOnWatchlistEntries(first: 5) {
        edges {
          node { watchlistName }
        }
      }
    }
  }
}
```

> `WatchlistEntry` exposes `watchlistName` (there is no `entityName`). These connections are legitimately empty for clean entities.

### Check for Bankruptcies

```graphql
legalEntities(first: 5) {
  edges {
    node {
      names(first: 1) { edges { node { name } } }
      bankruptcies(first: 5) {
        edges {
          node {
            caseNumber
            filingDate
            chapterType
          }
        }
      }
    }
  }
}
```

## Python Execution Template

```bash
python3 << 'PYEOF'
import json, urllib.request, os

query = '''query CorporateStructure($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on Brand {
      id
      names(first: 1) { edges { node { name } } }
      legalEntities(first: 10) {
        edges {
          node {
            names(first: 1) { edges { node { name } } }
            types(first: 1) { edges { node { legalEntityType } } }
            tins(first: 1) { edges { node { tin } } }
            registeredEntities(first: 5) {
              edges {
                node {
                  name
                  registeredEntityType
                  formationYear
                  registrations(first: 5) {
                    edges {
                      node {
                        registrationState
                        status
                        roles(first: 20) {
                          edges {
                            node {
                              jobTitle
                              legalEntities(first: 3) {
                                edges {
                                  node {
                                    names(first: 1) {
                                      edges { node { name } }
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
                }
              }
            }
          }
        }
      }
    }
  }
}'''

variables = {
  "searchInput": {
    "name": "Tacombi",
    "entityType": "BRAND"
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

## Related Queries

- **Person search**: Use `PERSON` entity type with `person: { firstName, lastName }` to find a specific person, then traverse their companies
- **Watchlist screening**: Check `isFlaggedByWatchlistEntries` and `appearsOnWatchlistEntries` connections
- **Cannabis licenses**: Use `cannabisLicenses` connection on `LegalEntity`
- **Negative news**: Use `negativeNewses` connection on `LegalEntity`
