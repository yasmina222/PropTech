"""
School Research Assistant - Configuration (v2)
"""

import os
from typing import Literal

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


LLM_PROVIDER: Literal["anthropic", "openai"] = "anthropic"

MODELS = {
    "anthropic": {
        "primary": "claude-sonnet-4-20250514",
        "fast": "claude-sonnet-4-20250514",
    },
    "openai": {
        "primary": "gpt-4o-mini",
        "fast": "gpt-4o-mini",
    }
}

def get_model(model_type: str = "primary") -> str:
    return MODELS[LLM_PROVIDER][model_type]


def get_api_keys() -> dict:
    keys = {
        "openai": None,
        "anthropic": None,
        "serper": None,
        "firecrawl": None,
    }
    
    keys["openai"] = os.getenv("OPENAI_API_KEY")
    keys["anthropic"] = os.getenv("ANTHROPIC_API_KEY")
    keys["serper"] = os.getenv("SERPER_API_KEY")
    keys["firecrawl"] = os.getenv("FIRECRAWL_API_KEY")
    
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            try:
                keys["openai"] = st.secrets["OPENAI_API_KEY"]
            except (KeyError, FileNotFoundError):
                pass
            try:
                keys["anthropic"] = st.secrets["ANTHROPIC_API_KEY"]
            except (KeyError, FileNotFoundError):
                pass
            try:
                keys["serper"] = st.secrets["SERPER_API_KEY"]
            except (KeyError, FileNotFoundError):
                pass
            try:
                keys["firecrawl"] = st.secrets["FIRECRAWL_API_KEY"]
            except (KeyError, FileNotFoundError):
                pass
    except Exception:
        pass
    
    return keys


DATA_SOURCE: Literal["csv", "databricks"] = "csv"

CSV_FILE_PATH_FINANCIAL = "data/london_schools_financial_CLEAN.csv"
CSV_FILE_PATH_GIAS = "data/london_schools_gias.csv"
CSV_FILE_PATH_SEND = "data/sen_school_level_ud.csv"
CSV_FILE_PATH = CSV_FILE_PATH_FINANCIAL

DATABRICKS_CONFIG = {
    "host": os.getenv("DATABRICKS_HOST", ""),
    "token": os.getenv("DATABRICKS_TOKEN", ""),
    "warehouse_id": os.getenv("DATABRICKS_WAREHOUSE_ID", ""),
    "catalog": "main",
    "schema": "schools",
    "table": "edco_schools"
}


PRIORITY_THRESHOLDS = {
    "HIGH": 500000,
    "MEDIUM": 200000,
    "LOW": 0,
}

PRIORITY_COST_FIELD = "total_teaching_support_costs"


DISPLAY_LABELS = {
    "la_name": "Local Authority",
    "la_code": "LA Code",
    "urn": "URN",
    "school_name": "School Name",
    "school_type": "School Type",
    "phase": "Phase",
    "pupil_count": "Number of Pupils",
    "headteacher": "Headteacher",
    "trust_name": "Trust Name",
    "postcode": "Postcode",
    "phone": "Phone Number",
    "website": "Website",
    "total_expenditure": "Total Expenditure",
    "teaching_staff_costs": "Teaching Staff Costs",
    "agency_supply_costs": "Agency Supply Costs",
    "total_teaching_support_costs": "Total Staffing Costs",
}

def get_display_label(field_name: str) -> str:
    return DISPLAY_LABELS.get(field_name, field_name.replace("_", " ").title())


ENABLE_CACHE = True
CACHE_TTL_HOURS = 24
CACHE_DIR = "cache"


def get_app_password() -> str:
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            try:
                return st.secrets["APP_PASSWORD"]
            except (KeyError, FileNotFoundError):
                pass
    except Exception:
        pass
    
    return os.getenv("APP_PASSWORD", "SEG2025AI!")


APP_PASSWORD = "SEG2025AI!"

OUTPUT_DIR = "outputs"
LOG_LEVEL = "INFO"


FEATURES = {
    "conversation_starters": True,      
    "financial_analysis": True,        
    "ofsted_analysis": True,
    "send_analysis": True,
    "live_web_search": False,           
    "export_to_excel": True,            
}


MAX_CONVERSATION_STARTERS = 5
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 1500
