# Segment / Bulk Export

Use `output: { filename }` on `SearchInput` for large result sets (hundreds/thousands). The API exports to S3 asynchronously.

## Key Concepts

- Uses `entityType: OPERATING_LOCATION` (not BRAND)
- Industry filtering uses `enigma_industry_description` (not NAICS codes)
- Response comes in `extensions.backgroundTasks`, not `data.search`
- Pre-signed S3 URL expires ~6 days
- Use field aliases for descriptive column names in output

---

## Segment Export Query

```graphql
query SegmentExport($searchInput: SearchInput!) {
  search(searchInput: $searchInput) {
    ... on OperatingLocation {
      locationNames: names(first: 1) { edges { node { locationName: name } } }
      brandNames: brands(first: 1) {
        edges { node { names(first: 1) { edges { node { brandName: name } } } } }
      }
      locationAddress: addresses(first: 1) { edges { node { fullAddress } } }
      legalName1: legalEntities(first: 1) {
        edges { node { registeredEntities(first: 1) { edges { node { legalName1: name } } } } }
      }
      legalName2: brands(first: 1) {
        edges { node { legalEntities(first: 1) { edges { node {
          registeredEntities(first: 1) { edges { node { legalName2: name } } }
        } } } } }
      }
      locationOperatingStatus: operatingStatuses(first: 1) {
        edges { node {
          locationOperatingStatus_operatingStatus: operatingStatus
          locationOperatingStatus_lastObservedDate: lastObservedDate
        } }
      }
      locationWebsites: websites(first: 1) { edges { node { locationWebsite: website } } }
      brandWebsites: brands(first: 1) {
        edges { node { websites(first: 1) { edges { node { brandWebsite: website } } } } }
      }
      locationPhones: phoneNumbers(first: 1) { edges { node { locationPhone: phoneNumber } } }
    }
  }
}
```

```json
{
  "searchInput": {
    "output": { "filename": "nail_salons_in_denver_co" },
    "conditions": {
      "filter": {
        "AND": [
          { "EQ": ["brands.industries.industryType", "enigma_industry_description"] },
          { "IN": ["brands.industries.industryDesc", ["nail salon"]] },
          { "IN": ["addresses.state", ["CO"]] },
          { "IN": ["addresses.city", ["DENVER"]] },
          { "IN": ["operatingStatuses.operatingStatus", ["Open"]] }
        ]
      }
    },
    "entityType": "OPERATING_LOCATION"
  }
}
```

---

## Response Format

`data.search` is `null`. Results appear in `extensions.backgroundTasks`:

```json
{
  "extensions": {
    "backgroundTasks": [{
      "id": "3e3a12a2-...",
      "status": "SUCCESS",
      "result": ["https://...s3.amazonaws.com/tmp/olap_output/nail_salons_in_denver_co/..."]
    }]
  },
  "data": { "search": null }
}
```

---

## Key Patterns

- **Industry filtering**: `EQ: ["brands.industries.industryType", "enigma_industry_description"]` + `IN: ["brands.industries.industryDesc", [...]]` for Enigma's semantic labels. Works with `OPERATING_LOCATION` (unlike `prompt` which requires `BRAND`).
- **Field aliases**: Use GraphQL aliases (e.g., `locationName: name`) for descriptive column names.
- **Dual legal name paths**: Both direct (`legalEntities → registeredEntities`) and via brand for maximum coverage.
- **Download URL**: Pre-signed S3 URL, expires ~6 days. Download promptly.
