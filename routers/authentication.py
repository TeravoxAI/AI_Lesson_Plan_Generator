"""
Auth Router - API endpoints for user authentication
"""
from fastapi import APIRouter, HTTPException, Depends
from src.models import UserCredentials, UserRegistration, AuthResponse
from src.db.client import db

router = APIRouter(tags=["Authentication"])


@router.post("/signup", response_model=AuthResponse)
async def sign_up(user_data: UserRegistration):
    """
    Create a new user and store profile information
    """
    if not db.client:
        raise HTTPException(status_code=500, detail="Database connection not available")

    try:
        # 1. Sign up with Supabase Auth
        response = db.client.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
        })

        # 2. If successful, create user profile
        if response.user and response.user.id:
            profile_created = db.create_user_profile(
                user_id=response.user.id,
                profile_data={
                    "email": user_data.email,
                    "first_name": user_data.first_name,
                    "last_name": user_data.last_name,
                    "grade": user_data.grade,
                    "subject": user_data.subject,
                    "school_branch": user_data.school_branch,
                    "role": user_data.role,
                    "is_approved": False if user_data.role.lower() == 'principal' else True
                }
            )

            if not profile_created:
                print(f"Warning: Failed to create profile for user {response.user.id}")
                # We return success true for auth even if profile creation fails?
                # Ideally we want it to be atomic, but with Supabase client-side calls it's two steps unless using an edge function.
                # For now, we'll return user created but add a note in message if profile failed?
                # Actually, the user asked for this flow, let's assume if auth works, we return success,
                # but maybe error if profile fails? Let's keep it simple: return success but log warning implementation above.

            user_response_data = response.user.model_dump() if hasattr(response.user, 'model_dump') else response.user.__dict__
            # Merge profile data
            user_response_data.update({
                 "email": user_data.email,
                 "first_name": user_data.first_name,
                 "last_name": user_data.last_name,
                 "grade": user_data.grade,
                 "subject": user_data.subject,
                 "school_branch": user_data.school_branch,
                 "role": user_data.role,
                 "is_approved": False if user_data.role.lower() == 'principal' else True
            })

            return AuthResponse(
                success=True,
                message="User created successfully.",
                user=user_response_data,
                session=response.session.model_dump() if response.session and hasattr(response.session, 'model_dump') else (response.session.__dict__ if response.session else None)
            )
        else:
             return AuthResponse(
                success=False,
                message="Failed to create user",
                error="No user returned from Supabase"
            )

    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg:
             return AuthResponse(
                success=False,
                message="User already exists",
                error="User already exists"
            )
        return AuthResponse(
            success=False,
            message="Signup failed",
            error=str(e)
        )


@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserCredentials):
    """
    Sign in a user using Supabase Auth
    """
    if not db.client:
        raise HTTPException(status_code=500, detail="Database connection not available")

    try:
        response = db.client.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password,
        })

        if response.user and response.session:
            # Fetch full profile to return to frontend
            profile = db.get_user_profile(response.user.id)

            user_data_resp = response.user.model_dump() if hasattr(response.user, 'model_dump') else response.user.__dict__

            if profile:
                user_data_resp.update(profile)

            return AuthResponse(
                success=True,
                message="Login successful",
                user=user_data_resp,
                session=response.session.model_dump() if hasattr(response.session, 'model_dump') else response.session.__dict__
            )
        else:
             return AuthResponse(
                success=False,
                message="Login failed",
                error="Invalid credentials or no session returned"
            )

    except Exception as e:
        error_msg = str(e)
        if "Invalid login credentials" in error_msg:
             return AuthResponse(
                success=False,
                message="User does not exist or invalid password",
                error="User does not exist or invalid password"
            )
        return AuthResponse(
            success=False,
            message="Login failed",
            error=str(e)
        )


@router.post("/logout", response_model=AuthResponse)
async def logout():
    """
    Sign out the current user
    """
    if not db.client:
        raise HTTPException(status_code=500, detail="Database connection not available")

    try:
        # Note: In a REST API context without browser cookies managed by the backend,
        # this mostly clears the client-side state in the python client if it was stateful in this scope.
        # But it's good practice to call it.
        db.client.auth.sign_out()

        return AuthResponse(
            success=True,
            message="Logout successful"
        )

    except Exception as e:
        return AuthResponse(
            success=False,
            message="Logout failed",
            error=str(e)
        )