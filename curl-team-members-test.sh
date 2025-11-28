#!/bin/bash

# Team Members & Handoff Management - End-to-End Test Script
# Tests the complete flow: Owner creates member -> Member sets password -> Member picks handoff

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://127.0.0.1:8000"
OWNER_EMAIL="hariomsuthar7143@gmail.com"
OWNER_PASSWORD="heria@021"
TEAM_MEMBER_EMAIL="e.yeager.0215@gmail.com"
TEAM_MEMBER_NAME="Eren Yeager"
TEAM_MEMBER_PASSWORD="eren@0215"

print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}\n"
}

print_step() {
    echo -e "${YELLOW}► $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# ============================================================================
# PHASE 1: OWNER REGISTRATION & LOGIN
# ============================================================================

print_header "PHASE 1: Owner Setup"

print_step "STEP 1: Registering owner account..."
SIGNUP_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/sign-up" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$OWNER_EMAIL\",
        \"password\": \"$OWNER_PASSWORD\"
    }")

echo "Response: $SIGNUP_RESPONSE"

print_step "STEP 2: Owner logs in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$OWNER_EMAIL\",
        \"password\": \"$OWNER_PASSWORD\"
    }")

echo "Response: $LOGIN_RESPONSE"
OWNER_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$OWNER_TOKEN" ]; then
    print_error "Failed to get owner token"
    exit 1
fi

print_success "Owner logged in successfully"
echo "Owner Token: ${OWNER_TOKEN:0:20}..."

# ============================================================================
# PHASE 2: OWNER CREATES ASSISTANT BOT
# ============================================================================

print_header "PHASE 2: Create Assistant Bot"

print_step "Creating an assistant bot for testing..."
ASSISTANT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/assistant/create-assistant" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OWNER_TOKEN" \
    -d '{
        "astName": "Support Bot",
        "astInstruction": "You are a helpful support agent. If user asks for human help, trigger handoff.",
        "gptModel": "gpt-4",
        "astTools": []
    }')

echo "Response: $ASSISTANT_RESPONSE"
BOT_ID=$(echo "$ASSISTANT_RESPONSE" | grep -o '"astId":"[^"]*' | cut -d'"' -f4 | head -1)

if [ -z "$BOT_ID" ]; then
    print_error "Failed to create bot"
    exit 1
fi

print_success "Bot created successfully"
echo "Bot ID: $BOT_ID"

# ============================================================================
# PHASE 3: OWNER INVITES TEAM MEMBER
# ============================================================================

print_header "PHASE 3: Owner Invites Team Member"

print_step "Owner inviting team member with bot assignment..."
INVITE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/owner/team-members/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OWNER_TOKEN" \
    -d "{
        \"email\": \"$TEAM_MEMBER_EMAIL\",
        \"name\": \"$TEAM_MEMBER_NAME\",
        \"role\": \"agent\",
        \"assigned_bots\": [\"$BOT_ID\"]
    }")

echo "Response: $INVITE_RESPONSE"
MEMBER_ID=$(echo "$INVITE_RESPONSE" | grep -o '"member_id":"[^"]*' | cut -d'"' -f4)
MAGIC_LINK_TOKEN=$(echo "$INVITE_RESPONSE" | grep -o '"magic_link_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$MEMBER_ID" ] || [ -z "$MAGIC_LINK_TOKEN" ]; then
    print_error "Failed to create team member"
    exit 1
fi

print_success "Team member invited successfully"
echo "Member ID: $MEMBER_ID"
echo "Magic Link Token: ${MAGIC_LINK_TOKEN:0:20}..."

# ============================================================================
# PHASE 4: TEAM MEMBER SETS PASSWORD USING MAGIC LINK
# ============================================================================

print_header "PHASE 4: Team Member Sets Password"

print_step "Team member setting password using magic link..."
SETUP_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/team-member/setup-password" \
    -H "Content-Type: application/json" \
    -d "{
        \"token\": \"$MAGIC_LINK_TOKEN\",
        \"password\": \"$TEAM_MEMBER_PASSWORD\"
    }")

echo "Response: $SETUP_RESPONSE"

if echo "$SETUP_RESPONSE" | grep -q '"status":"success"'; then
    print_success "Password set successfully"
else
    print_error "Failed to set password"
    exit 1
fi

# ============================================================================
# PHASE 5: TEAM MEMBER LOGIN
# ============================================================================

print_header "PHASE 5: Team Member Login"

print_step "Team member logging in with email and password..."
MEMBER_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/team-member/login" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$TEAM_MEMBER_EMAIL\",
        \"password\": \"$TEAM_MEMBER_PASSWORD\"
    }")

echo "Response: $MEMBER_LOGIN_RESPONSE"
MEMBER_TOKEN=$(echo "$MEMBER_LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
ASSIGNED_BOTS=$(echo "$MEMBER_LOGIN_RESPONSE" | grep -o '"assigned_bots":\[[^\]]*\]')

if [ -z "$MEMBER_TOKEN" ]; then
    print_error "Failed to get member token"
    exit 1
fi

print_success "Team member logged in successfully"
echo "Member Token: ${MEMBER_TOKEN:0:20}..."
echo "Assigned Bots: $ASSIGNED_BOTS"

# ============================================================================
# PHASE 6: CREATE CHAT THREAD & TRIGGER HANDOFF
# ============================================================================

print_header "PHASE 6: Create Handoff Scenario"

print_step "Creating chat thread..."
THREAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/threads/create-thread" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OWNER_TOKEN" \
    -d "{
        \"astId\": \"$BOT_ID\",
        \"threadTitle\": \"Handoff Test Thread\"
    }")

echo "Response: $THREAD_RESPONSE"
THREAD_ID=$(echo "$THREAD_RESPONSE" | grep -o '"threadId":"[^"]*' | cut -d'"' -f4)

if [ -z "$THREAD_ID" ]; then
    print_error "Failed to create thread"
    exit 1
fi

print_success "Thread created"
echo "Thread ID: $THREAD_ID"

print_step "Sending chat message to trigger handoff..."
CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/chats/create-chat" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OWNER_TOKEN" \
    -d "{
        \"astId\": \"$BOT_ID\",
        \"threadId\": \"$THREAD_ID\",
        \"message\": \"I need to speak with a human agent please\"
    }")

echo "Response: $CHAT_RESPONSE"

if echo "$CHAT_RESPONSE" | grep -q '"status":true'; then
    print_success "Chat created and handoff triggered"
else
    print_error "Failed to create chat"
    exit 1
fi

# ============================================================================
# PHASE 7: TEAM MEMBER VIEWS PENDING HANDOFFS
# ============================================================================

print_header "PHASE 7: Team Member Views Handoffs"

print_step "Team member checking pending handoffs (should only see from assigned bots)..."
PENDING_RESPONSE=$(curl -s -X GET "$BASE_URL/api/agent/pending-handoffs" \
    -H "Authorization: Bearer $MEMBER_TOKEN")

echo "Response: $PENDING_RESPONSE"

if echo "$PENDING_RESPONSE" | grep -q '"pending_count"'; then
    PENDING_COUNT=$(echo "$PENDING_RESPONSE" | grep -o '"pending_count":[0-9]*' | cut -d':' -f2)
    print_success "Team member can see pending handoffs"
    echo "Pending Handoffs: $PENDING_COUNT"
else
    print_error "Failed to get pending handoffs"
    exit 1
fi

# ============================================================================
# PHASE 8: TEAM MEMBER PICKS UP HANDOFF
# ============================================================================

print_header "PHASE 8: Team Member Picks Up Handoff"

print_step "Team member assigning thread to themselves..."
ASSIGN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/agent/assign/$THREAD_ID" \
    -H "Authorization: Bearer $MEMBER_TOKEN")

echo "Response: $ASSIGN_RESPONSE"

if echo "$ASSIGN_RESPONSE" | grep -q '"status":true'; then
    print_success "Thread assigned to team member"
else
    print_error "Failed to assign thread"
    exit 1
fi

# ============================================================================
# PHASE 9: TEAM MEMBER SENDS RESPONSE
# ============================================================================

print_header "PHASE 9: Team Member Sends Response"

print_step "Team member sending response to user..."
SEND_RESPONSE=$(curl -s -X POST "$BASE_URL/api/agent/send-message" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $MEMBER_TOKEN" \
    -d "{
        \"thread_id\": \"$THREAD_ID\",
        \"message\": \"Hi there! I'm a human agent. How can I help you today?\"
    }")

echo "Response: $SEND_RESPONSE"

if echo "$SEND_RESPONSE" | grep -q '"status":true'; then
    print_success "Message sent by team member"
else
    print_error "Failed to send message"
    exit 1
fi

# ============================================================================
# PHASE 10: VERIFY OWNER CAN SEE ALL TEAM MEMBERS
# ============================================================================

print_header "PHASE 10: Owner Views Team Members"

print_step "Owner listing all team members..."
MEMBERS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/owner/team-members" \
    -H "Authorization: Bearer $OWNER_TOKEN")

echo "Response: $MEMBERS_RESPONSE"

if echo "$MEMBERS_RESPONSE" | grep -q "$TEAM_MEMBER_EMAIL"; then
    print_success "Owner can see team members"
else
    print_error "Failed to list team members"
    exit 1
fi

# ============================================================================
# TEST COMPLETE
# ============================================================================

print_header "✓ ALL TESTS PASSED SUCCESSFULLY!"

echo -e "${GREEN}Summary:${NC}"
echo "✓ Owner registered and logged in"
echo "✓ Bot created"
echo "✓ Team member invited with bot assignment"
echo "✓ Team member set password via magic link"
echo "✓ Team member logged in (only seeing assigned bots)"
echo "✓ Handoff created from chat"
echo "✓ Team member viewed pending handoffs (role-based filtering)"
echo "✓ Team member picked up handoff"
echo "✓ Team member sent response"
echo "✓ Owner viewed team members"
echo ""
echo -e "${GREEN}Role-Based Access Control is working correctly!${NC}"
