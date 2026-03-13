#!/usr/bin/env python3
"""
Validate Enigma GraphQL queries before execution.

This script checks for common errors in GraphQL queries:
- Incorrect field names (suggests corrections from field_corrections.json)
- Missing required filters on cardTransactions
- Requesting totalCount on connections (not supported)
- Using prompt with non-BRAND entity types
- Cursor pagination bugs (first page with $cursor variable)

Usage:
    python3 validate_query.py query.graphql
    python3 validate_query.py - < query.graphql  # from stdin
    
Or import and use programmatically:
    from validate_query import validate_query
    errors, warnings = validate_query(query_string, variables_dict)
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Load field corrections from reference file
SCRIPT_DIR = Path(__file__).parent
FIELD_CORRECTIONS_PATH = SCRIPT_DIR.parent / "references" / "field_corrections.json"

try:
    with open(FIELD_CORRECTIONS_PATH) as f:
        FIELD_CORRECTIONS = json.load(f)["field_corrections"]
        COMMON_MISTAKES = json.load(f)["common_mistakes"]
except FileNotFoundError:
    print(f"Warning: Could not load {FIELD_CORRECTIONS_PATH}", file=sys.stderr)
    FIELD_CORRECTIONS = {}
    COMMON_MISTAKES = []


def validate_query(query: str, variables: Dict[str, Any] = None) -> Tuple[List[str], List[str]]:
    """
    Validate a GraphQL query and variables.
    
    Returns:
        (errors, warnings) - Two lists of strings
    """
    errors = []
    warnings = []
    variables = variables or {}
    
    # Check for incorrect field names
    for type_name, correction_info in FIELD_CORRECTIONS.items():
        for incorrect_field in correction_info.get("incorrect", []):
            if incorrect_field and re.search(rf'\b{re.escape(incorrect_field)}\b', query):
                errors.append(
                    f"Incorrect field '{incorrect_field}' on {type_name}. "
                    f"Use '{correction_info['correct']}' instead. "
                    f"Note: {correction_info['note']}"
                )
    
    # Check for totalCount (not supported)
    if 'totalCount' in query:
        errors.append(
            "Connections do NOT support 'totalCount'. "
            "Paginate and count manually, or use 'hasNextPage' to detect more results."
        )
    
    # Check for unfiltered cardTransactions
    if 'cardTransactions' in query and 'conditions:' not in query:
        warnings.append(
            "Querying 'cardTransactions' without conditions returns hundreds of records. "
            "ALWAYS use conditions with filter to narrow results. "
            "See examples/revenue/ for standard filters."
        )
    
    # Check for prompt with non-BRAND entity type
    search_input = variables.get('searchInput', {})
    if search_input.get('prompt') and search_input.get('entityType') != 'BRAND':
        errors.append(
            f"'prompt' only works with entityType: BRAND. "
            f"You specified entityType: {search_input.get('entityType')}. "
            f"For entity resolution by name, use 'name' field instead."
        )
    
    # Check for cursor pagination bug (first page with $cursor)
    if '$cursor' in query and 'after:' not in query:
        warnings.append(
            "First page query should NOT declare $cursor variable. "
            "Only subsequent pages should include $cursor. "
            "See references/pagination_template.py for correct pattern."
        )
    
    # Check for name instead of prompt for discovery
    if search_input.get('name') and not search_input.get('entityType'):
        # Check if name looks like an industry term rather than a specific business
        industry_terms = ['coffee', 'restaurant', 'shop', 'store', 'service', 'repair', 'salon', 'bar', 'gym']
        if any(term in search_input.get('name', '').lower() for term in industry_terms):
            warnings.append(
                f"Using 'name' with generic term '{search_input.get('name')}'. "
                f"For industry/category-based discovery, use 'prompt' instead (entityType: BRAND). "
                f"Use 'name' only for known business names like 'Starbucks' or 'Nike'."
            )
    
    # Check for lowercase values that should be uppercase
    if variables:
        var_str = json.dumps(variables)
        if re.search(r'"state":\s*"[a-z]{2}"', var_str):
            errors.append(
                "State codes must be UPPERCASE (e.g., 'NY' not 'ny'). "
                "Most Enigma field values are uppercase."
            )
        if re.search(r'"operatingStatus":\s*"(open|closed)"', var_str, re.IGNORECASE):
            if not re.search(r'"operatingStatus":\s*"(Open|Closed)"', var_str):
                errors.append(
                    "Operating status must be capitalized ('Open' or 'Closed'). "
                    "Most Enigma field values are properly cased."
                )
    
    # Check for common mistake patterns from field_corrections.json
    for mistake_info in COMMON_MISTAKES:
        mistake = mistake_info.get("mistake", "")
        if any(term in query for term in extract_key_terms(mistake)):
            warnings.append(
                f"Possible issue: {mistake_info['mistake']}. "
                f"Correction: {mistake_info['correction']}"
            )
    
    return errors, warnings


def extract_key_terms(text: str) -> List[str]:
    """Extract key field names from mistake description."""
    # Simple heuristic: extract capitalized words and field-like patterns
    return re.findall(r'\b[A-Z][a-z]+(?:\.[a-z]+)+\b|\b[a-z]+Count\b', text)


def main():
    """CLI entrypoint."""
    if len(sys.argv) < 2 or sys.argv[1] == '-':
        query = sys.stdin.read()
    else:
        query_file = Path(sys.argv[1])
        if not query_file.exists():
            print(f"Error: File {query_file} not found", file=sys.stderr)
            sys.exit(1)
        query = query_file.read_text()
    
    # Try to extract variables if provided as JSON after the query
    variables = {}
    if '\n---\n' in query:
        query, variables_str = query.split('\n---\n', 1)
        try:
            variables = json.loads(variables_str)
        except json.JSONDecodeError:
            print("Warning: Could not parse variables JSON", file=sys.stderr)
    
    errors, warnings = validate_query(query, variables)
    
    if errors:
        print("❌ ERRORS:")
        for error in errors:
            print(f"  - {error}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not errors and not warnings:
        print("✅ Query looks good!")
    
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
