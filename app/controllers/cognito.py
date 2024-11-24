import hmac
import hashlib
import base64
import boto3
import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import app.utils.mongo_utils as mongod


COGNITO_USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID')
COGNITO_CLIENT_ID = str(os.getenv('COGNITO_CLIENT_ID'))
COGNITO_CLIENT_SECRET = os.getenv('COGNITO_CLIENT_SECRET')
COGNITO_REGION = os.getenv('COGNITO_REGION')
cognito_client = boto3.client('cognito-idp', region_name=COGNITO_REGION)
security = HTTPBearer()

# def extract_sub_from_token(token: str) -> str:
#     decoded_token = jwt.decode(token, options={"verify_signature": False})
#     return decoded_token.get('sub')

def extract_sub_from_token(token):
    decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256"])
    return decoded_token['sub']

def get_secret_hash(email: str) -> str:
    message = email + COGNITO_CLIENT_ID
    dig = hmac.new(COGNITO_CLIENT_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(dig).decode()

def authenticate_user(email: str, password: str):
    try:
        secret_hash = get_secret_hash(email)
        response = cognito_client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password,
                'SECRET_HASH': secret_hash
            },
        )
        return response['AuthenticationResult']

    except cognito_client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    except cognito_client.exceptions.UserNotConfirmedException:
        raise HTTPException(status_code=400, detail="User is not confirmed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

async def initiate_password_reset(email: str):
    try:
        response = cognito_client.forgot_password(
            ClientId=COGNITO_CLIENT_ID,
            Username=email,
            SecretHash=get_secret_hash(email)
        )
        return {
            "status": "success",
            "message": "Password reset initiated. Please check your email for the verification code.",
            "data": response
        }

    except cognito_client.exceptions.UserNotFoundException:
        raise HTTPException(
            status_code=400,detail="User with the provided email does not exist.")

    except cognito_client.exceptions.InvalidParameterException as e:
        raise HTTPException(
            status_code=400,detail=f"Invalid parameters: {str(e)}")

    except cognito_client.exceptions.LimitExceededException:
        raise HTTPException(
            status_code=429,detail="Attempt limit exceeded, please try again later.")

    except Exception as e:
        raise HTTPException(
            status_code=500,detail=f"An unexpected error occurred during password reset initiation: {str(e)}")


async def confirm_password_reset(email: str, confirmation_code: str, new_password: str):
    try:
        response = cognito_client.confirm_forgot_password(
            ClientId=COGNITO_CLIENT_ID,
            Username=email,
            ConfirmationCode=confirmation_code,
            Password=new_password,
            SecretHash=get_secret_hash(email)
        )
        return {
            "status": "success",
            "message": "Password has been reset successfully.",
            "data": response
        }

    except cognito_client.exceptions.CodeMismatchException:
        raise HTTPException(status_code=400,detail="Invalid confirmation code.")

    except cognito_client.exceptions.ExpiredCodeException:
        raise HTTPException(status_code=400,detail="Confirmation code has expired. Please request a new code.")

    except cognito_client.exceptions.UserNotFoundException:
        raise HTTPException(status_code=400,detail="User with the provided email does not exist.")

    except Exception as e:
        raise HTTPException(
            status_code=500,detail=f"An unexpected error occurred during password reset confirmation: {str(e)}")

async def sign_up_user(email: str, password: str):
    secret_hash = get_secret_hash(email)
    # Check if user already exists in MongoDB
    existing_user = mongod.find_user_by_email(email)
    if existing_user:
        if not existing_user["is_confirmed"]:
            # Resend confirmation code if user is not confirmed
            cognito_client.resend_confirmation_code(
                ClientId=COGNITO_CLIENT_ID,
                SecretHash=secret_hash,
                Username=email
            )
            raise HTTPException(
                status_code=400,
                detail="User already exists but is not confirmed. Confirmation code has been resent. Please confirm your email."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="User already exists and is confirmed. Please login."
            )
    try:
        response = cognito_client.sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[{"Name": "email", "Value": email}],
            SecretHash=secret_hash
        )
        
        # Save user info after successful sign-up
        mongod.insert_new_user(email=email, sub_id=response['UserSub'], is_confirmed=False)
        
        return {"message": "User signed up successfully. Please check your email for the confirmation code."}

    except Exception as e:
        print(f"Error {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred during sign-up: {str(e)}")

def confirm_user(email: str, confirmation_code: str):
    try:
        cognito_client.confirm_sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=email,
            ConfirmationCode=confirmation_code,
            SecretHash=get_secret_hash(email)
        )
        
        # Update the user's confirmation status
        mongod.save_user_info(email=email, sub_id=None, is_confirmed=True)
        
    except cognito_client.exceptions.UserNotFoundException:
        raise HTTPException(status_code=400, detail="User not found")
    except cognito_client.exceptions.CodeMismatchException:
        raise HTTPException(status_code=400, detail="Invalid confirmation code")
    except cognito_client.exceptions.ExpiredCodeException:
        raise HTTPException(status_code=400, detail="Confirmation code expired")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


def resend_confirmation_code(email: str):
    try:
        cognito_client.resend_confirmation_code(
            ClientId=COGNITO_CLIENT_ID,
            SecretHash=get_secret_hash(email),
            Username=email
        )
        return {"status": "success", "message": "Confirmation code resent successfully"}
    except cognito_client.exceptions.UserNotFoundException:
        raise HTTPException(status_code=400, detail="User not found")
    except cognito_client.exceptions.InvalidParameterException as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        # Get user information from Cognito using the AccessToken
        response = cognito_client.get_user(AccessToken=token)
        # Decode the token to extract the `sub` (login_id)
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        login_id = decoded_token.get('sub')
        # Add the `login_id` to the response dictionary
        response['login_id'] = login_id
        
        return response
    except cognito_client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

async def get_api_token(ast_id,api_token):
    Ast_Id = await mongod.get_astId_by_apiToken(api_token)
    if ast_id == Ast_Id:
        return("Success")
    else:
        return("Failure")
    

    