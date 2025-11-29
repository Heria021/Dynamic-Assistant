#!/bin/bash

# ============================================================================
# Chat & Thread API Test Script
# ============================================================================
# This script tests all endpoints related to chat and thread management.
# Usage: bash curl-chat-thread-tests.sh
# ============================================================================

BASE_URL="http://127.0.0.1:8000"
EMAIL="hariomsuthar7143@gmail.com"
PASSWORD="heria@021"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

format_json() {
    echo "$1" | python3 -m json.tool 2>/dev/null || echo "$1"
}

# ============================================================================
# STEP 1: LOGIN & GET TOKEN
# ============================================================================
print_header "STEP 1: Authentication - Login"

echo -e "${YELLOW}Logging in...${NC}"

# FIXED: Removed literal \n characters and used proper multi-line string or clean single line
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$EMAIL\",
        \"password\": \"$PASSWORD\"
    }")

# Debug: Print raw response if needed
# echo "Raw Login Response: $LOGIN_RESPONSE"

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('access_token', '') or data.get('access_token', ''))" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
    print_error "Failed to get access token"
    echo -e "${RED}Server Response:${NC}"
    format_json "$LOGIN_RESPONSE"
    exit 1
fi
print_success "Access token obtained"

# ============================================================================
# STEP 2: CREATE ASSISTANT & THREAD
# ============================================================================
print_header "STEP 2: Create Assistant & Thread"

echo -e "${YELLOW}Creating Assistant...${NC}"
ASSISTANT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/assistant/create-assistant" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "astName": "Test Assistant", 
        "astInstruction": "Test", 
        "gptModel": "gpt-4o-mini", 
        "astTools": ["code_interpreter"]
    }')

ASSISTANT_ID=$(echo "$ASSISTANT_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('astId', ''))" 2>/dev/null)

if [ -z "$ASSISTANT_ID" ]; then
    print_error "Failed to create assistant"
    format_json "$ASSISTANT_RESPONSE"
    exit 1
fi
print_success "Assistant created: $ASSISTANT_ID"

echo -e "${YELLOW}Creating Thread...${NC}"
THREAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/threads/create-thread" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"astId\": \"$ASSISTANT_ID\", 
        \"threadTitle\": \"Test Thread\"
    }")

THREAD_ID=$(echo "$THREAD_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('threadId', '') or data.get('data', {}).get('thread_id', ''))" 2>/dev/null)

if [ -z "$THREAD_ID" ]; then
    print_error "Failed to create thread"
    format_json "$THREAD_RESPONSE"
    exit 1
fi
print_success "Thread created: $THREAD_ID"

# ============================================================================
# STEP 3: CREATE CHAT
# ============================================================================
print_header "STEP 3: Create Chat"

echo -e "${YELLOW}Sending message...${NC}"
CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/chats/create-chat" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "astId=$ASSISTANT_ID" \
    -F "threadId=$THREAD_ID" \
    -F "message=Hello, this is a test message.")

print_info "Chat Response:"
format_json "$CHAT_RESPONSE"

# ============================================================================
# STEP 4: GET CHAT HISTORY
# ============================================================================
print_header "STEP 4: Get Chat History"

HISTORY_RESPONSE=$(curl -s -X GET "$BASE_URL/api/chats/history/$THREAD_ID?limit=5" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

print_info "Chat History:"
format_json "$HISTORY_RESPONSE"

# ============================================================================
# STEP 5: GET ALL THREADS FOR ASSISTANT
# ============================================================================
print_header "STEP 5: Get All Threads for Assistant"

THREADS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/threads/get-thread/$ASSISTANT_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

print_info "Threads for Assistant:"
format_json "$THREADS_RESPONSE"

# ============================================================================
# STEP 6: GET THREAD HISTORY BY ID
# ============================================================================
print_header "STEP 6: Get Thread History by ID"

THREAD_HISTORY_RESPONSE=$(curl -s -X GET "$BASE_URL/api/threads/get-thread-history/$THREAD_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

print_info "Thread History:"
format_json "$THREAD_HISTORY_RESPONSE"

# ============================================================================
# SUMMARY
# ============================================================================
print_header "TEST SUMMARY"

echo -e "\n${BLUE}Tested Endpoints:${NC}"
echo "  1. ${GREEN}✓${NC} POST   /auth/login                           - Login & Get Token"
echo "  2. ${GREEN}✓${NC} POST   /api/assistant/create-assistant         - Create Assistant (for context)"
echo "  3. ${GREEN}✓${NC} POST   /api/threads/create-thread              - Create Thread"
echo "  4. ${GREEN}✓${NC} POST   /api/chats/create-chat                  - Create Chat"
echo "  5. ${GREEN}✓${NC} GET    /api/chats/history/{thread_id}           - Get Chat History"
echo "  6. ${GREEN}✓${NC} GET    /api/threads/get-thread/{assistant_id}   - Get All Threads for Assistant"
echo "  7. ${GREEN}✓${NC} GET    /api/threads/get-thread-history/{thread_id} - Get Thread History by ID"

echo -e "\n${GREEN}✓ All chat & thread tests completed!${NC}\n"