import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict
import secrets
from bson import ObjectId
from fastapi import HTTPException


class AuthController:
    def __init__(self, jwt_secret: str, jwt_algorithm: str = "HS256"):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.access_token_expire_minutes = 60  # 1 hour
        self.refresh_token_expire_days = 30  # 30 days
        self.verification_code_expire_hours = 24  # 24 hours

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False

    def generate_verification_code(self) -> str:
        """Generate 6-digit verification code"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

    def create_access_token(
        self, 
        user_id: str, 
        email: str, 
        role: str = "owner",
        assigned_bots: Optional[list] = None,
        is_team_member: bool = False
    ) -> str:
        """Create JWT access token with optional team member scoping"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "sub": user_id,
            "email": email,
            "type": "access",
            "role": role,
            "is_team_member": is_team_member,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        # Add assigned bots for team members
        if is_team_member and assigned_bots:
            payload["assigned_bots"] = assigned_bots
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def create_refresh_token(self, user_id: str, email: str) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        payload = {
            "sub": user_id,
            "email": email,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )

            # Verify token type
            if payload.get("type") != token_type:
                return None

            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_verification_expiry(self) -> datetime:
        """Get expiry time for verification code"""
        return datetime.utcnow() + timedelta(hours=self.verification_code_expire_hours)

    def generate_magic_link_token(self) -> str:
        """Generate a secure magic link token for passwordless login"""
        return secrets.token_urlsafe(32)

    def generate_magic_link_expires_at(self, hours: int = 24) -> datetime:
        """Generate expiry time for magic link token"""
        return datetime.utcnow() + timedelta(hours=hours)

    def create_team_member_access_token(
        self,
        member_id: str,
        email: str,
        role: str,
        assigned_bots: list
    ) -> str:
        """Create access token for team member with bot scoping"""
        return self.create_access_token(
            user_id=member_id,
            email=email,
            role=role,
            assigned_bots=assigned_bots,
            is_team_member=True
        )

