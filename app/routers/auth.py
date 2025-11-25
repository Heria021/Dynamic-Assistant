import os
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.controllers.auth_controller import AuthController
from app.services.email_service import EmailService
import app.utils.mongo_utils as mongo_utils
import app.models.model_types as modelType
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Initialize services
jwt_secret = os.getenv('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-this-in-production-min-32-characters')
auth_controller = AuthController(jwt_secret=jwt_secret)

try:
    email_service = EmailService(
        credentials_file=os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json'),
        token_file=os.getenv('GMAIL_TOKEN_FILE', 'token.pickle')
    )
except Exception as e:
    print(f"Warning: Gmail service not configured: {e}")
    email_service = None


@router.post("/sign-up")
async def sign_up(sign_up_request: modelType.SignUpRequest):
    """Sign up new user with email and password"""
    try:
        # Check if user already exists
        existing_user = mongo_utils.find_user_by_email(sign_up_request.email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="User with this email already exists"
            )

        # Hash password
        password_hash = auth_controller.hash_password(sign_up_request.password)

        # Generate verification code
        verification_code = auth_controller.generate_verification_code()

        # Create user in database
        user_id = mongo_utils.create_user(
            email=sign_up_request.email,
            password_hash=password_hash,
            verification_code=verification_code,
            is_confirmed=False
        )

        # Send verification email
        if email_service:
            try:
                email_service.send_verification_email(
                    to_email=sign_up_request.email,
                    verification_code=verification_code
                )
            except Exception as e:
                print(f"Warning: Failed to send verification email: {e}")
                # Continue anyway, user can request resend

        return {
            "status": "success",
            "message": "User signed up successfully. Check your email for verification code."
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error during sign-up: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during sign-up"
        )


@router.post("/confirm-sign-up")
async def confirm_sign_up(confirm_request: modelType.ConfirmUserRequest):
    """Confirm user email with verification code"""
    try:
        # Find user
        user = mongo_utils.find_user_by_email(confirm_request.email)
        if not user:
            raise HTTPException(
                status_code=400,
                detail="User not found"
            )

        # Check if already confirmed
        if user.get('is_confirmed'):
            raise HTTPException(
                status_code=400,
                detail="User already confirmed. Please log in."
            )

        # Verify code
        if user.get('verification_code') != confirm_request.confirmation_code:
            raise HTTPException(
                status_code=400,
                detail="Invalid verification code"
            )

        # Check if code expired
        if datetime.utcnow() > user.get('verification_code_expires_at', datetime.utcnow()):
            raise HTTPException(
                status_code=400,
                detail="Verification code has expired"
            )

        # Mark user as confirmed
        mongo_utils.mark_user_confirmed(confirm_request.email)

        # Send welcome email
        if email_service:
            try:
                email_service.send_welcome_email(to_email=confirm_request.email)
            except Exception as e:
                print(f"Warning: Failed to send welcome email: {e}")

        return {
            "status": "success",
            "message": "Email verified successfully. You can now log in."
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error during email confirmation: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during email confirmation"
        )


@router.post("/resend-verification")
async def resend_verification(request: modelType.ResendVerificationRequest):
    """Resend verification code to user email"""
    try:
        # Find user
        user = mongo_utils.find_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=400,
                detail="User not found"
            )

        # Check if already confirmed
        if user.get('is_confirmed'):
            raise HTTPException(
                status_code=400,
                detail="User is already confirmed"
            )

        # Generate new verification code
        new_verification_code = auth_controller.generate_verification_code()

        # Update verification code in database
        mongo_utils.UsersCollection.update_one(
            {"email": request.email},
            {
                "$set": {
                    "verification_code": new_verification_code,
                    "verification_code_expires_at": auth_controller.get_verification_expiry()
                }
            }
        )

        # Send verification email
        if email_service:
            email_service.send_verification_email(
                to_email=request.email,
                verification_code=new_verification_code
            )

        return {
            "status": "success",
            "message": "Verification code resent to your email"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error during resend verification: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while resending verification"
        )


@router.post("/login")
async def login(login_request: modelType.LoginRequest):
    """Login user with email and password"""
    try:
        # Find user
        user = mongo_utils.find_user_by_email(login_request.email)
        if not user:
            raise HTTPException(
                status_code=400,
                detail="Invalid email or password"
            )

        # Check if email confirmed
        if not user.get('is_confirmed'):
            raise HTTPException(
                status_code=400,
                detail="Please confirm your email first"
            )

        # Verify password
        if not auth_controller.verify_password(login_request.password, user['password_hash']):
            raise HTTPException(
                status_code=400,
                detail="Invalid email or password"
            )

        # Generate tokens
        user_id = str(user['_id'])
        access_token = auth_controller.create_access_token(user_id, login_request.email)
        refresh_token = auth_controller.create_refresh_token(user_id, login_request.email)

        # Update last login
        mongo_utils.update_last_login(login_request.email)

        return {
            "status": True,
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "login_id": user_id
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error during login: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during login"
        )


@router.post("/refresh")
async def refresh_token(request: modelType.RefreshTokenRequest):
    """Refresh access token using refresh token"""
    try:
        # Verify refresh token
        payload = auth_controller.verify_token(request.refresh_token, token_type="refresh")
        if not payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired refresh token"
            )

        # Generate new access token
        new_access_token = auth_controller.create_access_token(
            payload['sub'],
            payload['email']
        )

        return {
            "status": "success",
            "access_token": new_access_token,
            "token_type": "bearer"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error during token refresh: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during token refresh"
        )


@router.post("/password-reset/initiate")
async def initiate_password_reset(request: modelType.InitiatePasswordResetRequest):
    """Initiate password reset process"""
    try:
        # Find user
        user = mongo_utils.find_user_by_email(request.email)
        if not user:
            # Don't reveal if user exists or not (security best practice)
            return {
                "status": "success",
                "message": "If this email exists, you will receive a password reset code"
            }

        # Generate reset code
        reset_code = auth_controller.generate_verification_code()

        # Save reset code
        mongo_utils.save_password_reset_code(request.email, reset_code)

        # Send reset email
        if email_service:
            try:
                email_service.send_password_reset_email(
                    to_email=request.email,
                    reset_code=reset_code
                )
            except Exception as e:
                print(f"Warning: Failed to send reset email: {e}")

        return {
            "status": "success",
            "message": "If this email exists, you will receive a password reset code"
        }

    except Exception as e:
        print(f"Error during password reset initiation: {e}")
        # Return generic message for security
        return {
            "status": "success",
            "message": "If this email exists, you will receive a password reset code"
        }


@router.post("/password-reset/confirm")
async def confirm_password_reset(request: modelType.ConfirmPasswordResetRequest):
    """Confirm password reset with code and new password"""
    try:
        # Find user
        user = mongo_utils.find_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=400,
                detail="User not found"
            )

        # Verify reset code
        if user.get('reset_code') != request.confirmation_code:
            raise HTTPException(
                status_code=400,
                detail="Invalid reset code"
            )

        # Check if code expired
        if datetime.utcnow() > user.get('reset_code_expires_at', datetime.utcnow()):
            raise HTTPException(
                status_code=400,
                detail="Reset code has expired"
            )

        # Hash new password
        new_password_hash = auth_controller.hash_password(request.new_password)

        # Update password
        mongo_utils.update_user_password(request.email, new_password_hash)

        # Clear reset code
        mongo_utils.clear_password_reset_code(request.email)

        # Send confirmation email
        if email_service:
            try:
                email_service.send_password_reset_confirmation_email(to_email=request.email)
            except Exception as e:
                print(f"Warning: Failed to send confirmation email: {e}")

        return {
            "status": "success",
            "message": "Password reset successfully. You can now log in with your new password."
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error during password reset confirmation: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during password reset"
        )


@router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user information from access token"""
    try:
        token = credentials.credentials

        # Verify token
        payload = auth_controller.verify_token(token, token_type="access")
        if not payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )

        # Get user from database
        user = mongo_utils.find_user_by_email(payload['email'])
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return {
            "status": "success",
            "user": {
                "id": str(user['_id']),
                "email": user['email'],
                "is_confirmed": user.get('is_confirmed', False),
                "created_at": user.get('created_at'),
                "last_login": user.get('last_login')
            }
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while fetching user information"
        )
