---
name: enigma-kyb
description: Verify businesses using the Enigma KYB (Know Your Business) API. Use when the user wants to verify a business identity, check registration status, screen officers, or perform KYB due diligence.
---

# Enigma KYB API Skill

You are an expert at verifying businesses using the Enigma KYB API.

## API Basics

- **Endpoint**: `POST https://api.enigma.com/v2/kyb/`
- **Auth**: `x-api-key` header — user must have `ENIGMA_API_KEY` set
- **Method**: POST with `Content-Type: application/json`
- **NEVER use curl** — the API key contains characters that break shell argument parsing. Always use Python `urllib`.
- **ALWAYS use heredoc** — `python3 << 'PYEOF'` (NOT `python3 -c`) to avoid `$` escaping issues.

## Query Parameters

Append to the URL as `?param=value&param2=value2`:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `package` | string | `verify` | `"identify"` (basic matching + enrichment) or `"verify"` (full compliance validation) |
| `attrs` | string | — | Comma-separated add-on tasks: `watchlist`, `tin_verification`, `ssn_verification` |
| `match_threshold` | number | — | 0–1; filters results by match confidence |
| `top_n` | number | 1 | Max matches to return. **When `top_n > 1`, tasks are excluded from the response.** |

## Request Format

### Single Query (Most Common)

```json
{
  "name": "Business Name",
  "address": {
    "street_address1": "123 Main St",
    "street_address2": "Suite 100",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001"
  },
  "person": {
    "first_name": "John",
    "last_name": "Smith"
  },
  "website": "example.com",
  "tin": "123456789"
}
```

- `name` is **required** — the API returns HTTP 400 without it
- `address` is optional — improves match accuracy. Fields: `street_address1`, `street_address2`, `city`, `state`, `postal_code`. Must include at least one of `city`, `state`, or `postal_code`.
- **IMPORTANT**: Address fields are `street_address1`/`street_address2` (NOT `street_line_1`/`street_line_2`)
- `person` is optional — enables person verification against SoS officer records. Exclude suffixes, initials, honorifics.
- `website` is optional — helps with entity resolution
- `tin` is optional — 9-digit string, no dashes (e.g., `"123456789"` not `"12-3456789"`). Required if using `attrs=tin_verification`.

### Multi-Query Format

For enhanced matching with multiple business identifiers:

```json
{
  "data": {
    "names": ["Enigma Technologies", "Enigma"],
    "addresses": [{
      "street_address1": "245 5th Ave",
      "city": "New York",
      "state": "NY",
      "postal_code": "10016"
    }],
    "persons": [{ "first_name": "Hicham", "last_name": "Oudghiri" }],
    "websites": ["enigma.com"],
    "tins": ["000000000"]
  }
}
```

Limits: `names` max 2, `addresses` max 2, `persons` max 1, `websites` max 1, `tins` max 1.

## Packages

| Feature | Identify | Verify (default) |
|---|---|---|
| Name verification | Yes | Yes |
| Address verification | Yes | Yes |
| SoS name verification | Yes | Yes |
| SoS address verification | Yes | Yes |
| Person verification | — | Yes |
| Domestic registration | — | Yes |
| Registration status/detail fields | — | Yes |
| Jurisdiction type fields | — | Yes |

Both packages return results in under 2 seconds typically.

## Response Format

```json
{
  "response_id": "uuid",
  "risk_summary": {
    "tasks": [
      {
        "task_name": "name_verification",
        "status": "success",
        "result": "name_exact_match",
        "reason": "An input business name exactly matches a business name in any of Enigma's records",
        "sources": [{ "name": "ACME CORP", "match_entity_type": "brand" }]
      }
    ]
  },
  "data": {
    "registered_entities": [...],
    "brands": [...]
  }
}
```

**Top-level keys**: `response_id`, `risk_summary`, `data`. Note: the field is `response_id` (NOT `request_id`).

## Verification Tasks

### Standard Tasks (Included in Packages)

| Task | Package | Possible Results |
|---|---|---|
| `name_verification` | Both | `name_exact_match` (success), `name_match` (success), `name_not_verified` (failure) |
| `sos_name_verification` | Both | `name_exact_match` (success), `name_match` (success), `name_not_verified` (failure) |
| `address_verification` | Both | `address_exact_match` (success), `address_match` (success), `address_not_verified` (failure) |
| `sos_address_verification` | Both | `address_exact_match` (success), `address_match` (success), `address_not_verified` (failure) |
| `person_verification` | Verify | `person_match` (success), `person_not_verified` (failure) |
| `domestic_registration` | Verify | `domestic_active` (success), `domestic_unknown` (success), `domestic_inactive` (failure), `domestic_not_found` (failure) |

### Add-On Tasks (via `attrs` parameter)

| Task | Attr Value | Possible Results |
|---|---|---|
| `tin_verification` | `tin_verification` | `tin_verified` (success), `tin_invalid` (failure), `tin_not_verified` (failure), `not_completed` (failure) |
| `ssn_verification` | `ssn_verification` | `ssn_verified` (success), `ssn_invalid` (failure), `ssn_not_verified` (failure), `not_completed` (failure) |
| `watchlist` | `watchlist` | `watchlist_no_hits` (success), `watchlist_hits` (failure). No `sources` field on this task. |

### Task Sources Structure

Sources vary by task type:
- **Name tasks**: `{ "name": "ACME CORP", "match_entity_type": "brand" }`
- **Address tasks**: `{ "address": { "street_address1": "...", ... }, "match_entity_type": "registered_entity" }`
- **Domestic registration**: `{ "issue_date": "...", "file_number": "...", "registration_state": "...", "registered_name": "..." }`
- **Person verification**: `{ "name": "JOHN SMITH", "match_entity_type": "registered_entity" }`
- **Watchlist**: no sources

## Deriving Verification Status

The API returns individual tasks — derive the overall status:

| Condition | Status |
|---|---|
| `name_verification` or `sos_name_verification` success AND `domestic_registration` result is `domestic_active` | **VERIFIED** |
| `name_verification` or `sos_name_verification` success AND `domestic_registration` result is `domestic_unknown` | **VERIFIED (status unknown)** |
| `name_verification` or `sos_name_verification` success only (no domestic registration) | **PARTIAL_MATCH** |
| Neither name task succeeds | **NOT_FOUND** |

## Response Data Structure

### registered_entities[]

```json
{
  "id": "uuid",
  "formation_date": "2014-07-30",
  "registered_entity_type": "Corporation",
  "names": [{ "name": "ACME CORP" }],
  "brand_ids": ["uuid"],
  "registrations": [...]
}
```

### registrations[] (nested under registered_entities)

```json
{
  "registration_state": "NY",
  "jurisdiction_type": "domestic",
  "home_jurisdiction_state": null,
  "registered_name": "Acme Corp",
  "file_number": "123456",
  "issue_date": "2014-07-30",
  "status": "active",
  "sub_status": null,
  "status_detail": "Active",
  "persons": [{ "name": "JOHN SMITH", "titles": ["chief executive officer"] }],
  "addresses": [{ "street_address1": "...", "city": "...", "state": "...", "postal_code": "...", "type": "registered", "deliverable": "deliverable", "virtual": "not_virtual", "delivery_type": "street", "rdi": "commercial" }]
}
```

**Note**: `jurisdiction_type`, `home_jurisdiction_state`, `status`, `sub_status`, `status_detail` are only present in the **verify** package.

### Address deliverability fields

| Field | Values |
|---|---|
| `type` | `registered`, `mailing`, `officer` |
| `deliverable` | `deliverable`, `not_deliverable`, `vacant` |
| `virtual` | `virtual`, `not_virtual` |
| `delivery_type` | `street`, `multi-tenant building` |
| `rdi` | `commercial`, `residential` |

### brands[]

```json
{
  "id": "uuid",
  "registered_entity_ids": ["uuid"],
  "names": [{ "name": "ACME" }],
  "industries": [{ "classification_description": "...", "classification_type": "naics_2022_code", "classification_code": "..." }],
  "websites": ["https://example.com"],
  "activities": { "activities": [] },
  "operating_locations": [{ "id": "uuid", "addresses": [...], "names": [...] }]
}
```

## Execution Template

**Always check for the API key first**, then use this template:

```bash
python3 << 'PYEOF'
import json, urllib.request, os

body = {
    'name': 'BUSINESS_NAME'
    # Optional: add 'address', 'person', 'website', 'tin' for better matching
    # 'address': { 'street_address1': '...', 'city': '...', 'state': '...', 'postal_code': '...' },
    # 'person': { 'first_name': '...', 'last_name': '...' },
    # 'tin': '123456789'
}

# URL params: add ?package=identify or ?attrs=watchlist,tin_verification as needed
url = 'https://api.enigma.com/v2/kyb/'

payload = json.dumps(body)
req = urllib.request.Request(
    url,
    data=payload.encode(),
    headers={'content-type': 'application/json', 'x-api-key': os.environ['ENIGMA_API_KEY']}
)
try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())

    # Derive verification status
    tasks = data.get('risk_summary', {}).get('tasks', [])
    name_verified = any(
        t['task_name'] in ('name_verification', 'sos_name_verification') and t['status'] == 'success'
        for t in tasks
    )
    has_registration = any(
        t['task_name'] == 'domestic_registration' and t['status'] == 'success'
        for t in tasks
    )

    if name_verified and has_registration:
        status = 'VERIFIED'
    elif name_verified:
        status = 'PARTIAL_MATCH'
    else:
        status = 'NOT_FOUND'

    print(f'Verification Status: {status}')
    print(f'Response ID: {data.get("response_id")}')
    print(f'\nTasks:')
    for t in tasks:
        print(f'  {t["task_name"]}: {t["status"]} -> {t["result"]}')
        print(f'    {t.get("reason", "")}')

    # Show matched entities
    entities = data.get('data', {}).get('registered_entities', [])
    if entities:
        print(f'\nRegistered Entities: {len(entities)}')
        for e in entities:
            names = [n['name'] for n in e.get('names', [])]
            print(f'  {names[0] if names else "N/A"} ({e.get("registered_entity_type", "N/A")})')
            for r in e.get('registrations', []):
                print(f'    {r.get("registration_state")} | {r.get("registered_name")} | status={r.get("status", "N/A")}')

    brands = data.get('data', {}).get('brands', [])
    if brands:
        print(f'\nBrands: {len(brands)}')
        for b in brands:
            names = [n['name'] for n in b.get('names', [])]
            print(f'  {names[0] if names else "N/A"}')

except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.read().decode()}')
except KeyError:
    print('ERROR: ENIGMA_API_KEY not set. Run: export ENIGMA_API_KEY=your_key')
PYEOF
```

## Recipes

### Basic Business Verification

Verify a business by name only (uses verify package by default):

```python
body = {'name': 'Enigma Technologies'}
```

### Verification with Address

Provide address for address verification tasks to pass:

```python
body = {
    'name': 'Enigma Technologies',
    'address': {
        'street_address1': '245 5th Ave',
        'city': 'New York',
        'state': 'NY',
        'postal_code': '10016'
    }
}
```

### Verification with Person (Officer Check)

Verify that a person is listed as an officer on SoS registrations:

```python
body = {
    'name': 'Enigma Technologies',
    'address': {'state': 'NY'},
    'person': {'first_name': 'Hicham', 'last_name': 'Oudghiri'}
}
```

### Full Verification with Watchlist Screening

Use `attrs=watchlist` to add OFAC sanctions screening:

```python
url = 'https://api.enigma.com/v2/kyb/?attrs=watchlist'
body = {
    'name': 'Acme Corp',
    'address': {'state': 'NY'}
}
```

### TIN Verification

Requires the `tin` field in the body AND `attrs=tin_verification`:

```python
url = 'https://api.enigma.com/v2/kyb/?attrs=tin_verification'
body = {
    'name': 'Acme Corp',
    'tin': '123456789'  # 9 digits, no dashes
}
```

### Identify Package (Lighter, Faster)

Use for data enrichment workflows — fewer tasks, no registration status fields:

```python
url = 'https://api.enigma.com/v2/kyb/?package=identify'
body = {'name': 'Starbucks', 'address': {'state': 'WA'}}
```

### Multiple Matches (Discovery)

Return up to N matches — useful for finding the right entity. **Tasks are excluded when `top_n > 1`.**

```python
url = 'https://api.enigma.com/v2/kyb/?top_n=3'
body = {'name': 'Acme', 'address': {'state': 'NY'}}
```

### Multi-Query Format

Provide multiple names and addresses for best match resolution:

```python
body = {
    'data': {
        'names': ['Enigma Technologies', 'Enigma'],
        'addresses': [{
            'street_address1': '245 5th Ave',
            'city': 'New York',
            'state': 'NY',
            'postal_code': '10016'
        }]
    }
}
```

## Workflow

1. **Check API key**: `python3 -c "import os; print('OK' if os.environ.get('ENIGMA_API_KEY') else 'ERROR: set ENIGMA_API_KEY')"`
2. **Choose package** — `verify` (default) for compliance, `identify` for enrichment
3. **Choose add-ons** — `watchlist`, `tin_verification`, `ssn_verification` via `attrs` param
4. **Build the request body** — `name` is required, add `address`, `person`, `tin` for better matches
5. **Execute** via the execution template (NEVER curl, ALWAYS heredoc)
6. **Derive verification status** from `risk_summary.tasks`
7. **Present results** — status summary first, then task details, then matched entities

## Formatting Rules

- **Status summary**: Show VERIFIED / PARTIAL_MATCH / NOT_FOUND prominently
- **Tasks**: Table with task_name, result, and reason
- **Registration details**: State, status, file number, officers
- **Address deliverability**: Note if addresses are non-deliverable, vacant, or virtual
- **Entities**: Structured summary of matched registered entities and brands
- **Empty results**: "No verification data found for [business]. Try a more specific name or add an address."

## Error Handling

| Error | Cause | Fix |
|---|---|---|
| HTTP 403 | Bad/missing API key | Check `ENIGMA_API_KEY` — message is `{"message":"Forbidden"}` |
| HTTP 400 `Provide at least one business name` | Missing `name` field | `name` is required in the request body |
| HTTP 400 `Must provide a TIN for Tin Verification` | `attrs=tin_verification` without `tin` in body | Add `tin` field (9 digits, no dashes) |
| All tasks fail | Name too generic or misspelled | Try more specific name (e.g., "Target Corporation" not "Target"), add state |
| `domestic_unknown` | Registration found but status not provided by SoS | This is still a success — the entity exists but status is unknown |
