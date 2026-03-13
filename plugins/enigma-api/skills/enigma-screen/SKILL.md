---
name: enigma-screen
description: Screen persons and organizations against sanctions and PEP lists using the Enigma Screen API. Use ONLY when the user explicitly asks for compliance screening, sanctions checks, watchlist checks, or PEP screening — NOT for general person/business search or lookup.
---

# Enigma Screen API Skill

You are an expert at screening entities against sanctions, PEP, and watchlist databases using the Enigma Screen API.

## API Basics

- **Endpoint**: `POST https://api.enigma.com/evaluation/sanctions/screen`
- **Auth**: `x-api-key` header + `Account-Name: public_evaluation` — user must have `ENIGMA_API_KEY` set
- **Method**: POST with `Content-Type: application/json`
- **NEVER use curl** — the API key contains characters that break shell argument parsing. Always use Python `urllib`.
- **ALWAYS use heredoc** — `python3 << 'PYEOF'` (NOT `python3 -c`) to avoid `$` escaping issues.

## Request Format

### Entity Search (Person or Organization)

```json
{
  "tag": "claude-screen",
  "searches": [
    {
      "type": "ENTITY",
      "entity_description": {
        "person_name": ["John Smith"],
        "org_name": ["Acme Corp"],
        "dob": ["1980-01-15"],
        "address": ["123 Main St, New York, NY"],
        "country_of_affiliation": ["US"]
      }
    }
  ]
}
```

- `tag` is **required** — use a descriptive label
- `searches` array — at least one search required
- `type`: `"ENTITY"` for person/org searches, `"TEXT"` for free-text searches
- `entity_description` fields are **arrays** (support multiple values per field)
- For persons: use `person_name`
- For organizations: use `org_name`
- You can search multiple entities in one request by adding more items to `searches`

### Text Search

```json
{
  "tag": "claude-screen",
  "searches": [
    {
      "type": "TEXT",
      "text": "John Smith Acme Corp"
    }
  ]
}
```

**IMPORTANT**: The `text` field is a plain string, NOT a nested object.

### Configuration Overrides (Optional)

All thresholds are **0–1 floats** (not 0–100).

```json
{
  "tag": "claude-screen",
  "configuration_overrides": {
    "entity": {
      "alert_threshold": 0.8,
      "hit_threshold": 0.5,
      "max_results": 10,
      "weights": {
        "person_name": 3.0,
        "dob": 2.0,
        "country_of_affiliation": 1.0,
        "address": 1.0,
        "org_name": 3.0,
        "passport_number": 1.0
      }
    },
    "list_groups": ["OFAC", "EU", "UN"]
  },
  "searches": [...]
}
```

**Defaults** (from API): `alert_threshold: 0.8`, `hit_threshold: 0.5`, `max_results: 30`.

## Response Format

### ENTITY Hit Structure

```json
{
  "alert": true,
  "attributes": {
    "person_name": {
      "id": "sn-6",
      "score": 1.0,
      "value": "VLADIMIR PUTIN",
      "view_ids": ["pos/sdn/all"]
    }
  },
  "attributes_used": ["person_name", "country_of_affiliation"],
  "entity": { "id": "ofac/sdn/35096" },
  "score": 0.75
}
```

### TEXT Hit Structure

TEXT hits have a **different schema** — no `attributes`/`entity`, uses `entity_attribute` and `span` instead:

```json
{
  "alert": true,
  "score": 1.0,
  "entity_attribute": {
    "attribute_id": "sn-7",
    "attribute_type": "ORG_NAME",
    "attribute_value": "BANK OF RUSSIA",
    "entity_id": "ofac/non_sdn/31695",
    "view_id": "pos/non_sdn/all"
  },
  "span": {
    "begin": 30,
    "end": 44,
    "snippet": "BANK OF RUSSIA"
  }
}
```

### Top-Level Response

```json
{
  "alert": true,
  "request_id": "uuid",
  "request_timestamp": "2026-02-09T...",
  "configuration_used": { "entity": { "alert_threshold": 0.8, ... } },
  "search_results": [...]
}
```

### Key Fields

| Field | Type | Description |
|---|---|---|
| `alert` (top-level) | bool | `true` if ANY search triggered an alert |
| `search_results[].alert` | bool | `true` if this search triggered an alert |
| `hits[].score` | 0–1 float | Match confidence (1.0 = exact) |
| `hits[].alert` | bool | Whether this hit exceeds the alert threshold |
| **ENTITY hits** | | |
| `hits[].entity.id` | string | Watchlist entity ID (e.g., `ofac/sdn/35096`) |
| `hits[].attributes.<field>.value` | string | Matched name on the watchlist |
| `hits[].attributes.<field>.score` | 0–1 float | Per-attribute match score |
| `hits[].attributes_used` | array | Which input fields contributed to match |
| **TEXT hits** | | |
| `hits[].entity_attribute.attribute_value` | string | Matched watchlist entry name |
| `hits[].entity_attribute.attribute_type` | string | `PERSON_NAME` or `ORG_NAME` |
| `hits[].entity_attribute.entity_id` | string | Watchlist entity ID |
| `hits[].span.snippet` | string | Matched text span from input |
| `hits[].span.begin` / `end` | int | Character offsets in input text |

## Execution Template

**Always check for the API key first**, then use this template:

```bash
python3 << 'PYEOF'
import json, urllib.request, os

body = {
    'tag': 'claude-screen',
    'searches': [
        {
            'type': 'ENTITY',
            'entity_description': {
                'person_name': ['PERSON_NAME']  # or 'org_name': ['ORG_NAME']
            }
        }
    ]
}

payload = json.dumps(body)
req = urllib.request.Request(
    'https://api.enigma.com/evaluation/sanctions/screen',
    data=payload.encode(),
    headers={
        'content-type': 'application/json',
        'x-api-key': os.environ['ENIGMA_API_KEY'],
        'Account-Name': 'public_evaluation'
    }
)
try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())

    print(f'Alert: {data.get("alert", False)}')
    print(f'Request ID: {data.get("request_id")}')

    for i, result in enumerate(data.get('search_results', [])):
        search_type = result.get('type')
        print(f'\nSearch {i+1}: alert={result.get("alert", False)}, type={search_type}')
        hits = result.get('hits', [])
        if not hits:
            print('  No hits')
        for hit in hits:
            score = hit.get('score', 0)
            is_alert = hit.get('alert', False)

            if search_type == 'TEXT':
                # TEXT hits use entity_attribute + span
                ea = hit.get('entity_attribute', {})
                span = hit.get('span', {})
                print(f'  Score: {score:.2f} | Alert: {is_alert} | "{span.get("snippet", "N/A")}" -> {ea.get("attribute_value", "N/A")} ({ea.get("attribute_type", "N/A")})')
                print(f'    Entity: {ea.get("entity_id", "N/A")} | List: {ea.get("view_id", "N/A")}')
            else:
                # ENTITY hits use attributes + entity
                entity_id = hit.get('entity', {}).get('id', 'N/A')
                attrs = hit.get('attributes', {})
                matched_name = 'N/A'
                for key in ('person_name', 'org_name'):
                    if key in attrs:
                        matched_name = attrs[key].get('value', 'N/A')
                        break
                attrs_used = ', '.join(hit.get('attributes_used', []))
                print(f'  Score: {score:.2f} | Alert: {is_alert} | Matched: {matched_name}')
                print(f'    Entity: {entity_id} | Matched on: {attrs_used}')

except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.read().decode()}')
except KeyError:
    print('ERROR: ENIGMA_API_KEY not set. Run: export ENIGMA_API_KEY=your_key')
PYEOF
```

## Recipes

### Screen a Person

```python
body = {
    'tag': 'claude-screen',
    'searches': [{
        'type': 'ENTITY',
        'entity_description': {
            'person_name': ['Vladimir Putin'],
            'country_of_affiliation': ['RU']
        }
    }]
}
```

### Screen an Organization

```python
body = {
    'tag': 'claude-screen',
    'searches': [{
        'type': 'ENTITY',
        'entity_description': {
            'org_name': ['Acme International Trading']
        }
    }]
}
```

### Free-Text Screening

Useful when you have unstructured text mentioning entities:

```python
body = {
    'tag': 'claude-screen',
    'searches': [{
        'type': 'TEXT',
        'text': 'Payment to Vladimir Putin via Bank of Russia'
    }]
}
```

### Screen Multiple Entities at Once

```python
body = {
    'tag': 'claude-screen',
    'searches': [
        {
            'type': 'ENTITY',
            'entity_description': {'person_name': ['John Smith']}
        },
        {
            'type': 'ENTITY',
            'entity_description': {'org_name': ['Smith Trading LLC']}
        }
    ]
}
```

### Fine-Tune with Configuration Overrides

Lower thresholds to catch more potential matches, or raise them to reduce false positives. **All thresholds are 0–1 floats.**

```python
body = {
    'tag': 'claude-screen',
    'configuration_overrides': {
        'entity': {
            'alert_threshold': 0.7,   # Lower = more alerts (default 0.8)
            'hit_threshold': 0.3,     # Lower = more hits returned (default 0.5)
            'max_results': 20         # Default 30
        },
        'list_groups': ['OFAC']       # Restrict to specific lists
    },
    'searches': [{
        'type': 'ENTITY',
        'entity_description': {'person_name': ['John Smith']}
    }]
}
```

## Workflow

1. **Check API key**: `python3 -c "import os; print('OK' if os.environ.get('ENIGMA_API_KEY') else 'ERROR: set ENIGMA_API_KEY')"`
2. **Determine search type** — person (`person_name`), organization (`org_name`), or free text (`TEXT`)
3. **Build the request** — include all known details for better matching
4. **Execute** via the execution template (NEVER curl, ALWAYS heredoc)
5. **Check `alert` field** — if `true`, the entity matched a watchlist
6. **Review hits** — sort by score, show matched names and list IDs
7. **Present results** — clear ALERT/CLEAR status, then hit details

## Formatting Rules

- **Alert status**: Show "ALERT — matched N watchlist entries" or "CLEAR — no watchlist matches" prominently
- **Hits**: Table with score (0–1), alert status, matched name, entity ID, and list source
- **Multiple searches**: Group results by search, label each
- **No hits**: "No watchlist matches found for [name]"
- **Low-score hits**: Note that scores below 0.8 may be false positives
- **Entity IDs**: Format like `ofac/sdn/35096` tells you the source list (OFAC SDN, OFAC non-SDN, etc.)

## Error Handling

| Error | Cause | Fix |
|---|---|---|
| HTTP 403 | Bad/missing API key | Check `ENIGMA_API_KEY` |
| HTTP 400 | Malformed request | Check `tag` is set, `searches` is non-empty, `type` is `ENTITY` or `TEXT` |
| HTTP 400 (thresholds) | Thresholds out of range | Must be 0–1 floats, NOT 0–100 |
| HTTP 400 (text) | Wrong TEXT format | `text` must be a plain string, not `{"text": "..."}` |
| Empty hits | No matches | Entity is not on any screened lists — this is a good result |
