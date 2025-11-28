#!/bin/bash

# ============================================================================
# UNIFIED API TEST SUITE
# ============================================================================
# This script tests the entire lifecycle of the AI Assistant API:
# 1. Auth & Login
# 2. Assistant Creation (Active RAG)
# 3. Thread Management
# 4. Chat Features (RAG, Function Calling)
# 5. History Retrieval
# 6. Human Handoff (Agent Workflow)
# ============================================================================

BASE_URL="http://127.0.0.1:8000"
EMAIL="hariomsuthar7143@gmail.com"
PASSWORD="heria@021"
MANUAL_FILE="nebula_x9_manual.md"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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

ensure_manual_file() {
    if [ ! -f "$MANUAL_FILE" ]; then
        print_info "Creating dummy manual file: $MANUAL_FILE"
        echo "# Nebula-X9 Smart Toaster Manual
        
## Power Modes
1. **Eco Mode**: 500W output.
2. **Standard Mode**: 800W output.
3. **Hyper-Crunch Mode**: 1200W output (Warning: Do not use for bagels).

## Troubleshooting
- **Error E-99**: Crumb tray is full. Please empty immediately.
- **Error E-01**: Wi-Fi disconnected.

## Contact
For warranty claims, email support@nebulatoast.com." > "$MANUAL_FILE"
    fi
}

# ============================================================================
# PHASE 1: AUTHENTICATION
# ============================================================================
print_header "PHASE 1: Authentication"

echo -e "${YELLOW}Logging in...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{ \"email\": \"$EMAIL\", \"password\": \"$PASSWORD\" }")

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('access_token', '') or data.get('access_token', ''))" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
    print_error "Login failed."
    format_json "$LOGIN_RESPONSE"
    exit 1
fi
print_success "Access Token Acquired"

# ============================================================================
# PHASE 2: ASSISTANT CREATION (RAG SETUP)
# ============================================================================
print_header "PHASE 2: Assistant Creation (With File)"

ensure_manual_file

echo -e "${YELLOW}Creating Assistant with RAG file...${NC}"
ASSISTANT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/assistant/create-assistant-with-file" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "astName=Nebula-X9 Support Bot" \
    -F $'astInstruction=You are a support bot for Nebula-X9 Toaster. Use the manual to answer questions.\n\nCRITICAL FUNCTION RULES:\n1. If user asks for human/agent -> Call handoff_to_human\n2. If user asks for documentation link -> Call send_link\n' \
    -F "gptModel=gpt-4o-mini" \
    -F 'astTools=["code_interpreter","file_search"]' \
    -F "files=@$MANUAL_FILE")

# Extract Assistant ID
ASSISTANT_ID=$(echo "$ASSISTANT_RESPONSE" | python3 -c "import sys, json; 
try:
    data=json.load(sys.stdin)
    print(data.get('data', {}).get('astId', ''))
except: pass" 2>/dev/null)

if [ -z "$ASSISTANT_ID" ]; then
    print_error "Assistant creation failed. Trying to fetch existing..."
    # Fallback to getting existing assistant
    ASSISTANT_RESPONSE=$(curl -s -X GET "$BASE_URL/api/assistant/get-assistant" -H "Authorization: Bearer $ACCESS_TOKEN")
    ASSISTANT_ID=$(echo "$ASSISTANT_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('data',[{}])[0].get('astId',''))" 2>/dev/null)
fi

if [ -z "$ASSISTANT_ID" ]; then
    print_error "Could not get an Assistant ID. Aborting."
    exit 1
fi

print_success "Assistant Active: $ASSISTANT_ID"
print_info "Sleeping 3s for vector ingestion..."
sleep 3

# ============================================================================
# PHASE 3: THREAD & CHAT (RAG & FUNCTIONS)
# ============================================================================
print_header "PHASE 3: Chat Interactions (RAG & Function Calling)"

# 1. Create Thread
echo -e "${YELLOW}Creating User Thread...${NC}"
THREAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/threads/create-thread" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d "{ \"astId\": \"$ASSISTANT_ID\", \"threadTitle\": \"General Support\" }")

THREAD_ID=$(echo "$THREAD_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('threadId', '') or data.get('data', {}).get('thread_id', ''))" 2>/dev/null)
print_success "Thread Created: $THREAD_ID"

# 2. Test RAG
echo -e "\n${YELLOW}Test 1: RAG Question (Error E-99)${NC}"
RAG_CHAT=$(curl -s -X POST "$BASE_URL/api/chats/create-chat" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "astId=$ASSISTANT_ID" \
    -F "threadId=$THREAD_ID" \
    -F "message=What does Error E-99 mean?")

USED_RAG=$(echo "$RAG_CHAT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data',{}).get('used_rag', 'False'))" 2>/dev/null)
print_info "Used RAG: $USED_RAG"

# 3. Test Function Calling (Link)
echo -e "\n${YELLOW}Test 2: Function Calling (Send Link)${NC}"
FUNC_CHAT=$(curl -s -X POST "$BASE_URL/api/chats/create-chat" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "astId=$ASSISTANT_ID" \
    -F "threadId=$THREAD_ID" \
    -F "message=Send me the documentation link please")

ACTIONS=$(echo "$FUNC_CHAT" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin).get('actions', [])))" 2>/dev/null)
if [ "$ACTIONS" != "[]" ]; then
    print_success "Function Triggered!"
else
    print_info "No function triggered (Check prompt instructions)"
fi

# ============================================================================
# PHASE 4: HISTORY & MANAGEMENT
# ============================================================================
print_header "PHASE 4: History & Management"

echo -e "${YELLOW}Fetching Chat History...${NC}"
curl -s -X GET "$BASE_URL/api/chats/history/$THREAD_ID?limit=3" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -m json.tool

echo -e "\n${YELLOW}Fetching Assistant Threads...${NC}"
curl -s -X GET "$BASE_URL/api/threads/get-thread/$ASSISTANT_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Found {len(d.get('data',[]))} threads\")"

# ============================================================================
# PHASE 5: HUMAN HANDOFF WORKFLOW
# ============================================================================
print_header "PHASE 5: Human Handoff Workflow"

# 1. Trigger Handoff (User side)
echo -e "${YELLOW}User: Requesting Human Agent...${NC}"
HANDOFF_REQ=$(curl -s -X POST "$BASE_URL/api/chats/create-chat" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "astId=$ASSISTANT_ID" \
    -F "threadId=$THREAD_ID" \
    -F "message=I am frustrated and want to talk to a human agent now.")

# 2. Agent: Check Pending
echo -e "\n${YELLOW}Agent: Checking Pending Handoffs...${NC}"
PENDING=$(curl -s -X GET "$BASE_URL/api/agent/pending-handoffs" -H "Authorization: Bearer $ACCESS_TOKEN")
# Check if our thread is in there (simple grep check for visual)
echo "$PENDING" | grep -q "$THREAD_ID" && print_success "Thread found in pending list" || print_info "Thread not immediately visible in pending (might be status logic)"

# 3. Agent: Assign Thread
echo -e "\n${YELLOW}Agent: Assigning Thread to Self...${NC}"
ASSIGN=$(curl -s -X POST "$BASE_URL/api/agent/assign/$THREAD_ID" -H "Authorization: Bearer $ACCESS_TOKEN")
format_json "$ASSIGN"

# 4. Agent: Send Message
echo -e "\n${YELLOW}Agent: Sending Support Message...${NC}"
AGENT_MSG=$(curl -s -X POST "$BASE_URL/api/agent/send-message" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{ \"thread_id\": \"$THREAD_ID\", \"message\": \"Hi, I'm the human agent. I see you have Error E-99. Let me help.\" }")
format_json "$AGENT_MSG"

# 5. Agent: List My Threads
echo -e "\n${YELLOW}Agent: Verifying 'My Threads' List...${NC}"
curl -s -X GET "$BASE_URL/api/agent/my-threads" -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Agent has {len(d.get('data',[]))} active threads\")"

# 6. Agent: Complete Handoff
echo -e "\n${YELLOW}Agent: Closing Ticket (Complete Handoff)...${NC}"
COMPLETE=$(curl -s -X POST "$BASE_URL/api/agent/complete-handoff" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{ \"thread_id\": \"$THREAD_ID\", \"notes\": \"Resolved by advising to empty crumb tray.\" }")
format_json "$COMPLETE"

# ============================================================================
# SUMMARY
# ============================================================================
print_header "FULL TEST SUITE COMPLETE"
echo -e "Assistant ID: ${YELLOW}$ASSISTANT_ID${NC}"
echo -e "Thread ID:    ${YELLOW}$THREAD_ID${NC}"
print_success "All endpoints executed sequentially."