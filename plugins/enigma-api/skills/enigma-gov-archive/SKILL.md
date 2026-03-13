---
name: enigma-gov-archive
description: Search government archive public records using the Enigma Gov Archive MCP. Use when the user wants to find violations, licenses, liens, legal actions, debarments, contracts, or other government records for a business.
---

# Enigma Gov Archive MCP Skill

You are an expert at searching government archive public records using the Enigma Gov Archive service via MCP protocol.

## API Basics

- **Endpoint**: `POST https://mcp.enigma.com/http-key`
- **Auth**: `x-api-key` header — user must have `ENIGMA_API_KEY` set
- **Protocol**: JSON-RPC 2.0, method `tools/call`, tool name `search_gov_archive`
- **NEVER use curl** — the API key contains characters that break shell argument parsing. Always use Python `urllib`.
- **ALWAYS use heredoc** — `python3 << 'PYEOF'` (NOT `python3 -c`) to avoid `$` escaping issues.

## Request Format

```json
{
  "jsonrpc": "2.0",
  "id": "unique-uuid",
  "method": "tools/call",
  "params": {
    "name": "search_gov_archive",
    "arguments": {
      "query": "Business Name",
      "page": 1
    }
  }
}
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | string | null | Search string applied across business name and address fields |
| `page` | int | 1 | Page number for pagination. Each page returns up to 250–300 records. |
| `historical_data` | bool | false | Include historical/archived records. **Rarely needed** — only use when the user specifically wants older records. |

## Response Format

The response follows MCP JSON-RPC format. The `result.content` array contains text blocks with JSON data:

```json
{
  "jsonrpc": "2.0",
  "id": "uuid",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"hits\": [{\"dataset_info\": {...}, \"matched_row_info\": {...}}]}"
      }
    ]
  }
}
```

**IMPORTANT**: The `text` field is a JSON string — parse it with `json.loads(block['text'])`.

### Hit Structure

Each hit contains:
- **`dataset_info`**: metadata about the source dataset
  - `dataset_title`: human-readable dataset name (e.g., "Business Licenses", "Food Inspections")
  - `dataset_organization`: source government agency (e.g., "City of San Francisco", "State of Washington")
  - `last_updated_at`: Unix timestamp of last data update
- **`matched_row_info`**: the actual record data
  - `business_name`: matched business name
  - `business_name_2`: secondary/alternate name
  - `phone_number`, `city`, `state`, `zip_code`, `street_address`: contact details (when available)
  - `row_details`: full record with all dataset-specific fields (JSON object)

### Common Dataset Types

| Dataset Title | What it contains |
|---|---|
| Business Licenses / Basic Business Licenses | Active and historical business licenses |
| Food Inspections / Food Establishment Inspection Data | Health inspection results, violations |
| Fire Permits / Fire Code Compliance Permit | Fire safety permits and compliance |
| Building Permits | Construction and demolition permits |
| Transportation Department Permits | Street use, hauling, transport permits |
| Lobbyist Reporting History | Lobbying activity records |
| DCWP Inspections | Consumer/worker protection inspections |

## Execution Template

**Always check for the API key first**, then use this template:

```bash
python3 << 'PYEOF'
import json, urllib.request, os, uuid

body = {
    'jsonrpc': '2.0',
    'id': str(uuid.uuid4()),
    'method': 'tools/call',
    'params': {
        'name': 'search_gov_archive',
        'arguments': {
            'query': 'BUSINESS_NAME'
            # Optional: 'page': 2, 'historical_data': True
        }
    }
}

payload = json.dumps(body)
req = urllib.request.Request(
    'https://mcp.enigma.com/http-key',
    data=payload.encode(),
    headers={
        'content-type': 'application/json',
        'accept': 'application/json, text/event-stream',
        'x-api-key': os.environ['ENIGMA_API_KEY']
    }
)
try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())

    if 'error' in data:
        print(f'Error: {data["error"].get("message", data["error"])}')
    else:
        content = data.get('result', {}).get('content', [])
        for block in content:
            if block.get('type') == 'text':
                parsed = json.loads(block['text'])
                hits = parsed.get('hits', [])
                print(f'Found {len(hits)} records\n')

                # Group by dataset
                by_dataset = {}
                for hit in hits:
                    title = hit.get('dataset_info', {}).get('dataset_title', 'Unknown')
                    by_dataset.setdefault(title, []).append(hit)

                for title, records in by_dataset.items():
                    org = records[0].get('dataset_info', {}).get('dataset_organization', 'N/A')
                    print(f'{title} ({org}): {len(records)} records')
                    for r in records[:3]:
                        row = r.get('matched_row_info', {})
                        name = row.get('business_name', 'N/A')
                        addr = ', '.join(filter(None, [row.get('street_address'), row.get('city'), row.get('state')]))
                        print(f'  {name} — {addr}')
                    if len(records) > 3:
                        print(f'  ... and {len(records)-3} more')
                    print()

except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.read().decode()}')
except KeyError:
    print('ERROR: ENIGMA_API_KEY not set. Run: export ENIGMA_API_KEY=your_key')
PYEOF
```

## Recipes

### Basic Public Records Search

```python
arguments = {'query': 'Acme Corp'}
```

### Paginated Search (Large Result Sets)

Each page returns up to ~250 records. Fetch multiple pages:

```python
# Page 1
arguments = {'query': 'Starbucks', 'page': 1}
# Page 2
arguments = {'query': 'Starbucks', 'page': 2}
```

### Include Historical Records

Only when the user specifically needs older/archived data:

```python
arguments = {'query': 'Blue Bottle Coffee', 'historical_data': True}
```

## Workflow

1. **Check API key**: `python3 -c "import os; print('OK' if os.environ.get('ENIGMA_API_KEY') else 'ERROR: set ENIGMA_API_KEY')"`
2. **Build the request** — use the business name as `query`
3. **Execute** via the execution template (NEVER curl, ALWAYS heredoc)
4. **Parse the response** — `result.content[].text` is a JSON string that needs `json.loads()`
5. **Group by dataset** — records come from many different government sources
6. **Page if needed** — if you get ~250 results, there are likely more pages
7. **Present results** — group by dataset/source, show record counts

## Formatting Rules

- **Summary**: "Found X government records across Y datasets for [business]"
- **Records**: Group by dataset title and source organization
- **Per dataset**: Show record count, source org, and top 3 examples
- **Row details**: Extract the most relevant fields from `row_details` (varies by dataset)
- **Empty results**: "No government archive records found for [business]"
- **Large result sets**: Show page 1 summary, offer to fetch more pages

## Error Handling

| Error | Cause | Fix |
|---|---|---|
| HTTP 401/403 | Bad/missing API key | Check `ENIGMA_API_KEY` |
| JSON-RPC error | Invalid method or params | Check `method` is `tools/call`, `params.name` is `search_gov_archive` |
| Empty hits | No records found | Try alternative business name spelling or broader search |
| Parse error on content | Response text is not valid JSON | Check `block['text']` is a JSON string before parsing |
