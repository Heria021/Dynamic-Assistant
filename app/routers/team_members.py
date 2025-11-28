"""
Team Members Management Router
Owner can create, manage, and assign bots to team members
"""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from app.middleware.auth_middleware import get_current_user
from app.controllers.auth_controller import AuthController
from app.services.email_service import EmailService
import app.utils.mongo_utils as mongo_utils
import app.models.schemas as schemas
from datetime import datetime

router = APIRouter(prefix="/api/owner/team-members", tags=["Team Members"])

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


@router.post("/invite", response_model=schemas.InviteTeamMemberResponse)
async def invite_team_member(
    request: schemas.CreateTeamMemberRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Owner invites a new team member.
    Generates magic link for passwordless setup.
    """
    try:
        # Only owners can create team members
        if current_user.get("is_team_member"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can invite team members"
            )
        
        owner_id = current_user["sub"]
        
        # Check if member with this email already exists
        existing_member = mongo_utils.find_team_member_by_email(request.email)
        if existing_member and existing_member.get("owner_id") == owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team member with this email already exists"
            )
        
        # Generate unique member ID and magic link token
        member_id = str(uuid.uuid4())
        magic_link_token = auth_controller.generate_magic_link_token()
        expires_at = auth_controller.generate_magic_link_expires_at(hours=48)
        
        # Create login credentials with magic link
        login_credentials = {
            "type": "magic_link",
            "magic_link": {
                "token": magic_link_token,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat(),
                "used_at": None,
                "is_used": False
            }
        }
        
        # Create team member in database
        mongo_utils.create_team_member(
            owner_id=owner_id,
            member_id=member_id,
            email=request.email,
            name=request.name,
            role=request.role,
            login_credentials=login_credentials,
            assigned_bots=request.assigned_bots
        )
        
        # Send invitation email with magic link
        if email_service:
            try:
                magic_link_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/setup-password?token={magic_link_token}"
                email_service.send_team_member_invite_email(
                    to_email=request.email,
                    member_name=request.name,
                    owner_email=current_user["email"],
                    magic_link_url=magic_link_url
                )
            except Exception as e:
                print(f"Warning: Failed to send invitation email: {e}")
                # Continue anyway, token is stored in DB
        
        return schemas.InviteTeamMemberResponse(
            member_id=member_id,
            email=request.email,
            name=request.name,
            invite_sent=True,
            magic_link_token=magic_link_token,
            message="Team member invited successfully. Check email for setup link."
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error inviting team member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invite team member: {str(e)}"
        )


@router.get("/", response_model=list[schemas.TeamMemberResponse])
async def list_team_members(
    current_user: dict = Depends(get_current_user)
):
    """
    Get all team members for the owner.
    Only owners can view their team members.
    """
    try:
        if current_user.get("is_team_member"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can list team members"
            )
        
        owner_id = current_user["sub"]
        team_members = mongo_utils.find_team_members_by_owner(owner_id)
        
        response = []
        for member in team_members:
            response.append(schemas.TeamMemberResponse(
                member_id=member["member_id"],
                email=member["email"],
                name=member["name"],
                role=member["role"],
                assigned_bots=member.get("assigned_bots", []),
                is_active=member.get("is_active", True),
                created_at=member.get("created_at"),
                confirmed_at=member.get("confirmed_at")
            ))
        
        return response
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error listing team members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team members"
        )


@router.get("/{member_id}", response_model=schemas.TeamMemberResponse)
async def get_team_member(
    member_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get details of a specific team member.
    """
    try:
        if current_user.get("is_team_member"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can view team member details"
            )
        
        owner_id = current_user["sub"]
        member = mongo_utils.find_team_member_by_id(member_id)
        
        if not member or member.get("owner_id") != owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )
        
        return schemas.TeamMemberResponse(
            member_id=member["member_id"],
            email=member["email"],
            name=member["name"],
            role=member["role"],
            assigned_bots=member.get("assigned_bots", []),
            is_active=member.get("is_active", True),
            created_at=member.get("created_at"),
            confirmed_at=member.get("confirmed_at")
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error retrieving team member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team member"
        )


@router.patch("/{member_id}", response_model=schemas.TeamMemberResponse)
async def update_team_member(
    member_id: str,
    request: schemas.UpdateTeamMemberRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update team member details.
    Owner can update role, assigned bots, and activation status.
    """
    try:
        if current_user.get("is_team_member"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can update team members"
            )
        
        owner_id = current_user["sub"]
        member = mongo_utils.find_team_member_by_id(member_id)
        
        if not member or member.get("owner_id") != owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )
        
        # Build update data
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.role is not None:
            update_data["role"] = request.role
        if request.assigned_bots is not None:
            update_data["assigned_bots"] = request.assigned_bots
        if request.is_active is not None:
            update_data["is_active"] = request.is_active
        
        if update_data:
            mongo_utils.update_team_member(member_id, update_data)
        
        # Fetch updated member
        updated_member = mongo_utils.find_team_member_by_id(member_id)
        
        return schemas.TeamMemberResponse(
            member_id=updated_member["member_id"],
            email=updated_member["email"],
            name=updated_member["name"],
            role=updated_member["role"],
            assigned_bots=updated_member.get("assigned_bots", []),
            is_active=updated_member.get("is_active", True),
            created_at=updated_member.get("created_at"),
            confirmed_at=updated_member.get("confirmed_at")
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error updating team member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update team member"
        )


@router.delete("/{member_id}")
async def delete_team_member(
    member_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete (deactivate) a team member.
    """
    try:
        if current_user.get("is_team_member"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can delete team members"
            )
        
        owner_id = current_user["sub"]
        member = mongo_utils.find_team_member_by_id(member_id)
        
        if not member or member.get("owner_id") != owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )
        
        mongo_utils.delete_team_member(member_id)
        
        return {
            "status": True,
            "message": "Team member deleted successfully"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error deleting team member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete team member"
        )


@router.post("/{member_id}/resend-invite")
async def resend_invite(
    member_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Resend invitation email to team member.
    Generates new magic link token.
    """
    try:
        if current_user.get("is_team_member"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can resend invites"
            )
        
        owner_id = current_user["sub"]
        member = mongo_utils.find_team_member_by_id(member_id)
        
        if not member or member.get("owner_id") != owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )
        
        # Generate new magic link token
        new_token = auth_controller.generate_magic_link_token()
        expires_at = auth_controller.generate_magic_link_expires_at(hours=48)
        
        new_credentials = {
            "type": "magic_link",
            "magic_link": {
                "token": new_token,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat(),
                "used_at": None,
                "is_used": False
            }
        }
        
        mongo_utils.update_team_member_login_credentials(member_id, new_credentials)
        
        # Send email
        if email_service:
            try:
                magic_link_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/setup-password?token={new_token}"
                email_service.send_team_member_invite_email(
                    to_email=member["email"],
                    member_name=member["name"],
                    owner_email=current_user["email"],
                    magic_link_url=magic_link_url
                )
            except Exception as e:
                print(f"Warning: Failed to send invitation email: {e}")
        
        return {
            "status": True,
            "message": "Invitation resent successfully",
            "token": new_token
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error resending invite: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend invite"
        )
