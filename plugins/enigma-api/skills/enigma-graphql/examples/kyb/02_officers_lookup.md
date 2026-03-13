# KYB Example: Corporate Officers & Structure Lookup

## User Intent

Look up the corporate structure of a business and find all officers, directors, and registered agents.

## Key Concepts

- Start with `BRAND` entity type using `name` (entity resolution)
- Traverse: `BRAND → legalEntities → registeredEntities → registrations → roles → legalEntities`
- **CRITICAL**: Officers are on `Registration.roles`, NOT `LegalEntity.persons` (which is usually empty)
- People are modeled as `LegalEntity` nodes with `names` connection
- `Role` has `jobTitle`, `jobFunction`, `managementLevel` fields

## Variables

```json
{
  "searchInput": {
    "name": "Nike",
    "entityType": "BRAND"
  }
}
```

## GraphQL Query

```graphql
query CorporateStructure($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      names: names(first: 1) { edges { node { name } } }
      websites: websites(first: 1) { edges { node { website } } }
      legalEntities(first: 10) {
        edges {
          node {
            names: names(first: 1) { edges { node { name } } }
            types: types(first: 1) { edges { node { type } } }
            tins: tins(first: 1) { edges { node { tin } } }
            addresses: addresses(first: 1) {
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
                        jurisdictionCode
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
                                    names: names(first: 1) {
                                      edges {
                                        node {
                                          name
                                        }
                                      }
                                    }
                                    addresses: addresses(first: 1) {
                                      edges {
                                        node {
                                          fullAddress
                                        }
                                      }
                                    }
                                  }
                                }
                              }
                              emailAddresses: emailAddresses(first: 1) {
                                edges {
                                  node {
                                    emailAddress
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
## Nike Corporate Structure

**Brand**: Nike, Inc.
**Website**: https://www.nike.com

### Legal Entities

| Legal Entity | Type | TIN | Address | Formation Year |
|---|---|---|---|---|
| NIKE, Inc. | Corporation | 93-0584541 | One Bowerman Drive, Beaverton, OR | 1964 |
| Nike Retail Services, Inc. | Corporation | XX-XXXXXXX | One Bowerman Drive, Beaverton, OR | 1995 |

### Officers & Registered Agents

**NIKE, Inc. (Oregon Registration #123456)**
- Status: Active

| Name | Title | Function | Management Level | Contact |
|---|---|---|---|---|
| John H. Donahoe II | Chief Executive Officer | executive | C-Level | - |
| Matthew Friend | Chief Financial Officer | finance | C-Level | - |
| Corporation Service Company | Registered Agent | agent | - | (503) 555-0100 |
```

## Common Mistakes to Avoid

1. ❌ **Using `LegalEntity.persons` to find officers**:
   ```graphql
   legalEntities {
     persons { edges { node { names } } }  // WRONG - usually empty
   }
   ```
   ✅ Use:
   ```graphql
   legalEntities {
     registeredEntities {
       registrations {
         roles {
           legalEntities { names }  // CORRECT - people are LegalEntity nodes
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

3. ❌ **Accessing `Person.fullName` directly**:
   ```graphql
   person { fullName }  // WRONG
   ```
   ✅ Use:
   ```graphql
   legalEntities {
     names { edges { node { name } } }  // CORRECT - people are LegalEntity nodes with names connection
   }
   ```

4. ❌ **Expecting `jurisdictionCode` on `RegisteredEntity`**:
   ```graphql
   registeredEntities { jurisdictionCode }  // WRONG
   ```
   ✅ Use:
   ```graphql
   registeredEntities {
     registrations { edges { node { jurisdictionCode } } }  // CORRECT - on Registration
   }
   ```

## Variations

### Focus on Specific Registration State

```graphql
query ByState($searchInput: SearchInput!, $regConditions: ConnectionConditions) {
  search(searchInput: $searchInput) {
    ... on Brand {
      legalEntities {
        registeredEntities {
          registrations(first: 5, conditions: $regConditions) {
            edges { node { ... } }
          }
        }
      }
    }
  }
}
```

```json
{
  "regConditions": {
    "filter": { "EQ": ["registrationState", "DE"] }
  }
}
```

### Include Watchlist Screening

```graphql
legalEntities {
  names { edges { node { name } } }
  isFlaggedByWatchlistEntries {
    edges {
      node {
        watchlistName
      }
      confidence
    }
  }
  appearsOnWatchlistEntries {
    edges {
      node {
        watchlistName
      }
      confidence
    }
  }
}
```

### Check for Bankruptcies

```graphql
legalEntities {
  names { edges { node { name } } }
  bankruptcies {
    edges {
      node {
        caseNumber
        filingDate
        chapterType
        dispositionType
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
    ... on Brand {
      id
      names: names(first: 1) { edges { node { name } } }
      legalEntities(first: 10) {
        edges {
          node {
            names: names(first: 1) { edges { node { name } } }
            types: types(first: 1) { edges { node { type } } }
            tins: tins(first: 1) { edges { node { tin } } }
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
                                    names: names(first: 1) {
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
    "name": "Nike",
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
