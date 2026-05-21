# enigma-api

Query Enigma APIs — GraphQL business data, KYB verification, and sanctions screening. Claude automatically uses the appropriate skill based on what you're asking about.

## Installation

```
/plugin install enigma-api@enigma-plugins
```

## Prerequisites

Set your Enigma API key in your environment:

```bash
export ENIGMA_API_KEY=your_api_key_here
```

Get your API key from [console.enigma.com](https://console.enigma.com/).

## Skills

### enigma-graphql

Query the Enigma GraphQL API for business intelligence data — brands, operating locations, legal entities, corporate structure, and more.

```
"Look up Starbucks in the Enigma API"
"Find all operating locations for Target in California"
"Search for the legal entity behind Acme Corp"
"Get the corporate structure for Nike"
```

### enigma-kyb

Verify businesses using the KYB (Know Your Business) API — check registration status, name verification, and due diligence.

```
"Verify Enigma Technologies Inc as a business"
"Run KYB on Acme Corp in New York"
"Check if this business is registered: Smith & Sons LLC, 123 Main St, Chicago IL"
```

### enigma-screen

Screen persons and organizations against sanctions, PEP, and watchlist databases.

```
"Screen Vladimir Putin for sanctions"
"Check if Acme International Trading is on any watchlists"
"Run a sanctions screening on John Smith"
"Screen this text for sanctioned entities: 'Payment to Bank of Russia'"
```

## Supported Entity Types (GraphQL)

| Type | What it represents |
|---|---|
| Brand | A business brand/company — industries, locations, revenue signals |
| Operating Location | A physical business location — address, phone, status, reviews |
| Legal Entity | A registered legal entity — officers, TINs, filings, registrations |
| Person | A person — associated companies, officer roles, registrations |

## Documentation

- [Enigma API Docs](https://documentation.enigma.com/)
- [GraphQL Guide](https://documentation.enigma.com/guides/graphql)
- [API Playground](https://console.enigma.com/explore/graphql)

## Author

Jarrod Parker
