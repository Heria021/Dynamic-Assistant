from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class UserLimits(BaseModel):
    """User rate limits configuration."""

    daily_messages: int = Field(default=100, ge=0)
    weekly_messages: int = Field(default=500, ge=0)
    monthly_tokens: int = Field(default=1_000_000, ge=0)
    max_assistants: int = Field(default=5, ge=1)
    max_threads_per_assistant: int = Field(default=50, ge=1)


class UserUsage(BaseModel):
    """Current usage tracking snapshot."""

    messages_today: int = Field(default=0, ge=0)
    messages_this_week: int = Field(default=0, ge=0)
    tokens_this_month: int = Field(default=0, ge=0)
    assistants_created: int = Field(default=0, ge=0)
    threads_created: int = Field(default=0, ge=0)
    last_reset_daily: Optional[datetime] = None
    last_reset_weekly: Optional[datetime] = None
    last_reset_monthly: Optional[datetime] = None


class OpenAIKeyUpdate(BaseModel):
    """Request body for setting/updating an OpenAI API key."""

    api_key: str = Field(..., min_length=20, description="OpenAI API key (sk-...)")

    @validator("api_key")
    def validate_key_format(cls, value: str) -> str:  # noqa: N805
        if not value.startswith("sk-"):
            raise ValueError('OpenAI API keys must start with "sk-"')
        return value


class OpenAIKeyStatus(BaseModel):
    """Status response for OpenAI key configuration."""

    has_custom_key: bool
    key_type: str
    message: str
    assistants_using_custom_key: Optional[int] = None


class UsageStats(BaseModel):
    """Current usage statistics for a user."""

    user_id: str
    messages_today: int
    messages_this_week: int
    tokens_this_month: int
    assistants_created: int
    threads_created: int
    daily_messages_limit: int
    weekly_messages_limit: int
    monthly_tokens_limit: int
    max_assistants: int
    max_threads_per_assistant: int
    daily_remaining: int
    weekly_remaining: int
    tokens_remaining: int
    assistants_remaining: int
    can_send_message: bool
    can_create_assistant: bool
    can_create_thread: bool
    warning: Optional[str] = None
    blocked_reason: Optional[str] = None


class UsageHistoryItem(BaseModel):
    """Individual usage history record entry."""

    timestamp: datetime
    action: str
    assistant_id: Optional[str] = None
    assistant_name: Optional[str] = None
    thread_id: Optional[str] = None
    tokens_used: int = 0
    model_used: Optional[str] = None
    cost_estimate: float = 0.0
    used_custom_key: bool = False


class UsageHistory(BaseModel):
    """Usage history response payload."""

    user_id: str
    period: str
    total_messages: int
    total_tokens: int
    total_cost_estimate: float
    items: List[UsageHistoryItem]


class AssistantUsageStats(BaseModel):
    """Usage statistics scoped to a single assistant."""

    assistant_id: str
    assistant_name: str
    total_messages: int
    total_tokens: int
    total_threads: int
    cost_estimate: float
    last_used: Optional[datetime] = None
    avg_response_time_ms: Optional[float] = None
    most_active_day: Optional[str] = None


class UpdateUserLimits(BaseModel):
    """Admin payload for updating a user's rate limits."""

    user_id: str
    daily_messages: Optional[int] = Field(None, ge=0)
    weekly_messages: Optional[int] = Field(None, ge=0)
    monthly_tokens: Optional[int] = Field(None, ge=0)
    max_assistants: Optional[int] = Field(None, ge=1)
    max_threads_per_assistant: Optional[int] = Field(None, ge=1)


class ResetUserUsage(BaseModel):
    """Admin payload for resetting usage counters."""

    user_id: str
    reset_daily: bool = False
    reset_weekly: bool = False
    reset_monthly: bool = False
    reset_all: bool = False


class RateLimitError(BaseModel):
    """Detailed rate limit error description."""

    code: str
    message: str
    used: int
    limit: int
    resets_at: datetime
    hours_until_reset: float
    suggestions: List[str] = []
    can_upgrade: bool = True


class TokenPricing(BaseModel):
    """OpenAI token pricing definition."""

    model: str
    input_cost_per_1k: float
    output_cost_per_1k: float


class CostEstimate(BaseModel):
    """Estimated cost for a single message exchange."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    model: str
    estimated_cost: float
    currency: str = "USD"


# ============================================================================
# TEAM MEMBER & HANDOFF MANAGEMENT MODELS
# ============================================================================

class MagicLinkCredential(BaseModel):
    """Magic link credential for one-time passwordless login."""
    
    token: str
    created_at: datetime
    expires_at: datetime
    used_at: Optional[datetime] = None
    is_used: bool = False


class PasswordCredential(BaseModel):
    """Password credential for team member login."""
    
    hash: str
    set_at: datetime


class LoginCredentials(BaseModel):
    """Login credentials for a team member."""
    
    type: str = Field(..., description="'password' or 'magic_link'")
    password_hash: Optional[str] = None
    magic_link: Optional[MagicLinkCredential] = None


class TeamMember(BaseModel):
    """Team member under owner's workspace."""
    
    member_id: str = Field(..., description="UUID of team member")
    owner_id: str = Field(..., description="UUID of owner who created this member")
    email: str
    name: str
    role: str = Field(default="agent", description="'agent' or 'supervisor'")
    assigned_bots: List[str] = Field(default=[], description="List of assistant IDs assigned")
    login_credentials: LoginCredentials
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None
    invited_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    metadata: dict = Field(default={}, description="Additional metadata")


class CreateTeamMemberRequest(BaseModel):
    """Request to create new team member."""
    
    email: str
    name: str
    role: str = Field(default="agent", description="'agent' or 'supervisor'")
    assigned_bots: List[str] = Field(default=[], description="Bot IDs to assign")


class UpdateTeamMemberRequest(BaseModel):
    """Request to update team member."""
    
    name: Optional[str] = None
    role: Optional[str] = None
    assigned_bots: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TeamMemberResponse(BaseModel):
    """Response for team member info."""
    
    member_id: str
    email: str
    name: str
    role: str
    assigned_bots: List[str]
    is_active: bool
    created_at: datetime
    confirmed_at: Optional[datetime] = None


class SetPasswordRequest(BaseModel):
    """Request to set password for team member."""
    
    token: str = Field(..., description="Magic link token")
    password: str = Field(..., min_length=8, description="New password")


class MagicLinkLoginRequest(BaseModel):
    """Request to login with magic link."""
    
    token: str


class TeamMemberLoginRequest(BaseModel):
    """Request for team member login."""
    
    email: str
    password: str


class InviteTeamMemberResponse(BaseModel):
    """Response when inviting new team member."""
    
    member_id: str
    email: str
    name: str
    invite_sent: bool
    magic_link_token: str = Field(..., description="Token for setting password")
    message: str


