# Discovery: Find Locations by Industry Label (OPERATING_LOCATION)

## User Intent

Find all business locations of a specific industry type in a city/state, with precise category matching.

## Key Concepts

- Use `entityType: OPERATING_LOCATION` with `brands.industries.industryDesc` filter
- Pair with `brands.industries.industryType` = `enigma_industry_description` for Enigma's semantic labels
- Add `output: { filename }` to trigger background export for large result sets
- Alternative to BRAND+prompt — more precise but requires knowing the exact Enigma industry label

---

## OL Industry Discovery Query

```graphql
query Search {
  search(searchInput: {
    conditions: {
      limit: 10
      filter: { AND: [
        { EQ: ["brands.industries.industryType", "enigma_industry_description"] }
        { IN: ["brands.industries.industryDesc", ["nail salon"]] }
        { IN: ["addresses.state", ["CO"]] }
        { IN: ["addresses.city", ["DENVER"]] }
        { IN: ["operatingStatuses.operatingStatus", ["Open"]] }
      ]}
    }
    entityType: OPERATING_LOCATION
  }) {
    ... on OperatingLocation {
      locationNames: names(first: 1) { edges { node { name } } }
      brandNames: brands(first: 1) {
        edges { node { names(first: 1) { edges { node { name } } } } }
      }
      locationAddress: addresses(first: 1) { edges { node { fullAddress } } }
      locationOperatingStatus: operatingStatuses(first: 1) {
        edges { node { operatingStatus lastObservedDate } }
      }
      locationWebsites: websites(first: 1) { edges { node { website } } }
      brandWebsites: brands(first: 1) {
        edges { node { websites(first: 1) { edges { node { website } } } } }
      }
      locationPhones: phoneNumbers(first: 1) { edges { node { phoneNumber } } }
      locationCardRevenue: cardTransactions(first: 1, conditions: { filter: { AND: [
        { EQ: ["period", "12m"] }
        { EQ: ["quantityType", "card_revenue_amount"] }
        { EQ: ["rank", 0] }
      ]}}) {
        edges { node { projectedQuantity periodEndDate } }
      }
      brandCardRevenue: brands(first: 1) {
        edges { node { cardTransactions(first: 1, conditions: { filter: { AND: [
          { EQ: ["period", "12m"] }
          { EQ: ["quantityType", "card_revenue_amount"] }
          { EQ: ["rank", 0] }
          { IS_NULL: ["platformBrandId"] }
        ]}}) { edges { node { projectedQuantity periodEndDate } } } } }
      }
    }
  }
}
```

---

## With Background Export

For large result sets, add `output: { filename }` to trigger an S3 export instead of inline results:

```graphql
query Search {
  search(searchInput: {
    output: { filename: "nail_salons_in_denver_co" }
    conditions: {
      limit: 10
      filter: { AND: [
        { EQ: ["brands.industries.industryType", "enigma_industry_description"] }
        { IN: ["brands.industries.industryDesc", ["nail salon"]] }
        { IN: ["addresses.state", ["CO"]] }
        { IN: ["addresses.city", ["DENVER"]] }
        { IN: ["operatingStatuses.operatingStatus", ["Open"]] }
      ]}
    }
    entityType: OPERATING_LOCATION
  }) {
    ... on OperatingLocation {
      locationNames: names(first: 1) { edges { node { name } } }
      locationAddress: addresses(first: 1) { edges { node { fullAddress } } }
    }
  }
}
```

**When `output` is provided**: Response is `{ "data": { "search": null }, "extensions": { "backgroundTasks": [{ "status": "SUCCESS", "result": ["https://...signed-s3-url..."] }] } }`. Download the result from the S3 URL.

---

## BRAND+prompt vs OPERATING_LOCATION+industry

| Approach | When to Use | Pros | Cons |
|---|---|---|---|
| `BRAND` + `prompt` | Semantic discovery ("trendy coffee shop") | Flexible, interprets intent | May return adjacent categories |
| `OL` + `industryDesc` | Precise category matching ("nail salon") | Exact match, location-level data | Must know exact Enigma label |

Use `BRAND` + `prompt` when you want the API to interpret a fuzzy industry description. Use `OPERATING_LOCATION` + `brands.industries.industryDesc` when you know the exact Enigma industry label and want location-level results.

---

## Common Mistakes to Avoid

1. **Forgetting `industryType` filter** — always pair `industryDesc` with `industryType: "enigma_industry_description"`
2. **Using lowercase city names** — cities must be UPPERCASE (e.g., `"DENVER"` not `"Denver"`)
3. **Missing `IS_NULL: ["platformBrandId"]`** on brand-level card revenue (nested inside `brands`)
