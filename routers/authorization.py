from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.db.client import db
from typing import Dict, Any

router = APIRouter(tags=["Authorization"])
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Verify JWT token and retrieve user profile with role/subject.
    """
    token = credentials.credentials

    if not db.client:
        raise HTTPException(status_code=500, detail="Database connection not available")

    try:
        # Verify token with Supabase Auth
        # This calls the Supabase API to get the user from the JWT
        user_response = db.client.auth.get_user(token)

        if not user_response or not user_response.user:
             raise HTTPException(status_code=401, detail="Invalid authentication token")

        user_id = user_response.user.id

        # Get profile from permissions table (users)
        profile = db.get_user_profile(user_id)

        if not profile:
             # If profile is missing, we can't determine role/subject permissions
             raise HTTPException(status_code=403, detail="User profile not found. Please contact support.")

        return profile

    except Exception as e:
        # Check if it is a specific Supabase error regarding token
        print(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")
