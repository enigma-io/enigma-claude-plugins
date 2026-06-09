# KYB Full Verification: TINs, Watchlists, Bankruptcies, Officers

## User Intent

Verify a business for compliance — check registrations, TIN validity, watchlist screening, bankruptcies, and look up officers.

## Key Concepts

- Use `entityType: LEGAL_ENTITY` with `name` (+ optional `address.state`)
- TINs include `validity` field for verification status (NOT `tinStatus`)
- Officers are on `Registration.roles`, NOT `LegalEntity.persons` (usually empty)
- Filter out registered agents/applicants/unknown — they're service providers, not officers
- `search` returns `[SearchUnion]` — select with `__typename` + `... on LegalEntity`. Every nested field is a Relay connection (`field(first: N) { edges { node { ... } } }`).
- `WatchlistEntry` exposes only `watchlistName`. `RegisteredEntity` has BOTH `formationYear` (Int) and `formationDate` (Date).

---

## KYB Verification Query

```graphql
query KYBVerify($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on LegalEntity {
      id
      names(first: 5) { edges { node { name } } }
      types(first: 5) { edges { node { legalEntityType } } }
      tins(first: 5) { edges { node { tin tinType validity } } }
      addresses(first: 3) { edges { node { fullAddress } } }
      registeredEntities(first: 5) {
        edges {
          node {
            name
            registeredEntityType
            formationYear
            formationDate
            registrations(first: 5) {
              edges {
                node {
                  registrationState
                  jurisdictionType
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
      isFlaggedByWatchlistEntries(first: 5) {
        edges { node { watchlistName } }
      }
      appearsOnWatchlistEntries(first: 5) {
        edges { node { watchlistName } }
      }
      bankruptcies(first: 5) {
        edges { node { caseNumber filingDate chapterType debtorName dateTerminated } }
      }
    }
  }
}
```

```json
{
  "searchInput": {
    "name": "Sweetgreen",
    "entityType": "LEGAL_ENTITY"
  }
}
```

> Compliance connections (`tins`, watchlists, `bankruptcies`) legitimately return empty edges for clean entities — that is a valid, error-free result.

---

## KYB Officers Query

**IMPORTANT**: `LegalEntity.persons` is usually EMPTY. People are found on **registration records** via roles. Individuals (e.g., "Hicham Oudghiri") are modeled as `LegalEntity` nodes linked to `Registration` records via `Role` edges.

The traversal path is: `LegalEntity → registeredEntities → registrations → roles → legalEntities → names` (and, for structured person names, `→ legalEntities → persons → names { firstName lastName fullName }`).

```graphql
query KYBOfficers($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    __typename
    ... on LegalEntity {
      id
      names(first: 3) { edges { node { name } } }
      registeredEntities(first: 5) {
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
                              names(first: 1) { edges { node { name } } }
                              persons(first: 1) {
                                edges {
                                  node {
                                    names(first: 1) {
                                      edges { node { firstName lastName fullName } }
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
}
```

```json
{
  "searchInput": {
    "name": "Tacombi",
    "entityType": "LEGAL_ENTITY"
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

1. **Using `LegalEntity.persons` on the searched entity to find officers** — usually empty at the top level. Traverse via registration roles, then read the role's `legalEntities` (and its `persons`).
2. **Assuming `homeJurisdictionState` identifies the home state** — it's always null on domestic registrations. Find the domestic registration first.
3. **Showing all registrations equally** — distinguish domestic (home) from foreign (authorized in other states).
4. **Including registered agents as officers** — they're service providers, not company officers.
5. **Using `jurisdictionCode` or `jurisdiction` on `Registration`** — the fields are `registrationState` and `jurisdictionType`.
6. **Selecting `type` on `types` or `tinStatus` on `tins`** — use `legalEntityType` and `validity`. `WatchlistEntry` has only `watchlistName` (no `entityName`/`watchlistEntryId`).
