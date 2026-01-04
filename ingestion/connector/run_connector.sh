#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables from parent .env file
if [ ! -f "../../.env" ]; then
    echo -e "${RED}Error: .env file not found in repository root${NC}"
    exit 1
fi

# Export variables from .env
set -a
source ../../.env
set +a

# Validate required environment variables
REQUIRED_VARS=("ELASTICSEARCH_URL" "ELASTICSEARCH_API_KEY" "CONNECTOR_INDEX_PATTERN" "CONNECTOR_INDEX_ALIAS" "CONNECTOR_ID")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}Error: Required environment variable $var is not set${NC}"
        exit 1
    fi
done

echo -e "${GREEN}=== Hall of Eternal Champions Connector Deployment ===${NC}"
echo ""

# Step 1: Create new index with timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
NEW_INDEX="${CONNECTOR_INDEX_PATTERN%-*}-${TIMESTAMP}"
echo -e "${YELLOW}Step 1: Creating new index ${NEW_INDEX}${NC}"

# Read mapping from file
MAPPING=$(cat hallofeternalchampions/elasticsearch_mapping.json)

# Create index with mapping
CREATE_RESPONSE=$(curl -X PUT "${ELASTICSEARCH_URL}/${NEW_INDEX}" \
  -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "${MAPPING}" \
  --fail --silent --show-error)

CREATE_EXIT_CODE=$?
echo "$CREATE_RESPONSE" | jq '.'

if [ $CREATE_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}Failed to create index${NC}"
    exit 1
fi
echo -e "${GREEN}Index created successfully${NC}"
echo ""

# Step 2: Stop any running containers and build Docker image
echo -e "${YELLOW}Step 2: Stopping any running containers${NC}"
docker-compose down 2>/dev/null || true

# Check if base image exists, build it if not
if ! docker image inspect judgement-connector-base:latest >/dev/null 2>&1; then
    echo -e "${YELLOW}Base image not found. Building base image (this is slow but only happens once)...${NC}"
    docker build -f Dockerfile.base -t judgement-connector-base:latest .
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to build base Docker image${NC}"
        exit 1
    fi
    echo -e "${GREEN}Base image built successfully${NC}"
else
    echo -e "${GREEN}Using existing base image${NC}"
fi

echo -e "${YELLOW}Building connector image (fast, using cached base)${NC}"
docker-compose build
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to build connector image${NC}"
    exit 1
fi
echo -e "${GREEN}Connector image built successfully${NC}"
echo ""

# Step 3: Delete all pending sync jobs
echo -e "${YELLOW}Step 3: Deleting pending sync jobs${NC}"
DELETE_RESPONSE=$(curl -s -X POST "${ELASTICSEARCH_URL}/.elastic-connectors-sync-jobs/_delete_by_query" \
  -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match_all": {}
    }
  }')

DELETED_COUNT=$(echo "$DELETE_RESPONSE" | jq -r '.deleted // 0')
echo -e "${GREEN}Deleted ${DELETED_COUNT} pending sync jobs${NC}"
echo ""

# Step 4: Update connector configuration to point to new index
echo -e "${YELLOW}Step 4: Updating connector to use new index${NC}"
UPDATE_RESPONSE=$(curl -X POST "${ELASTICSEARCH_URL}/.elastic-connectors/_update/${CONNECTOR_ID}" \
  -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"doc\": {
      \"index_name\": \"${NEW_INDEX}\",
      \"status\": \"configured\"
    }
  }" \
  --fail --silent --show-error)

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to update connector configuration${NC}"
    echo "$UPDATE_RESPONSE"
    exit 1
fi

echo "$UPDATE_RESPONSE" | jq '.'

# Verify the update
sleep 2
CONNECTOR_DOC=$(curl -s -X GET "${ELASTICSEARCH_URL}/.elastic-connectors/_doc/${CONNECTOR_ID}" \
  -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
  -H "Content-Type: application/json")

CURRENT_INDEX=$(echo "$CONNECTOR_DOC" | jq -r '._source.index_name')
CURRENT_STATUS=$(echo "$CONNECTOR_DOC" | jq -r '._source.status')

if [ "$CURRENT_INDEX" != "$NEW_INDEX" ]; then
    echo -e "${RED}Connector index_name verification failed!${NC}"
    echo -e "${RED}Expected: ${NEW_INDEX}${NC}"
    echo -e "${RED}Got: ${CURRENT_INDEX}${NC}"
    exit 1
fi

if [ "$CURRENT_STATUS" != "configured" ]; then
    echo -e "${RED}Connector status verification failed!${NC}"
    echo -e "${RED}Expected: configured${NC}"
    echo -e "${RED}Got: ${CURRENT_STATUS}${NC}"
    exit 1
fi

echo -e "${GREEN}Connector configuration updated and verified: ${NEW_INDEX} (status: ${CURRENT_STATUS})${NC}"
echo ""

# Step 5: Create sync job using Connector API
echo -e "${YELLOW}Step 5: Creating sync job${NC}"
curl -X POST "${ELASTICSEARCH_URL}/_connector/_sync_job" \
  -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"${CONNECTOR_ID}\",
    \"job_type\": \"full\",
    \"trigger_method\": \"on_demand\"
  }" \
  --fail --silent --show-error | jq '.'

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to create sync job${NC}"
    exit 1
fi
echo -e "${GREEN}Sync job created successfully${NC}"
echo ""

# Step 6: Run connectors service and monitor
echo -e "${YELLOW}Step 6: Running connectors service${NC}"
echo -e "${YELLOW}Watching logs... (Press Ctrl+C to stop once sync completes)${NC}"
echo ""

# Start the service in the background
docker-compose up -d

# Follow logs and watch for completion
docker-compose logs -f &
LOGS_PID=$!

# Function to check sync status
check_sync_status() {
    STATUS=$(curl -s -X GET "${ELASTICSEARCH_URL}/.elastic-connectors/_doc/${CONNECTOR_ID}" \
      -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" | jq -r '._source.last_sync_status // "unknown"')
    echo "$STATUS"
}

# Poll for sync completion
echo -e "${YELLOW}Monitoring sync status...${NC}"
SYNC_COMPLETE=false
MAX_WAIT=3600  # 1 hour timeout
ELAPSED=0
CHECK_INTERVAL=10

while [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep $CHECK_INTERVAL
    ELAPSED=$((ELAPSED + CHECK_INTERVAL))

    STATUS=$(check_sync_status)

    if [ "$STATUS" = "completed" ]; then
        echo -e "${GREEN}Sync completed successfully!${NC}"
        SYNC_COMPLETE=true
        break
    elif [ "$STATUS" = "error" ] || [ "$STATUS" = "failed" ]; then
        echo -e "${RED}Sync failed with status: ${STATUS}${NC}"
        kill $LOGS_PID 2>/dev/null || true
        docker-compose down
        exit 1
    fi

    echo -e "${YELLOW}Sync status: ${STATUS} (${ELAPSED}s elapsed)${NC}"
done

# Stop following logs
kill $LOGS_PID 2>/dev/null || true

# Stop the service
docker-compose down

if [ "$SYNC_COMPLETE" = false ]; then
    echo -e "${RED}Sync did not complete within timeout${NC}"
    exit 1
fi
echo ""

# Step 7: Update index alias
echo -e "${YELLOW}Step 7: Updating index alias${NC}"

# Get old indices from alias (if alias exists)
ALIAS_RESPONSE=$(curl -s -X GET "${ELASTICSEARCH_URL}/_alias/${CONNECTOR_INDEX_ALIAS}" \
  -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
  -H "Content-Type: application/json")

# Check if alias exists by looking for error in response
if echo "$ALIAS_RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
    echo -e "${YELLOW}Alias does not exist yet, will create it${NC}"
    OLD_INDICES=""
else
    OLD_INDICES=$(echo "$ALIAS_RESPONSE" | jq -r 'keys[]' 2>/dev/null || echo "")
    if [ ! -z "$OLD_INDICES" ]; then
        echo -e "${YELLOW}Found existing indices in alias: ${OLD_INDICES}${NC}"
    fi
fi

# Build alias actions JSON
ALIAS_ACTIONS='{"actions":['

# Add new index
ALIAS_ACTIONS="${ALIAS_ACTIONS}{\"add\":{\"index\":\"${NEW_INDEX}\",\"alias\":\"${CONNECTOR_INDEX_ALIAS}\"}}"

# Remove old indices from alias
if [ ! -z "$OLD_INDICES" ]; then
    for OLD_INDEX in $OLD_INDICES; do
        ALIAS_ACTIONS="${ALIAS_ACTIONS},{\"remove\":{\"index\":\"${OLD_INDEX}\",\"alias\":\"${CONNECTOR_INDEX_ALIAS}\"}}"
    done
fi

ALIAS_ACTIONS="${ALIAS_ACTIONS}]}"

# Update alias
UPDATE_RESPONSE=$(curl -s -X POST "${ELASTICSEARCH_URL}/_aliases" \
  -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "${ALIAS_ACTIONS}")

# Check if update was successful
if echo "$UPDATE_RESPONSE" | jq -e '.acknowledged == true' >/dev/null 2>&1; then
    echo -e "${GREEN}Alias updated successfully${NC}"
else
    echo -e "${RED}Failed to update alias${NC}"
    echo "$UPDATE_RESPONSE" | jq '.'
    exit 1
fi
echo ""

# Get document count in new index
DOC_COUNT=$(curl -s -X GET "${ELASTICSEARCH_URL}/${NEW_INDEX}/_count" \
  -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" | jq -r '.count // 0')

# Step 8: Cleanup old indices
echo -e "${YELLOW}Step 8: Cleanup${NC}"
if [ ! -z "$OLD_INDICES" ]; then
    if [ "$DOC_COUNT" -gt 0 ]; then
        echo -e "${YELLOW}Deleting old indices: ${OLD_INDICES}${NC}"
        for OLD_INDEX in $OLD_INDICES; do
            DELETE_RESPONSE=$(curl -s -X DELETE "${ELASTICSEARCH_URL}/${OLD_INDEX}" \
                -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
                -H "Content-Type: application/json")

            if echo "$DELETE_RESPONSE" | jq -e '.acknowledged == true' >/dev/null 2>&1; then
                echo -e "${GREEN}Deleted old index: ${OLD_INDEX}${NC}"
            else
                echo -e "${RED}Failed to delete old index: ${OLD_INDEX}${NC}"
                echo "$DELETE_RESPONSE" | jq '.'
            fi
        done
    else
        echo -e "${RED}New index has 0 documents - keeping old indices for safety${NC}"
        echo -e "${YELLOW}Old indices: ${OLD_INDICES}${NC}"
    fi
else
    echo -e "${GREEN}No old indices to clean up${NC}"
fi
echo ""

echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo -e "${GREEN}New index: ${NEW_INDEX}${NC}"
echo -e "${GREEN}Document count: ${DOC_COUNT}${NC}"
echo -e "${GREEN}Alias: ${CONNECTOR_INDEX_ALIAS}${NC}"
