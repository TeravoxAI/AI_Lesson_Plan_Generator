import os
import sys

# Add the parent directory (project root) to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Vercel needs a variable named 'app' in the exposed module
# Since main.py already has 'app', we just import it.
# This file serves as the clean entry point for the Vercel Python runtime.
