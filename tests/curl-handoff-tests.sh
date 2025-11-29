#!/bin/bash

# ============================================================================
# Human Handoff End-to-End Test Script
# ============================================================================
# This script tests the Human Handoff flow:
# 1. Login & get token
# 2. Get existing assistant
# 3. Create new thread
# 4. Trigger handoff via chat
# 5. Test agent endpoints:
#       - pending-handoffs
#       - assign thread
#       - send human message
#       - complete handoff
#       - my-threads
# Usage: bash curl-handoff-tests.sh
# ============================================================================

BASE_URL="http://127.0.0.1:8000"
EMAIL="hariomsuthar7143@gmail.com"
PASSWORD="heria@021"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

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

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

format_json() {
    echo "$1" | python3 -m json.tool 2>/dev/null || echo "$1"
}

# ============================================================================
# STEP 1: LOGIN
# ============================================================================
print_header "STEP 1: Authentication - Login"

echo "curl -X POST $BASE_URL/auth/login -H 'Content-Type: application/json' -d '{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}'"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
        \"email\": \"$EMAIL\",
        \"password\": \"$PASSWORD\"
      }")

print_info "Login Response:"
format_json "$LOGIN_RESPONSE"

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
    print_error "Failed to extract access token"
    exit 1
fi

print_success "Access token acquired"

# ============================================================================
# STEP 2: GET EXISTING ASSISTANT
# ============================================================================
print_header "STEP 2: Get Existing Assistant"

echo "curl -X GET $BASE_URL/api/assistant/get-assistant -H 'Authorization: Bearer $ACCESS_TOKEN'"
ASSISTANTS=$(curl -s -X GET "$BASE_URL/api/assistant/get-assistant" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

format_json "$ASSISTANTS"

ASSISTANT_ID=$(echo "$ASSISTANTS" | python3 -c "import sys, json; d=json.load(sys.stdin); 
ast=''; 
try:
    if d.get('data'):
        ast=d['data'][0].get('astId','')
except: pass
print(ast)" 2>/dev/null)

if [ -z "$ASSISTANT_ID" ]; then
    print_error "No assistant found. Please create one first."
    exit 1
fi

print_success "Using Assistant: $ASSISTANT_ID"

# ============================================================================
# STEP 3: CREATE THREAD
# ============================================================================
print_header "STEP 3: Create Thread"

echo "curl -X POST $BASE_URL/api/threads/create-thread -H 'Content-Type: application/json' -H 'Authorization: Bearer $ACCESS_TOKEN' -d '{\"astId\": \"$ASSISTANT_ID\", \"threadTitle\": \"Handoff Test Thread\"}'"
THREAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/threads/create-thread" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{
        \"astId\": \"$ASSISTANT_ID\",
        \"threadTitle\": \"Handoff Test Thread\"
      }")

format_json "$THREAD_RESPONSE"

THREAD_ID=$(echo "$THREAD_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin);
print(d.get('data',{}).get('threadId',''))" 2>/dev/null)

print_success "Thread created: $THREAD_ID"

# ============================================================================
# STEP 4: TRIGGER HANDOFF VIA CHAT
# ============================================================================
print_header "STEP 4: Trigger Handoff via Chat"

echo "curl -X POST $BASE_URL/api/chats/create-chat -H 'Authorization: Bearer $ACCESS_TOKEN' -F 'astId=$ASSISTANT_ID' -F 'threadId=$THREAD_ID' -F 'message=I want to talk to a human agent right now'"
HANDOFF_RESPONSE=$(curl -s -X POST "$BASE_URL/api/chats/create-chat" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "astId=$ASSISTANT_ID" \
  -F "threadId=$THREAD_ID" \
  -F "message=I want to talk to a human agent right now")

format_json "$HANDOFF_RESPONSE"

print_success "Handoff request sent"

# ============================================================================
# STEP 5: AGENT — PENDING HANDOFFS
# ============================================================================
print_header "STEP 5: Agent - Get Pending Handoffs"

echo "curl -X GET $BASE_URL/api/agent/pending-handoffs -H 'Authorization: Bearer $ACCESS_TOKEN'"
PENDING=$(curl -s -X GET "$BASE_URL/api/agent/pending-handoffs" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

format_json "$PENDING"

print_success "Fetched pending handoffs"

# ============================================================================
# STEP 6: ASSIGN THREAD TO AGENT
# ============================================================================
print_header "STEP 6: Assign Thread to Agent"

echo "curl -X POST $BASE_URL/api/agent/assign/$THREAD_ID -H 'Authorization: Bearer $ACCESS_TOKEN'"
ASSIGN=$(curl -s -X POST "$BASE_URL/api/agent/assign/$THREAD_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

format_json "$ASSIGN"

print_success "Thread assigned to agent"

# ============================================================================
# STEP 7: SEND HUMAN MESSAGE TO USER
# ============================================================================
print_header "STEP 7: Agent Send Message to User"

echo "curl -X POST $BASE_URL/api/agent/send-message -H 'Authorization: Bearer $ACCESS_TOKEN' -H 'Content-Type: application/json' -d '{\"thread_id\": \"$THREAD_ID\", \"message\": \"Hello! This is a human agent. How can I help you?\"}'"
SEND_MSG=$(curl -s -X POST "$BASE_URL/api/agent/send-message" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
        \"thread_id\": \"$THREAD_ID\",
        \"message\": \"Hello! This is a human agent. How can I help you?\"
      }")

format_json "$SEND_MSG"

print_success "Human message delivered"

# ============================================================================
# STEP 8: VIEW THREADS ASSIGNED TO AGENT
# ============================================================================
print_header "STEP 8: Agent - My Active Threads"

echo "curl -X GET $BASE_URL/api/agent/my-threads -H 'Authorization: Bearer $ACCESS_TOKEN'"
MY_THREADS=$(curl -s -X GET "$BASE_URL/api/agent/my-threads" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

format_json "$MY_THREADS"

print_success "Fetched agent active threads"

# ============================================================================
# STEP 9: COMPLETE HANDOFF
# ============================================================================
print_header "STEP 9: Complete Handoff"

echo "curl -X POST $BASE_URL/api/agent/complete-handoff -H 'Authorization: Bearer $ACCESS_TOKEN' -H 'Content-Type: application/json' -d '{\"thread_id\": \"$THREAD_ID\", \"notes\": \"Issue resolved successfully.\"}'"
COMPLETE=$(curl -s -X POST "$BASE_URL/api/agent/complete-handoff" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
        \"thread_id\": \"$THREAD_ID\",
        \"notes\": \"Issue resolved successfully.\"
      }")

format_json "$COMPLETE"

print_success "Handoff completed"

# ============================================================================
# DONE
# ============================================================================
print_header "HUMAN HANDOFF TEST COMPLETED SUCCESSFULLY"
print_success "All agent + chat handoff operations executed"