#!/bin/bash

set -e

# Load environment variables
source ../../.env

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Cleaning up connector resources...${NC}"
echo ""

# Step 1: Delete all pending sync jobs
echo -e "${YELLOW}Step 1: Deleting pending sync jobs${NC}"
DELETE_JOBS_RESPONSE=$(curl -s -X POST "${ELASTICSEARCH_URL}/.elastic-connectors-sync-jobs/_delete_by_query" \
  -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match_all": {}
    }
  }')

DELETED_JOBS=$(echo "$DELETE_JOBS_RESPONSE" | jq -r '.deleted // 0')
echo -e "${GREEN}Deleted ${DELETED_JOBS} pending sync jobs${NC}"
echo ""

# Step 2: Clean up connector indices
echo -e "${YELLOW}Step 2: Cleaning up connector indices${NC}"

# Get the base pattern without the wildcard
BASE_PATTERN="${CONNECTOR_INDEX_PATTERN%\*}"

# Get all indices matching the pattern
INDICES=$(curl -s -X GET "${ELASTICSEARCH_URL}/_cat/indices/${CONNECTOR_INDEX_PATTERN}?h=index" \
    -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
    -H "Content-Type: application/json")

if [ -z "$INDICES" ]; then
    echo -e "${GREEN}No indices found matching pattern ${CONNECTOR_INDEX_PATTERN}${NC}"
    exit 0
fi

# Get indices associated with the alias
ALIASED_INDICES=$(curl -s -X GET "${ELASTICSEARCH_URL}/_alias/${CONNECTOR_INDEX_ALIAS}" \
    -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
    -H "Content-Type: application/json" | \
    jq -r 'keys[]' 2>/dev/null || echo "")

echo -e "${YELLOW}Found indices matching pattern:${NC}"
echo "$INDICES"
echo ""
echo -e "${YELLOW}Indices associated with alias ${CONNECTOR_INDEX_ALIAS}:${NC}"
if [ -n "$ALIASED_INDICES" ]; then
    echo "$ALIASED_INDICES"
else
    echo "None"
fi
echo ""

# Loop through each index
while IFS= read -r INDEX; do
    [ -z "$INDEX" ] && continue

    # Check if index is associated with the alias
    IS_ALIASED=false
    if echo "$ALIASED_INDICES" | grep -q "^${INDEX}$"; then
        IS_ALIASED=true
    fi

    if [ "$IS_ALIASED" = true ]; then
        echo -e "${GREEN}Skipping ${INDEX} (associated with alias)${NC}"
        continue
    fi

    # Get document count for the index
    DOC_COUNT=$(curl -s -X GET "${ELASTICSEARCH_URL}/${INDEX}/_count" \
        -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
        -H "Content-Type: application/json" | \
        jq -r '.count' 2>/dev/null || echo "0")

    if [ "$DOC_COUNT" = "0" ]; then
        echo -e "${YELLOW}Deleting empty index: ${INDEX}${NC}"
        RESPONSE=$(curl -s -X DELETE "${ELASTICSEARCH_URL}/${INDEX}" \
            -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
            -H "Content-Type: application/json")

        if echo "$RESPONSE" | jq -e '.acknowledged == true' >/dev/null 2>&1; then
            echo -e "${GREEN}Successfully deleted ${INDEX}${NC}"
        else
            echo -e "${RED}Failed to delete ${INDEX}${NC}"
            echo "$RESPONSE"
        fi
    else
        echo -e "${YELLOW}Skipping ${INDEX} (contains ${DOC_COUNT} documents)${NC}"
    fi
done <<< "$INDICES"

echo -e "${GREEN}Cleanup complete!${NC}"
