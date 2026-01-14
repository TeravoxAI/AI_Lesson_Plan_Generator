"""
Lesson Plan Generator Configuration
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Model Configuration
LLM_MODEL = "openai/gpt-5.1"  # For OCR and generation

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")

def get_supabase_client() -> Client:
    """Get Supabase client from connection string."""
    # Parse the connection string to get project URL and key
    # The provided URL is a PostgreSQL connection string
    # We need the Supabase REST API URL and anon key
    supabase_project_url = os.getenv("SUPABASE_PROJECT_URL", "")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    
    if supabase_project_url and supabase_anon_key:
        return create_client(supabase_project_url, supabase_anon_key)
    return None
