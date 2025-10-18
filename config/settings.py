"""
Configuration settings for the Algorand AI-Powered Smart Contract Creator application.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Application info
APP_NAME = "Algorand AI-Powered Smart Contract Creator"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "An AI-Powered Smart Contract Creator that generates, explains, and deploys Algorand PyTeal contracts using GPT-4."

# Perplexity API Configuration
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_BASE_URL = os.getenv("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")

# Model configuration
PERPLEXITY_MODELS = {
    
    "web": "sonar-code-v1",   # For web scraping
   }


# Environment and debug settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"