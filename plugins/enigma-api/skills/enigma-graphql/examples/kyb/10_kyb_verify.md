# KYB Full Verification: TINs, Watchlists, Bankruptcies, Officers

## User Intent

Verify a business for compliance — check registrations, TIN validity, watchlist screening, bankruptcies, and look up officers.

## Key Concepts

- Use `entityType: LEGAL_ENTITY` with `name` (+ optional `address.state`)
- TINs include `validity` field for verification status
- Officers are on `Registration.roles`, NOT `LegalEntity.persons` (usually empty)
- Filter out registered agents/applicants/unknown — they're service providers, not officers

---

## KYB Verification Query

```graphql
query KYBVerify($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on LegalEntity {
      id
      names { edges { node { name } } }
      types { edges { node { type } } }
      tins { edges { node { tin tinType validity } } }
      addresses { edges { node { fullAddress } } }
      registeredEntities {
        edges {
          node {
            name
            registeredEntityType
            formationYear
            registrations(first: 5) {
              edges {
                node {
                  jurisdictionCode
                  registrationState
                  fileNumber
                  status
                  registrationType
                  issueDate
                  homeJurisdictionState
                }
              }
            }
          }
        }
      }
      isFlaggedByWatchlistEntries {
        edges { node { watchlistName watchlistEntryId } }
      }
      appearsOnWatchlistEntries {
        edges { node { watchlistName watchlistEntryId } }
      }
      bankruptcies {
        edges { node { caseNumber filingDate chapterType debtorName dateTerminated } }
      }
    }
  }
}
```

```json
{
  "searchInput": {
    "name": "Acme Corp",
    "entityType": "LEGAL_ENTITY",
    "address": { "state": "IL" }
  }
}
```

---

## KYB Officers Query

**IMPORTANT**: `LegalEntity.persons` is usually EMPTY. People are found on **registration records** via roles. Individuals (e.g., "Hicham Oudghiri") are modeled as `LegalEntity` nodes linked to `Registration` records via `Role` edges.

The traversal path is: `LegalEntity → registeredEntities → registrations → roles → legalEntities → names`

```graphql
query KYBOfficers($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on LegalEntity {
      id
      names { edges { node { name } } }
      registeredEntities {
        edges {
          node {
            name
            registeredEntityType
            formationYear
            registrations(first: 10) {
              edges {
                node {
                  registrationState
                  fileNumber
                  status
                  registrationType
                  roles(first: 50) {
                    edges {
                      node {
                        jobTitle
                        jobFunction
                        managementLevel
                        legalEntities(first: 3) {
                          edges {
                            node {
                              names { edges { node { name } } }
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

```json
{
  "searchInput": {
    "name": "Enigma Technologies Inc",
    "entityType": "LEGAL_ENTITY",
    "address": { "state": "NY" }
  }
}
```

---

## Interpreting Registration Data

A single legal entity can have dozens of registrations across states (e.g., Target Corporation has 46). Not all registrations are equal — distinguish **domestic** (home state) from **foreign** (authorized to do business in another state).

### Finding the Domestic Registration

1. Look for "domestic" (case-insensitive) in `registrationType` — e.g., `"Business Corporation (Domestic)"`
2. If no match, fall back to the first registration returned
3. Note: `registrationType` labels vary wildly by state — FL uses "Foreign for Profit", WY and MS use just "Profit Corporation" (no domestic/foreign indicator), CT uses "Stock", SC uses "Corporation"

### Determining Home State

1. If you found the domestic registration, its `registrationState` IS the home state — done
2. Only if you could not identify the domestic registration (no `registrationType` contains "domestic"), check `homeJurisdictionState` on any other registration as a fallback
3. `homeJurisdictionState` is **always null on domestic registrations** — it is only populated on foreign registrations, where it points back to the home state (e.g., Target's CA foreign registration has `homeJurisdictionState: "MN"`)

### Presenting Results

Show the domestic registration prominently (state, status, issue date). Summarize foreign registrations as a count or list of states, not individual detail rows.

---

## Filtering Officers vs Service Providers

Roles with `jobTitle` of `registered agent`, `applicant`, or `unknown` are typically corporate service providers, not actual officers. Filter these out when presenting results.

**Officer titles**: `chief executive officer`, `ceo`, `president`, `governor`, `director`, `secretary`, `chief financial officer`, `vp of finance`, etc.

**Service provider titles** (exclude): `registered agent`, `applicant`, `unknown`

---

## Common Mistakes to Avoid

1. **Using `LegalEntity.persons` to find officers** — usually empty. Traverse via registration roles.
2. **Assuming `homeJurisdictionState` identifies the home state** — it's always null on domestic registrations. Find the domestic registration first.
3. **Showing all registrations equally** — distinguish domestic (home) from foreign (authorized in other states).
4. **Including registered agents as officers** — they're service providers, not company officers.
