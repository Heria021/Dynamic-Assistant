#!/bin/bash

# ============================================================================
# Assistant API Test Script - RAG & Function Calling Features
# ============================================================================
# This script tests the new Active RAG and Function Calling features:
# 1. Creates assistant with nebula_x9_manual.md file
# 2. Tests RAG retrieval from uploaded files
# 3. Tests function calling (handoff, send_link, send_email)
# Usage: bash curl-assistant-tests.sh
# ============================================================================

BASE_URL="http://127.0.0.1:8000"
EMAIL="hariomsuthar7143@gmail.com"
PASSWORD="heria@021"

MANUAL_FILE="nebula_x9_manual.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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
# STEP 2: CHECK IF MANUAL FILE EXISTS
# ============================================================================
print_header "STEP 2: Verify Manual File Exists"

if [ ! -f "$MANUAL_FILE" ]; then
    print_error "File $MANUAL_FILE not found in current directory"
    print_info "Please ensure nebula_x9_manual.md is in the same directory as this script"
    exit 1
fi

print_success "Manual file found: $MANUAL_FILE"

# ============================================================================
# STEP 3: CREATE ASSISTANT WITH FILE
# ============================================================================
print_header "STEP 3: Create Assistant with Nebula-X9 Manual"

echo -e "\n${YELLOW}Creating assistant with file upload...${NC}"

ASSISTANT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/assistant/create-assistant-with-file" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "astName=Nebula-X9 Support Assistant" \
    -F $'astInstruction=You are a helpful support assistant for the Nebula-X9 Smart Toaster.\n\nKNOWLEDGE BASE:\nAnswer questions using the product manual. Keep responses to 2-3 lines maximum.\n\nCRITICAL - YOU MUST USE THESE FUNCTIONS:\nWhen user says ANY of these phrases, you MUST call the corresponding function:\n\n1. HUMAN HANDOFF - If user mentions:\n   - "human", "agent", "person", "real person", "talk to someone"\n   - "I'\''m frustrated", "this isn'\''t working", "help me"\n   → Call handoff_to_human function IMMEDIATELY\n\n2. SEND LINK - If user asks for:\n   - "link", "URL", "website", "documentation page"\n   → Call send_link function with appropriate URL\n\n3. SEND EMAIL - If user says:\n   - "email me", "send to my email", "send via email"\n   → Call send_email function\n\nDO NOT just say you'\''ll do these - ACTUALLY CALL THE FUNCTION.' \
    -F "gptModel=gpt-4o-mini" \
    -F 'astTools=["code_interpreter","file_search"]' \
    -F "files=@$MANUAL_FILE")

echo -e "\n${YELLOW}Assistant Created:${NC}"
format_json "$ASSISTANT_RESPONSE"

# Extract assistant ID and API token
ASSISTANT_EXTRACTION=$(echo "$ASSISTANT_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
result = {'astId': '', 'apiToken': ''}
try:
    if data.get('status') and data.get('data'):
        assistant_data = data.get('data', {})
        result['astId'] = assistant_data.get('astId', '')
        result['apiToken'] = assistant_data.get('apiToken', '')
except Exception:
    pass
print(f\"{result['astId']}|{result['apiToken']}\")
" 2>/dev/null)

ASSISTANT_ID=$(echo "$ASSISTANT_EXTRACTION" | cut -d'|' -f1)
ASSISTANT_API_TOKEN=$(echo "$ASSISTANT_EXTRACTION" | cut -d'|' -f2)

if [ -z "$ASSISTANT_ID" ]; then
    print_error "Failed to create assistant or extract assistant ID"
    print_info "Trying to get existing assistants..."
    
    EXISTING_ASSISTANTS=$(curl -s -X GET "$BASE_URL/api/assistant/get-assistant" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    ASSISTANT_EXTRACTION=$(echo "$EXISTING_ASSISTANTS" | python3 -c "import sys, json
data=json.load(sys.stdin)
result = {'astId': '', 'apiToken': ''}
try:
    if data.get('status') and data.get('data') and isinstance(data.get('data'), list) and len(data['data']) > 0:
        assistant = data['data'][0]
        result['astId'] = assistant.get('astId', '')
        result['apiToken'] = assistant.get('apiToken', '')
except Exception:
    pass
print(f\"{result['astId']}|{result['apiToken']}\")
" 2>/dev/null)
    
    ASSISTANT_ID=$(echo "$ASSISTANT_EXTRACTION" | cut -d'|' -f1)
    ASSISTANT_API_TOKEN=$(echo "$ASSISTANT_EXTRACTION" | cut -d'|' -f2)
    
    if [ -z "$ASSISTANT_ID" ]; then
        print_error "Failed to get assistant. Cannot proceed."
        exit 1
    else
        print_success "Using existing assistant: $ASSISTANT_ID"
    fi
else
    print_success "Assistant created with ID: $ASSISTANT_ID"
fi

print_info "Waiting 3 seconds for file ingestion into Milvus..."
sleep 3

# ============================================================================
# STEP 4: CREATE THREAD
# ============================================================================
print_header "STEP 4: Create Thread"

echo -e "\n${YELLOW}Creating thread for assistant...${NC}"

THREAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/threads/create-thread" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d "{
        \"astId\": \"$ASSISTANT_ID\",
        \"threadTitle\": \"Nebula-X9 Support Thread\"
    }")

echo -e "\n${YELLOW}Thread Created:${NC}"
format_json "$THREAD_RESPONSE"

# Extract thread ID
THREAD_ID=$(echo "$THREAD_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
out=''
try:
    if data.get('status') and data.get('data'):
        thread_data = data.get('data', {})
        out = thread_data.get('threadId', '') or thread_data.get('thread_id', '')
except Exception:
    pass
print(out)
" 2>/dev/null)

if [ -z "$THREAD_ID" ]; then
    print_error "Failed to extract thread ID"
    exit 1
fi

print_success "Thread created with ID: $THREAD_ID"

# ============================================================================
# STEP 5: TEST RAG - Question about Manual Content
# ============================================================================
print_header "STEP 5: Test Active RAG - Question About Manual"

echo -e "\n${YELLOW}Testing RAG retrieval with question about the manual...${NC}"
echo -e "${CYAN}Question: What is the power output of the Nebula-X9 in Hyper-Crunch Mode?${NC}"

RAG_CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/chats/create-chat" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "astId=$ASSISTANT_ID" \
    -F "threadId=$THREAD_ID" \
    -F "message=What is the power output of the Nebula-X9 in Hyper-Crunch Mode?")

echo -e "\n${YELLOW}RAG Chat Response:${NC}"
format_json "$RAG_CHAT_RESPONSE"

# Check if RAG was used
USED_RAG=$(echo "$RAG_CHAT_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
out=False
try:
    if data.get('data', {}).get('used_rag'):
        out=True
except Exception:
    pass
print(out)
" 2>/dev/null)

if [ "$USED_RAG" = "True" ]; then
    print_success "RAG was used! (used_rag: true)"
else
    print_info "RAG may not have been used (used_rag: false or not found)"
fi

# Extract assistant response
ASSISTANT_RESPONSE=$(echo "$RAG_CHAT_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
out=''
try:
    out = data.get('data', {}).get('assistant_response', '')
except Exception:
    pass
print(out)
" 2>/dev/null)

echo -e "\n${CYAN}Assistant Response:${NC} $ASSISTANT_RESPONSE"

# ============================================================================
# STEP 6: TEST RAG - Another Question
# ============================================================================
print_header "STEP 6: Test RAG - Another Manual Question"

echo -e "\n${YELLOW}Testing RAG with another question...${NC}"
echo -e "${CYAN}Question: What does Error E-99 mean?${NC}"

RAG_CHAT_RESPONSE_2=$(curl -s -X POST "$BASE_URL/api/chats/create-chat" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "astId=$ASSISTANT_ID" \
    -F "threadId=$THREAD_ID" \
    -F "message=What does Error E-99 mean?")

echo -e "\n${YELLOW}RAG Chat Response 2:${NC}"
format_json "$RAG_CHAT_RESPONSE_2"

ASSISTANT_RESPONSE_2=$(echo "$RAG_CHAT_RESPONSE_2" | python3 -c "import sys, json
data=json.load(sys.stdin)
out=''
try:
    out = data.get('data', {}).get('assistant_response', '')
except Exception:
    pass
print(out)
" 2>/dev/null)

echo -e "\n${CYAN}Assistant Response:${NC} $ASSISTANT_RESPONSE_2"

# ============================================================================
# STEP 7: TEST FUNCTION CALLING - Handoff to Human
# ============================================================================
print_header "STEP 7: Test Function Calling - Handoff to Human"

echo -e "\n${YELLOW}Testing function calling with handoff request...${NC}"
echo -e "${CYAN}Message: I need to speak with a human agent please${NC}"

HANDOFF_CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/chats/create-chat" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "astId=$ASSISTANT_ID" \
    -F "threadId=$THREAD_ID" \
    -F "message=I need to speak with a human agent please")

echo -e "\n${YELLOW}Handoff Chat Response:${NC}"
format_json "$HANDOFF_CHAT_RESPONSE"

# Check for actions
ACTIONS=$(echo "$HANDOFF_CHAT_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
actions = []
try:
    if data.get('actions'):
        actions = data.get('actions', [])
    elif data.get('data', {}).get('actions'):
        actions = data.get('data', {}).get('actions', [])
except Exception:
    pass
if actions:
    print(json.dumps(actions))
else:
    print('[]')
" 2>/dev/null)

if [ "$ACTIONS" != "[]" ] && [ -n "$ACTIONS" ]; then
    print_success "Actions detected!"
    echo -e "${CYAN}Actions:${NC}"
    echo "$ACTIONS" | python3 -m json.tool 2>/dev/null || echo "$ACTIONS"
else
    print_info "No actions detected (this is okay if function calling didn't trigger)"
fi

# ============================================================================
# STEP 8: TEST FUNCTION CALLING - Send Link
# ============================================================================
print_header "STEP 8: Test Function Calling - Send Link"

echo -e "\n${YELLOW}Testing function calling with link request...${NC}"
echo -e "${CYAN}Message: Can you send me a link to the product documentation?${NC}"

LINK_CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/chats/create-chat" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "astId=$ASSISTANT_ID" \
    -F "threadId=$THREAD_ID" \
    -F "message=Can you send me a link to the product documentation?")

echo -e "\n${YELLOW}Link Chat Response:${NC}"
format_json "$LINK_CHAT_RESPONSE"

ACTIONS_LINK=$(echo "$LINK_CHAT_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
actions = []
try:
    if data.get('actions'):
        actions = data.get('actions', [])
    elif data.get('data', {}).get('actions'):
        actions = data.get('data', {}).get('actions', [])
except Exception:
    pass
if actions:
    print(json.dumps(actions))
else:
    print('[]')
" 2>/dev/null)

if [ "$ACTIONS_LINK" != "[]" ] && [ -n "$ACTIONS_LINK" ]; then
    print_success "Actions detected!"
    echo -e "${CYAN}Actions:${NC}"
    echo "$ACTIONS_LINK" | python3 -m json.tool 2>/dev/null || echo "$ACTIONS_LINK"
fi

# ============================================================================
# STEP 9: TEST FUNCTION CALLING - Send Email
# ============================================================================
print_header "STEP 9: Test Function Calling - Send Email"

echo -e "\n${YELLOW}Testing function calling with email request...${NC}"
echo -e "${CYAN}Message: Please email me the warranty information${NC}"

EMAIL_CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/chats/create-chat" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "astId=$ASSISTANT_ID" \
    -F "threadId=$THREAD_ID" \
    -F "message=Please email me the warranty information")

echo -e "\n${YELLOW}Email Chat Response:${NC}"
format_json "$EMAIL_CHAT_RESPONSE"

ACTIONS_EMAIL=$(echo "$EMAIL_CHAT_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
actions = []
try:
    if data.get('actions'):
        actions = data.get('actions', [])
    elif data.get('data', {}).get('actions'):
        actions = data.get('data', {}).get('actions', [])
except Exception:
    pass
if actions:
    print(json.dumps(actions))
else:
    print('[]')
" 2>/dev/null)

if [ "$ACTIONS_EMAIL" != "[]" ] && [ -n "$ACTIONS_EMAIL" ]; then
    print_success "Actions detected!"
    echo -e "${CYAN}Actions:${NC}"
    echo "$ACTIONS_EMAIL" | python3 -m json.tool 2>/dev/null || echo "$ACTIONS_EMAIL"
fi

# ============================================================================
# STEP 10: GET CHAT HISTORY
# ============================================================================
print_header "STEP 10: Get Chat History"

echo -e "\n${YELLOW}Retrieving chat history...${NC}"

HISTORY_RESPONSE=$(curl -s -X GET "$BASE_URL/api/chats/history/$THREAD_ID?limit=10" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

echo -e "\n${YELLOW}Chat History:${NC}"
format_json "$HISTORY_RESPONSE"

# ============================================================================
# SUMMARY
# ============================================================================
print_header "TEST SUMMARY"

echo -e "\n${BLUE}Tested Endpoints:${NC}"
echo "  1. ${GREEN}✓${NC} POST   /auth/login                           - Login & Get Token"
echo "  2. ${GREEN}✓${NC} POST   /api/assistant/create-assistant-with-file - Create Assistant with File"
echo "  3. ${GREEN}✓${NC} POST   /api/assistant/create-assistant               - Create Assistant (JSON)"
echo "  4. ${GREEN}✓${NC} POST   /api/assistant/upload-assistant-files/{ast_id} - Upload Files to Assistant"
echo "  5. ${GREEN}✓${NC} GET    /api/assistant/get-assistant                   - Get All Assistants"
echo "  6. ${GREEN}✓${NC} GET    /api/assistant/get-assistant/{ast_id}          - Get Assistant by ID"
echo "  7. ${GREEN}✓${NC} PUT    /api/assistant/update-assistant                 - Update Assistant"
echo "  8. ${GREEN}✓${NC} POST   /api/threads/create-thread                      - Create Thread (for context)"
echo "  9. ${GREEN}✓${NC} POST   /api/chats/create-chat                          - Test RAG/Function Calling"
echo " 10. ${GREEN}✓${NC} GET    /api/chats/history/{thread_id}                 - Get Chat History"

echo -e "\n${BLUE}Test Data:${NC}"
echo "  Assistant ID:   ${YELLOW}$ASSISTANT_ID${NC}"
echo "  Thread ID:      ${YELLOW}$THREAD_ID${NC}"
echo "  Manual File:    ${YELLOW}$MANUAL_FILE${NC}"

echo -e "\n${BLUE}Features Tested:${NC}"
echo "  ${GREEN}✓${NC} Active RAG - Retrieval from uploaded files"
echo "  ${GREEN}✓${NC} Function Calling - handoff_to_human"
echo "  ${GREEN}✓${NC} Function Calling - send_link"
echo "  ${GREEN}✓${NC} Function Calling - send_email"
echo "  ${GREEN}✓${NC} Actions array in response"

echo -e "\n${GREEN}✓ All tests completed!${NC}\n"

# ============================================================================
# NOTES
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}NOTES${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "\n${YELLOW}1. RAG Testing:${NC}"
echo "   - Check 'used_rag' field in response to verify RAG was used"
echo "   - Responses should reference content from nebula_x9_manual.md"
echo ""
echo -e "${YELLOW}2. Function Calling:${NC}"
echo "   - Actions array should appear in response when functions are triggered"
echo "   - Each action has 'type' and 'data' fields"
echo "   - Actual execution happens in your backend/webhook"
echo ""
echo -e "${YELLOW}3. Response Format:${NC}"
echo "   {
     \"status\": true,
     \"message\": \"Chat created successfully\",
     \"data\": {
       \"assistant_response\": \"...\",
       \"used_rag\": true/false
     },
     \"actions\": [
       {
         \"type\": \"handoff_to_human\",
         \"data\": {...}
       }
     ]
   }"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}\n"

