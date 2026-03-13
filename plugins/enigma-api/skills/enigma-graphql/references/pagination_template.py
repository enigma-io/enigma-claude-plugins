#!/usr/bin/env python3
"""
Standard pagination template for Enigma GraphQL API connections.

This template handles the cursor pagination bug where the first page query
must NOT declare $cursor as a variable, but subsequent pages must include it.

Usage:
  1. Replace CONNECTION_NAME with the connection you're paginating (e.g., operatingLocations)
  2. Replace NESTED_FIELDS with the fields you want to query
  3. Update the searchInput and conditions variables as needed
  4. Adjust MAX_PAGES if you need more than 3 pages (be careful with runaway fetches)
"""

import json
import urllib.request
import os
import time

MAX_PAGES = 3  # Cap pagination to avoid runaway fetches

# First page query - NO $cursor variable
query_first = '''query Q($searchInput: SearchInput!, $conditions: ConnectionConditions) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      CONNECTION_NAME(first: 100, conditions: $conditions) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            NESTED_FIELDS
          }
        }
      }
    }
  }
}'''

# Subsequent pages query - includes $cursor variable
query_next = '''query Q($searchInput: SearchInput!, $cursor: String, $conditions: ConnectionConditions) {
  search(searchInput: $searchInput) {
    ... on Brand {
      id
      CONNECTION_NAME(first: 100, after: $cursor, conditions: $conditions) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            NESTED_FIELDS
          }
        }
      }
    }
  }
}'''

def fetch(cursor=None):
    """Fetch a page of results."""
    variables = {
        'searchInput': {'name': 'BRAND_NAME', 'entityType': 'BRAND'},
        'conditions': {'filter': {'EQ': ['addresses.state', 'NY']}}  # Optional: remove for unfiltered
    }
    
    if cursor:
        variables['cursor'] = cursor
        q = query_next
    else:
        q = query_first
    
    payload = json.dumps({'query': q, 'variables': variables})
    req = urllib.request.Request(
        'https://api.enigma.com/graphql',
        data=payload.encode(),
        headers={
            'content-type': 'application/json',
            'x-api-key': os.environ['ENIGMA_API_KEY']
        }
    )
    return json.loads(urllib.request.urlopen(req).read())

# Paginate through results
all_items = []
cursor = None
for page in range(1, MAX_PAGES + 1):
    data = fetch(cursor)
    
    # Check for errors
    if 'errors' in data:
        print('Errors:', data['errors'])
        break
    
    # Extract results
    results = data.get('data', {}).get('search', [])
    if not results:
        break
    
    conn = results[0].get('CONNECTION_NAME', {})
    edges = conn.get('edges', [])
    all_items.extend(edges)
    
    info = conn.get('pageInfo', {})
    print(f'Page {page}: {len(edges)} items (total: {len(all_items)})')
    
    # Check if there are more pages
    if not info.get('hasNextPage'):
        break
    
    cursor = info['endCursor']
    time.sleep(0.05)  # Be nice to the API

# Report if there are more results available
if info.get('hasNextPage'):
    print(f'NOTE: More results available beyond {MAX_PAGES} pages. Fetched {len(all_items)} so far.')

# Display first few results
print(json.dumps(all_items[:5], indent=2))
