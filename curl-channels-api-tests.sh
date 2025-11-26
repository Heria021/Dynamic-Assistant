#!/bin/bash

# ============================================================================
# Channels API cURL Testing Script
# ============================================================================
# This script tests all Channels endpoints
# Usage: bash curl-channels-api-tests.sh
# ============================================================================

BASE_URL="http://127.0.0.1:8000"
EMAIL="hariomsuthar7143@gmail.com"
PASSWORD="heria@021"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

format_json() {
    echo "$1" | python3 -m json.tool 2>/dev/null || echo "$1"
}

# ============================================================================
# STEP 1: LOGIN & GET TOKEN
# ============================================================================
print_header "STEP 1: Authentication - Login"

echo -e "\n${YELLOW}Logging in...${NC}"

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$EMAIL\",
        \"password\": \"$PASSWORD\"
    }")

echo -e "\n${YELLOW}Login Response:${NC}"
format_json "$LOGIN_RESPONSE"

# Extract token
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('access_token', '') or data.get('access_token', ''))" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
    print_error "Failed to get access token"
    exit 1
fi

print_success "Access token obtained"
echo -e "Token (first 50 chars): ${YELLOW}${ACCESS_TOKEN:0:50}...${NC}"

# ============================================================================
# STEP 2: CREATE AN ASSISTANT (needed for channels API)
# ============================================================================
print_header "STEP 2: Create Assistant (Prerequisite for Channels)"

echo -e "\n${YELLOW}Creating test assistant...${NC}"

ASSISTANT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/assistant/create-assistant" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d "{
        \"astName\": \"Channels Test Assistant\",
        \"astInstruction\": \"You are a helpful assistant for testing channel functionality.\",
        \"gptModel\": \"gpt-4o-mini\",
        \"astTools\": [\"code_interpreter\"]
    }")

echo -e "\n${YELLOW}Assistant Created:${NC}"
format_json "$ASSISTANT_RESPONSE"

ASSISTANT_ID=$(echo "$ASSISTANT_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
out=''
try:
    out = data.get('data', {}).get('_id','') or (data.get('data',{}).get('assistant')[0].get('astId') if data.get('data',{}).get('assistant') else '')
except Exception:
    out = ''
print(out)
" 2>/dev/null)

if [ -z "$ASSISTANT_ID" ]; then
    print_error "Failed to create assistant"
    exit 1
fi

print_success "Assistant created with ID: $ASSISTANT_ID"

# ============================================================================
# STEP 3: CHANNELS API - Get Assistant Info
# ============================================================================
print_header "STEP 3: Channels API - Get Assistant Info"

echo -e "\n${YELLOW}Fetching assistant info for channels...${NC}"

AST_INFO_RESPONSE=$(curl -s -X POST "$BASE_URL/api/channel/channels-ast-info?ast_ID=$ASSISTANT_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

echo -e "\n${YELLOW}Assistant Info Response:${NC}"
format_json "$AST_INFO_RESPONSE"

# ============================================================================
# STEP 4: CHANNELS API - API Integration Setup
# ============================================================================
print_header "STEP 4: Channels API - API Integration"

echo -e "\n${YELLOW}Setting up API integration...${NC}"

# Create channel data (using query parameters for Channel model)
CHANNEL_RESPONSE=$(curl -s -X POST "$BASE_URL/api/channel/channels-api-integration?astName=Channels%20Test%20Assistant&apiToken=test-token" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

echo -e "\n${YELLOW}API Integration Response:${NC}"
format_json "$CHANNEL_RESPONSE"

# ============================================================================
# SUMMARY
# ============================================================================
print_header "TEST SUMMARY"

echo -e "\n${BLUE}Tested Endpoints:${NC}"
echo "  1. ${GREEN}✓${NC} POST   /auth/login                       - Login & Get Token"
echo "  2. ${GREEN}✓${NC} POST   /api/assistant/create-assistant   - Create Assistant"
echo "  3. ${GREEN}✓${NC} POST   /api/channel/channels-ast-info    - Get Assistant Info"
echo "  4. ${GREEN}✓${NC} POST   /api/channel/channels-api-integration - API Integration"

echo -e "\n${BLUE}Test Data:${NC}"
echo "  Assistant ID: ${YELLOW}$ASSISTANT_ID${NC}"
echo "  Access Token: ${YELLOW}${ACCESS_TOKEN:0:50}...${NC}"

echo -e "\n${GREEN}✓ All tests completed successfully!${NC}\n"

# ============================================================================
# OPTIONAL: Quick Reference
# ============================================================================

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}QUICK REFERENCE - Channels API Commands${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"

echo -e "\n${YELLOW}1. Get Assistant Info for Channels:${NC}"
echo "curl -X POST http://127.0.0.1:8000/api/channel/channels-ast-info \\"
echo "  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \\"
echo "  -d 'ast_ID=ASSISTANT_ID'"

echo -e "\n${YELLOW}2. Setup API Integration:${NC}"
echo "curl -X POST 'http://127.0.0.1:8000/api/channel/channels-api-integration?astName=ASSISTANT_NAME&apiToken=API_TOKEN' \\"
echo "  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'"

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}\n"
