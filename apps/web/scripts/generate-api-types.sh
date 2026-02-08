#!/bin/bash
# Generate TypeScript types from FastAPI OpenAPI schema
# Usage: npm run types:generate
#
# Prerequisites: Backend must be running at $API_URL (default: http://localhost:8000)

API_URL="${API_URL:-http://localhost:8000}"
OUTPUT_FILE="src/types/api-generated.d.ts"

echo "Fetching OpenAPI schema from $API_URL/api/openapi.json..."
npx openapi-typescript "$API_URL/api/openapi.json" -o "$OUTPUT_FILE"
echo "Types generated at $OUTPUT_FILE"
