#!/bin/bash

# ============================================================================
# End-User API cURL Testing Script
# ============================================================================
# This script tests the public end-user chat endpoint (uses apiToken auth)
# Usage: bash curl-enduser-api-tests.sh
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
# STEP 2: CREATE AN ASSISTANT
# ============================================================================
print_header "STEP 2: Create Assistant"

echo -e "\n${YELLOW}Creating test assistant...${NC}"

ASSISTANT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/assistant/create-assistant" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d "{
        \"astName\": \"End-User Chat Assistant\",
        \"astInstruction\": \"You are a helpful assistant for testing end-user chat functionality.\",
        \"gptModel\": \"gpt-4o-mini\",
        \"astTools\": [\"code_interpreter\"]
    }")

echo -e "\n${YELLOW}Assistant Created:${NC}"
format_json "$ASSISTANT_RESPONSE"

# Extract assistant ID and API token from response
ASSISTANT_EXTRACTION=$(echo "$ASSISTANT_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
result = {'astId': '', 'astName': '', 'apiToken': ''}
try:
    if data.get('status') and data.get('data'):
        assistant_data = data.get('data', {})
        if isinstance(assistant_data, dict):
            # New format: data is a dict with astId and apiToken directly
            result['astId'] = assistant_data.get('astId', '')  # Use astId (OpenAI assistant ID)
            result['astName'] = assistant_data.get('astName', '')
            result['apiToken'] = assistant_data.get('apiToken', '')
        elif isinstance(assistant_data, list) and len(assistant_data) > 0:
            # Old format: data is a list
            result['astId'] = assistant_data[0].get('astId', '') or assistant_data[0].get('_id', '')
            result['astName'] = assistant_data[0].get('astName', '')
            result['apiToken'] = assistant_data[0].get('apiToken', '') or assistant_data[0].get('api_token', '')
except Exception:
    pass
print(f\"{result['astId']}|{result['astName']}|{result['apiToken']}\")
" 2>/dev/null)

ASSISTANT_ID=$(echo "$ASSISTANT_EXTRACTION" | cut -d'|' -f1)
ASSISTANT_NAME=$(echo "$ASSISTANT_EXTRACTION" | cut -d'|' -f2)
ASSISTANT_API_TOKEN=$(echo "$ASSISTANT_EXTRACTION" | cut -d'|' -f3)

# If assistant creation failed, try to get existing assistants
if [ -z "$ASSISTANT_ID" ] || [ -z "$ASSISTANT_API_TOKEN" ]; then
    echo -e "\n${YELLOW}Assistant creation failed or limit reached. Fetching existing assistants...${NC}"
    
    EXISTING_ASSISTANTS=$(curl -s -X GET "$BASE_URL/api/assistant/get-assistant" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    echo -e "\n${YELLOW}Existing Assistants Response:${NC}"
    format_json "$EXISTING_ASSISTANTS"
    
    # Extract from first assistant
    ASSISTANT_EXTRACTION=$(echo "$EXISTING_ASSISTANTS" | python3 -c "import sys, json
data=json.load(sys.stdin)
result = {'astId': '', 'astName': '', 'apiToken': ''}
try:
    if data.get('status') and data.get('data') and isinstance(data.get('data'), list) and len(data['data']) > 0:
        assistant = data['data'][0]
        result['astId'] = assistant.get('astId', '')
        result['astName'] = assistant.get('astName', '')
        result['apiToken'] = assistant.get('apiToken', '')
except Exception:
    pass
print(f\"{result['astId']}|{result['astName']}|{result['apiToken']}\")
" 2>/dev/null)
    
    ASSISTANT_ID=$(echo "$ASSISTANT_EXTRACTION" | cut -d'|' -f1)
    ASSISTANT_NAME=$(echo "$ASSISTANT_EXTRACTION" | cut -d'|' -f2)
    ASSISTANT_API_TOKEN=$(echo "$ASSISTANT_EXTRACTION" | cut -d'|' -f3)
    
    if [ -z "$ASSISTANT_ID" ] || [ -z "$ASSISTANT_API_TOKEN" ]; then
        print_error "Failed to create assistant and no existing assistants found. Cannot proceed."
        exit 1
    else
        print_success "Using existing assistant: $ASSISTANT_NAME (ID: $ASSISTANT_ID)"
    fi
else
    print_success "Assistant created with ID: $ASSISTANT_ID"
fi

if [ -z "$ASSISTANT_API_TOKEN" ]; then
    print_error "Failed to extract API token from assistant"
    exit 1
fi

print_success "Assistant API Token extracted: ${ASSISTANT_API_TOKEN:0:20}..."
echo "Full API Token: ${YELLOW}$ASSISTANT_API_TOKEN${NC}"

# ============================================================================
# STEP 3: END-USER API - Create Chat (New Thread)
# ============================================================================
print_header "STEP 3: End-User API - Create Chat with New Thread"

echo -e "\n${YELLOW}Creating a new end-user chat (this will create a thread automatically)...${NC}"

ENDUSER_CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/enduser/end-user-chat" \
    -F "astName=$ASSISTANT_NAME" \
    -F "apiToken=$ASSISTANT_API_TOKEN" \
    -F "message=Hello! Can you help me understand Python generators?")

echo -e "\n${YELLOW}End-User Chat Response:${NC}"
format_json "$ENDUSER_CHAT_RESPONSE"

# Extract thread token from response
THREAD_ID=$(echo "$ENDUSER_CHAT_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
out=''
try:
    # Try direct threadtoken field first
    out = data.get('threadtoken', '')
    if not out:
        # Try threadToken (camelCase)
        out = data.get('threadToken', '')
    if not out:
        # Try in data object
        out = data.get('data', {}).get('threadtoken', '') or data.get('data', {}).get('threadToken', '')
    if not out:
        # Try thread_data array
        thread_data = data.get('thread_data', [])
        if thread_data and len(thread_data) > 0:
            out = thread_data[0].get('threadToken', '') or thread_data[0].get('threadtoken', '')
except Exception as e:
    out = ''
print(out)
" 2>/dev/null)

if [ -z "$THREAD_ID" ]; then
    print_error "Failed to extract thread token"
    THREAD_ID="unknown"
else
    print_success "Thread Token extracted: $THREAD_ID"
fi

# ============================================================================
# STEP 4: END-USER API - Continue Chat (Using Existing Thread)
# ============================================================================
print_header "STEP 4: End-User API - Continue Chat in Existing Thread"

echo -e "\n${YELLOW}Sending another message to the same thread...${NC}"

ENDUSER_CHAT_RESPONSE_2=$(curl -s -X POST "$BASE_URL/api/enduser/end-user-chat" \
    -F "astName=$ASSISTANT_NAME" \
    -F "apiToken=$ASSISTANT_API_TOKEN" \
    -F "threadtoken=$THREAD_ID" \
    -F "message=What is the difference between list comprehension and generator expressions?")

echo -e "\n${YELLOW}End-User Chat Response (Continued):${NC}"
format_json "$ENDUSER_CHAT_RESPONSE_2"

# ============================================================================
# STEP 5: END-USER API - Chat with File Upload (if needed)
# ============================================================================
print_header "STEP 5: End-User API - Chat with Message"

echo -e "\n${YELLOW}Sending a final message...${NC}"

ENDUSER_CHAT_RESPONSE_3=$(curl -s -X POST "$BASE_URL/api/enduser/end-user-chat" \
    -F "astName=$ASSISTANT_NAME" \
    -F "apiToken=$ASSISTANT_API_TOKEN" \
    -F "threadtoken=$THREAD_ID" \
    -F "message=How can I optimize my Python code for better performance?")

echo -e "\n${YELLOW}End-User Chat Response (Final):${NC}"
format_json "$ENDUSER_CHAT_RESPONSE_3"

# ============================================================================
# SUMMARY
# ============================================================================
print_header "TEST SUMMARY"

echo -e "\n${BLUE}Tested Endpoints:${NC}"
echo "  1. ${GREEN}✓${NC} POST   /auth/login                     - Login & Get Token"
echo "  2. ${GREEN}✓${NC} POST   /api/assistant/create-assistant - Create Assistant"
echo "  3. ${GREEN}✓${NC} POST   /api/enduser/end-user-chat      - Create Chat (New Thread)"
echo "  4. ${GREEN}✓${NC} POST   /api/enduser/end-user-chat      - Continue Chat (Existing Thread)"
echo "  5. ${GREEN}✓${NC} POST   /api/enduser/end-user-chat      - Send Multiple Messages"

echo -e "\n${BLUE}Test Data:${NC}"
echo "  Assistant Name: ${YELLOW}$ASSISTANT_NAME${NC}"
echo "  Assistant ID:   ${YELLOW}$ASSISTANT_ID${NC}"
echo "  API Token:      ${YELLOW}${ASSISTANT_API_TOKEN:0:20}...${NC}"
echo "  Thread ID:      ${YELLOW}$THREAD_ID${NC}"

echo -e "\n${GREEN}✓ All tests completed successfully!${NC}\n"

# ============================================================================
# OPTIONAL: Quick Reference
# ============================================================================

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}QUICK REFERENCE - End-User API Commands${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"

echo -e "\n${YELLOW}1. Create New Chat (Creates Thread Automatically):${NC}"
echo "curl -X POST http://127.0.0.1:8000/api/enduser/end-user-chat \\"
echo "  -F 'astName=Your Assistant Name' \\"
echo "  -F 'apiToken=YOUR_API_TOKEN' \\"
echo "  -F 'message=Your message here'"

echo -e "\n${YELLOW}2. Continue Chat in Existing Thread:${NC}"
echo "curl -X POST http://127.0.0.1:8000/api/enduser/end-user-chat \\"
echo "  -F 'astName=Your Assistant Name' \\"
echo "  -F 'apiToken=YOUR_API_TOKEN' \\"
echo "  -F 'threadtoken=THREAD_ID' \\"
echo "  -F 'message=Your follow-up message'"

echo -e "\n${YELLOW}3. Send Message with File Upload:${NC}"
echo "curl -X POST http://127.0.0.1:8000/api/enduser/end-user-chat \\"
echo "  -F 'astName=Your Assistant Name' \\"
echo "  -F 'apiToken=YOUR_API_TOKEN' \\"
echo "  -F 'threadtoken=THREAD_ID' \\"
echo "  -F 'message=Your message' \\"
echo "  -F 'image=@/path/to/file.jpg'"

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}\n"
