#!/bin/bash

# =============================================================================
# New Feature Endpoints cURL Testing Script
# =============================================================================
# This script exercises the newly added Settings, Usage, and Admin endpoints.
# It follows the same style as the existing curl-* scripts and can be adjusted
# via environment variables defined below.
# Usage: bash curl-new-endpoints-tests.sh
# =============================================================================

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
EMAIL="${EMAIL:-hariomsuthar7143@gmail.com}"
PASSWORD="${PASSWORD:-heria@021}"
# Optional: provide a valid custom OpenAI key to fully test /openai-key
CUSTOM_OPENAI_KEY="${CUSTOM_OPENAI_KEY:-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}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ORIGINAL_CURL_BIN=$(command -v curl)

log_curl_command() {
    local formatted=""
    for arg in "$@"; do
        formatted+="$(printf "%q " "$arg")"
    done
    echo -e "${BLUE}${formatted}${NC}" >&2
}

curl() {
    log_curl_command curl "$@"
    "$ORIGINAL_CURL_BIN" "$@"
}

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

trim_quotes() {
    sed -e 's/^"//' -e 's/"$//'
}

# -----------------------------------------------------------------------------
# STEP 1: Authenticate & obtain token
# -----------------------------------------------------------------------------
print_header "STEP 1: Authentication"
echo -e "${YELLOW}Logging in as $EMAIL...${NC}"

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$EMAIL\",
        \"password\": \"$PASSWORD\"
    }")

format_json "$LOGIN_RESPONSE"

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json
data=json.load(sys.stdin)
print(
    data.get('data', {}).get('access_token') or
    data.get('access_token') or
    data.get('token', '')
)
" 2>/dev/null | trim_quotes)

if [ -z "$ACCESS_TOKEN" ]; then
    print_error "Unable to extract access token"
    exit 1
fi
print_success "Access token acquired"

# -----------------------------------------------------------------------------
# STEP 2: Create assistant (prerequisite for settings/usage tests)
# -----------------------------------------------------------------------------
print_header "STEP 2: Create test assistant"
ASSISTANT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/assistant/create-assistant" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d "{
        \"astName\": \"Integration Test Assistant\",
        \"astInstruction\": \"You help validate integration endpoints.\",
        \"gptModel\": \"gpt-4o-mini\",
        \"astTools\": [\"code_interpreter\"]
    }")

format_json "$ASSISTANT_RESPONSE"

ASSISTANT_ID=$(echo "$ASSISTANT_RESPONSE" | python3 -c "import sys,json
data=json.load(sys.stdin)
print(data.get('data', {}).get('astId') or data.get('data', {}).get('data', {}).get('astId',''))
" 2>/dev/null | trim_quotes)

ASSISTANT_DB_ID=$(echo "$ASSISTANT_RESPONSE" | python3 -c "import sys,json
data=json.load(sys.stdin)
print(data.get('data', {}).get('_id') or data.get('data', {}).get('data', {}).get('_id',''))
" 2>/dev/null | trim_quotes)

USER_ID=$(echo "$ASSISTANT_RESPONSE" | python3 -c "import sys,json
data=json.load(sys.stdin)
print(data.get('data', {}).get('userId') or data.get('data', {}).get('data', {}).get('userId',''))
" 2>/dev/null | trim_quotes)

ASSISTANT_API_TOKEN=$(echo "$ASSISTANT_RESPONSE" | python3 -c "import sys,json
data=json.load(sys.stdin)
print(data.get('data', {}).get('apiToken') or data.get('data', {}).get('data', {}).get('apiToken',''))
" 2>/dev/null | trim_quotes)

if [ -z "$ASSISTANT_ID" ]; then
    print_error "Assistant creation failed"
    exit 1
fi

print_success "Assistant created (astId=$ASSISTANT_ID)"
[ -n "$ASSISTANT_DB_ID" ] && print_success "Assistant DB id: $ASSISTANT_DB_ID"
[ -n "$USER_ID" ] && print_success "User id for admin calls: $USER_ID"
[ -n "$ASSISTANT_API_TOKEN" ] && echo -e "${YELLOW}Assistant API token:${NC} $ASSISTANT_API_TOKEN"

# -----------------------------------------------------------------------------
# STEP 2B: Create thread & send chat message
# -----------------------------------------------------------------------------
print_header "STEP 2B: Thread & chat smoke test"

THREAD_TITLE="Integration Test Thread $(date +%s)"
THREAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/threads/create-thread" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"astId\": \"$ASSISTANT_ID\",
        \"threadTitle\": \"$THREAD_TITLE\"
    }")

format_json "$THREAD_RESPONSE"

THREAD_ID=$(echo "$THREAD_RESPONSE" | python3 -c "import sys,json
data=json.load(sys.stdin)
print(data.get('data', {}).get('threadId',''))
" 2>/dev/null | trim_quotes)

if [ -n "$THREAD_ID" ]; then
    print_success "Thread created (threadId=$THREAD_ID)"

    CHAT_MESSAGE="Hello from automated smoke test at $(date -Iseconds)"
    CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/chats/create-chat" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -F "astId=$ASSISTANT_ID" \
        -F "threadId=$THREAD_ID" \
        -F "message=$CHAT_MESSAGE")

    format_json "$CHAT_RESPONSE"
else
    print_error "Thread creation failed; skipping chat smoke test"
fi

if [ -n "$ASSISTANT_API_TOKEN" ]; then
    echo -e "${YELLOW}Sample end-user curl using assistant apiToken:${NC}"
    cat <<EOF
curl -X POST "$BASE_URL/api/enduser/end-user-chat" \\
  -F "astName=Integration Test Assistant" \\
  -F "apiToken=$ASSISTANT_API_TOKEN" \\
  -F "message=Hello from token demo"
EOF
fi

# -----------------------------------------------------------------------------
# STEP 3: Settings API (custom OpenAI key management)
# -----------------------------------------------------------------------------
print_header "STEP 3: Settings API"

echo -e "${YELLOW}3.1 Check current OpenAI key status${NC}"
STATUS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/settings/openai-key/status" \
    -H "Authorization: Bearer $ACCESS_TOKEN")
format_json "$STATUS_RESPONSE"

echo -e "${YELLOW}3.2 Validate sample key (expected to fail unless key is valid)${NC}"
VALIDATE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/settings/validate-openai-key" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"api_key\": \"sk-test-invalid-key-for-ci\"}")
format_json "$VALIDATE_RESPONSE"

if [ -n "$CUSTOM_OPENAI_KEY" ]; then
    echo -e "${YELLOW}3.3 Setting custom user-level OpenAI key${NC}"
    SET_KEY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/settings/openai-key" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"api_key\": \"$CUSTOM_OPENAI_KEY\"}")
    format_json "$SET_KEY_RESPONSE"

    echo -e "${YELLOW}3.4 Confirming updated status${NC}"
    STATUS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/settings/openai-key/status" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    format_json "$STATUS_RESPONSE"

    echo -e "${YELLOW}3.5 Removing custom key (cleanup)${NC}"
    REMOVE_KEY_RESPONSE=$(curl -s -X DELETE "$BASE_URL/api/settings/openai-key" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    format_json "$REMOVE_KEY_RESPONSE"
else
    echo -e "${YELLOW}Skipping user-level key set/remove (CUSTOM_OPENAI_KEY not provided)${NC}"
fi

# -----------------------------------------------------------------------------
# STEP 4: Usage API (stats, history, cost)
# -----------------------------------------------------------------------------
print_header "STEP 4: Usage API"

echo -e "${YELLOW}4.1 Current usage stats${NC}"
USAGE_STATS=$(curl -s -X GET "$BASE_URL/api/usage/stats" \
    -H "Authorization: Bearer $ACCESS_TOKEN")
format_json "$USAGE_STATS"

echo -e "${YELLOW}4.2 Usage history (week)${NC}"
USAGE_HISTORY=$(curl -s -G "$BASE_URL/api/usage/history" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    --data-urlencode "period=week")
format_json "$USAGE_HISTORY"

if [ -n "$ASSISTANT_DB_ID" ]; then
    echo -e "${YELLOW}4.3 Assistant-specific usage stats${NC}"
    ASSISTANT_USAGE=$(curl -s -X GET "$BASE_URL/api/usage/assistant/$ASSISTANT_DB_ID/stats" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    format_json "$ASSISTANT_USAGE"
else
    echo -e "${YELLOW}Skipping assistant usage (assistant DB id unavailable)${NC}"
fi

echo -e "${YELLOW}4.4 Cost breakdown (month)${NC}"
COST_BREAKDOWN=$(curl -s -G "$BASE_URL/api/usage/cost-breakdown" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    --data-urlencode "period=month")
format_json "$COST_BREAKDOWN"

echo -e "${YELLOW}4.5 Export usage data (json)${NC}"
USAGE_EXPORT=$(curl -s -G "$BASE_URL/api/usage/export" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    --data-urlencode "format=json")
format_json "$USAGE_EXPORT"

# -----------------------------------------------------------------------------
# STEP 5: Admin API (limit management & system stats)
# -----------------------------------------------------------------------------
print_header "STEP 5: Admin API"

if [ -z "$USER_ID" ]; then
    echo -e "${YELLOW}User ID not available; skipping admin user-specific calls${NC}"
else
    echo -e "${YELLOW}5.1 Update user limits${NC}"
    ADMIN_UPDATE=$(curl -s -X PUT "$BASE_URL/api/admin/user/$USER_ID/limits" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "user_id": "'"$USER_ID"'",
            "daily_messages": 150,
            "weekly_messages": 800,
            "monthly_tokens": 1500000,
            "max_assistants": 10,
            "max_threads_per_assistant": 75
        }')
    format_json "$ADMIN_UPDATE"

    echo -e "${YELLOW}5.2 Get user limits${NC}"
    ADMIN_GET_LIMITS=$(curl -s -X GET "$BASE_URL/api/admin/user/$USER_ID/limits" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    format_json "$ADMIN_GET_LIMITS"

    echo -e "${YELLOW}5.3 Get user usage${NC}"
    ADMIN_GET_USAGE=$(curl -s -X GET "$BASE_URL/api/admin/user/$USER_ID/usage" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    format_json "$ADMIN_GET_USAGE"

    echo -e "${YELLOW}5.4 Reset user usage (daily)${NC}"
    ADMIN_RESET_USAGE=$(curl -s -X POST "$BASE_URL/api/admin/user/$USER_ID/reset-usage" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "user_id": "'"$USER_ID"'",
            "reset_daily": true
        }')
    format_json "$ADMIN_RESET_USAGE"
fi

echo -e "${YELLOW}5.5 System overview${NC}"
ADMIN_OVERVIEW=$(curl -s -X GET "$BASE_URL/api/admin/stats/overview" \
    -H "Authorization: Bearer $ACCESS_TOKEN")
format_json "$ADMIN_OVERVIEW"

echo -e "${YELLOW}5.6 Top users${NC}"
ADMIN_TOP_USERS=$(curl -s -G "$BASE_URL/api/admin/stats/top-users" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    --data-urlencode "limit=5")
format_json "$ADMIN_TOP_USERS"

# -----------------------------------------------------------------------------
# SUMMARY
# -----------------------------------------------------------------------------
print_header "SUMMARY"
echo -e "${GREEN}✓ Completed Settings, Usage, and Admin endpoint checks${NC}"
echo -e "${BLUE}Assistant AstId:${NC} ${ASSISTANT_ID:-N/A}"
echo -e "${BLUE}Assistant DB Id:${NC} ${ASSISTANT_DB_ID:-N/A}"
echo -e "${BLUE}User Id:${NC} ${USER_ID:-N/A}"

if [ -z "$CUSTOM_OPENAI_KEY" ]; then
    echo -e "${YELLOW}Note:${NC} Provide CUSTOM_OPENAI_KEY env var to fully exercise key set/remove flows."
fi

echo -e "\n${GREEN}Tests finished!${NC}\n"

