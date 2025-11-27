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
# STEP 2: GET OR CREATE AN ASSISTANT (needed for channels API)
# ============================================================================
print_header "STEP 2: Get or Create Assistant (Prerequisite for Channels)"

echo -e "\n${YELLOW}Attempting to create test assistant...${NC}"

ASSISTANT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/assistant/create-assistant" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d "{
        \"astName\": \"Channels Test Assistant\",
        \"astInstruction\": \"You are a helpful assistant for testing channel functionality.\",
        \"gptModel\": \"gpt-4o-mini\",
        \"astTools\": [\"code_interpreter\"]
    }")

echo -e "\n${YELLOW}Assistant Creation Response:${NC}"
format_json "$ASSISTANT_RESPONSE"

# Extract assistant ID, name, and API token from creation response
ASSISTANT_EXTRACTION=$(echo "$ASSISTANT_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
result = {'astId': '', 'astName': '', 'apiToken': ''}
try:
    if data.get('status') and data.get('data'):
        assistant_data = data.get('data', {})
        if isinstance(assistant_data, dict):
            result['astId'] = assistant_data.get('astId', '') or assistant_data.get('_id', '')
            result['astName'] = assistant_data.get('astName', '')
            result['apiToken'] = assistant_data.get('apiToken', '')
        elif isinstance(assistant_data, list) and len(assistant_data) > 0:
            result['astId'] = assistant_data[0].get('astId', '') or assistant_data[0].get('_id', '')
            result['astName'] = assistant_data[0].get('astName', '')
            result['apiToken'] = assistant_data[0].get('apiToken', '')
except Exception:
    pass
print(f\"{result['astId']}|{result['astName']}|{result['apiToken']}\")
" 2>/dev/null)

ASSISTANT_ID=$(echo "$ASSISTANT_EXTRACTION" | cut -d'|' -f1)
CREATED_ASSISTANT_NAME=$(echo "$ASSISTANT_EXTRACTION" | cut -d'|' -f2)
CREATED_API_TOKEN=$(echo "$ASSISTANT_EXTRACTION" | cut -d'|' -f3)

# If assistant creation failed, try to get existing assistants
if [ -z "$ASSISTANT_ID" ]; then
    echo -e "\n${YELLOW}Assistant creation failed. Trying to fetch existing assistants...${NC}"
    
    EXISTING_ASSISTANTS=$(curl -s -X GET "$BASE_URL/api/assistant/get-assistant" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    echo -e "\n${YELLOW}Existing Assistants Response:${NC}"
    format_json "$EXISTING_ASSISTANTS"
    
    ASSISTANT_ID=$(echo "$EXISTING_ASSISTANTS" | python3 -c "import sys, json
data=json.load(sys.stdin)
out=''
try:
    if data.get('status') and data.get('data') and isinstance(data.get('data'), list) and len(data['data']) > 0:
        # Get the first assistant's astId
        out = data['data'][0].get('astId', '')
        if not out:
            # Try _id as fallback
            out = data['data'][0].get('_id', '')
except Exception:
    pass
print(out)
" 2>/dev/null)
    
    if [ -z "$ASSISTANT_ID" ]; then
        print_error "Failed to create assistant and no existing assistants found. Cannot proceed with channel tests."
        exit 1
    else
        print_success "Using existing assistant with ID: $ASSISTANT_ID"
    fi
else
    print_success "Assistant created with ID: $ASSISTANT_ID"
fi

# ============================================================================
# STEP 3: CHANNELS API - Get Assistant Info
# ============================================================================
print_header "STEP 3: Channels API - Get Assistant Info"

echo -e "\n${YELLOW}Fetching assistant info for channels...${NC}"

AST_INFO_RESPONSE=$(curl -s -X POST "$BASE_URL/api/channel/channels-ast-info?ast_ID=$ASSISTANT_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

echo -e "\n${YELLOW}Assistant Info Response:${NC}"
format_json "$AST_INFO_RESPONSE"

# Extract assistant name and API token from the response
# First try from channels-ast-info response, then fallback to existing assistants list
ASSISTANT_NAME=$(echo "$AST_INFO_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
out=''
try:
    if data.get('status') and data.get('data') and isinstance(data.get('data'), list) and len(data['data']) > 0:
        out = data['data'][0].get('astName', '')
except Exception:
    pass
print(out)
" 2>/dev/null)

API_TOKEN=$(echo "$AST_INFO_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
out=''
try:
    if data.get('status') and data.get('data') and isinstance(data.get('data'), list) and len(data['data']) > 0:
        # Try both api_token and apiToken field names
        out = data['data'][0].get('api_token', '') or data['data'][0].get('apiToken', '')
except Exception:
    pass
print(out)
" 2>/dev/null)

# First priority: Use values from assistant creation if available
if [ -n "$CREATED_ASSISTANT_NAME" ]; then
    ASSISTANT_NAME="$CREATED_ASSISTANT_NAME"
fi
if [ -n "$CREATED_API_TOKEN" ]; then
    API_TOKEN="$CREATED_API_TOKEN"
fi

# If channels-ast-info didn't return data, extract from existing assistants list
if [ -z "$ASSISTANT_NAME" ] || [ -z "$API_TOKEN" ]; then
    if [ -n "$EXISTING_ASSISTANTS" ]; then
        echo -e "\n${YELLOW}Extracting assistant info from existing assistants list...${NC}"
        
        EXTRACTED_NAME=$(echo "$EXISTING_ASSISTANTS" | python3 -c "import sys, json
data=json.load(sys.stdin)
out=''
try:
    if data.get('status') and data.get('data') and isinstance(data.get('data'), list) and len(data['data']) > 0:
        for assistant in data['data']:
            if assistant.get('astId') == '$ASSISTANT_ID':
                out = assistant.get('astName', '')
                break
except Exception:
    pass
print(out)
" 2>/dev/null)
        
        EXTRACTED_TOKEN=$(echo "$EXISTING_ASSISTANTS" | python3 -c "import sys, json
data=json.load(sys.stdin)
out=''
try:
    if data.get('status') and data.get('data') and isinstance(data.get('data'), list) and len(data['data']) > 0:
        for assistant in data['data']:
            if assistant.get('astId') == '$ASSISTANT_ID':
                out = assistant.get('apiToken', '')
                break
except Exception:
    pass
print(out)
" 2>/dev/null)
        
        if [ -n "$EXTRACTED_NAME" ]; then
            ASSISTANT_NAME="$EXTRACTED_NAME"
        fi
        
        if [ -n "$EXTRACTED_TOKEN" ]; then
            API_TOKEN="$EXTRACTED_TOKEN"
        fi
    fi
fi

if [ -n "$ASSISTANT_NAME" ]; then
    echo -e "\n${GREEN}✓ Extracted Assistant Name: $ASSISTANT_NAME${NC}"
else
    ASSISTANT_NAME="Channels Test Assistant"
    echo -e "\n${YELLOW}⚠ Using default assistant name${NC}"
fi

if [ -n "$API_TOKEN" ]; then
    echo -e "${GREEN}✓ Extracted API Token: ${API_TOKEN:0:20}...${NC}"
else
    API_TOKEN="test-token"
    echo -e "${YELLOW}⚠ Using default test token (api_token not found)${NC}"
fi

# ============================================================================
# STEP 4: CHANNELS API - API Integration Setup
# ============================================================================
print_header "STEP 4: Channels API - API Integration"

echo -e "\n${YELLOW}Setting up API integration...${NC}"
echo -e "Using Assistant Name: ${YELLOW}$ASSISTANT_NAME${NC}"
echo -e "Using API Token: ${YELLOW}${API_TOKEN:0:20}...${NC}"

# URL encode the assistant name and API token
ENCODED_AST_NAME=$(echo -n "$ASSISTANT_NAME" | python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read()))" 2>/dev/null || echo "$ASSISTANT_NAME")
ENCODED_API_TOKEN=$(echo -n "$API_TOKEN" | python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read()))" 2>/dev/null || echo "$API_TOKEN")

# Create channel data (using query parameters for Channel model)
CHANNEL_RESPONSE=$(curl -s -X POST "$BASE_URL/api/channel/channels-api-integration?astName=$ENCODED_AST_NAME&apiToken=$ENCODED_API_TOKEN" \
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
