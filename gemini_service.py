"""
gemini_service.py - Centralized Google GenAI (Gemini) Service for LedgerLens AI.
Handles client configuration, connection testing, error sanitization,
model availability verification, insights generation, and interactive chat assistance.
"""

from pathlib import Path
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv, set_key
from google import genai
from google.genai import errors, types

# Root-level .env path configuration
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

# Deprecated model mapping to modern, active models
DEPRECATED_MODEL_MAP = {
    "gemini-2.0-flash": "gemini-3.8-flash",
    "gemini-1.5-flash": "gemini-3.8-flash",
    "gemini-1.5-pro": "gemini-3.8-flash",
    "gemini-2.5-flash": "gemini-3.8-flash",
    "gemini-2.5-pro": "gemini-3.8-flash",
}

# Supported and verified Gemini models available in Google GenAI
SUPPORTED_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
]
DEFAULT_MODEL = "gemini-3.5-flash"
FALLBACK_MODEL = "gemini-3.5-flash"


def reload_environment() -> None:
    """Reload environment variables from root .env."""
    load_dotenv(dotenv_path=ENV_PATH, override=True)


def get_api_key() -> Optional[str]:
    """Retrieve the Gemini API key securely from environment variables or Streamlit secrets."""
    reload_environment()
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        # Check Streamlit Cloud secrets when deployed
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                key = st.secrets["GEMINI_API_KEY"]
        except Exception:
            pass

    if key:
        cleaned = str(key).strip().strip("'\"")
        return cleaned if cleaned else None
    return None


def get_selected_model() -> str:
    """Retrieve the configured model name or default, automatically upgrading deprecated models."""
    reload_environment()
    raw_model = os.getenv("GEMINI_MODEL")
    if not raw_model:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "GEMINI_MODEL" in st.secrets:
                raw_model = st.secrets["GEMINI_MODEL"]
        except Exception:
            pass

    raw_model = (raw_model or DEFAULT_MODEL).strip()
    if raw_model in DEPRECATED_MODEL_MAP:
        return DEPRECATED_MODEL_MAP[raw_model]
    if raw_model in SUPPORTED_MODELS:
        return raw_model
    return DEFAULT_MODEL


def mask_key(key: Optional[str]) -> str:
    """Return a masked representation of the API key without revealing secrets."""
    if not key:
        return "Not configured"
    cleaned = key.strip()
    if len(cleaned) <= 8:
        return "••••••••"
    return f"{cleaned[:4]}••••••••{cleaned[-4:]}"


def sanitize_error_message(error: Exception, api_key: Optional[str] = None) -> str:
    """Remove sensitive API key details from error messages."""
    msg = str(error)
    if api_key and api_key in msg:
        msg = msg.replace(api_key, "[REDACTED_API_KEY]")
    # Also redact potential key patterns (Google AI Studio and Cloud format)
    msg = re.sub(r"(AIza[0-9A-Za-z-_]{35})", "[REDACTED_API_KEY]", msg)
    msg = re.sub(r"(AQ\.[0-9A-Za-z-_]{30,})", "[REDACTED_API_KEY]", msg)
    return msg


def get_gemini_client(
    api_key: Optional[str] = None, timeout_seconds: float = 15.0
) -> genai.Client:
    """
    Instantiate and return the official google-genai Client with request timeout configuration.
    Raises ValueError if API key is missing.
    """
    active_key = api_key or get_api_key()
    if not active_key:
        raise ValueError(
            "Gemini API key is not configured. Please add GEMINI_API_KEY to your .env file or update it in Settings."
        )
    return genai.Client(
        api_key=active_key,
        http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
    )


def classify_gemini_error(
    exc: Exception,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """
    Transform raw SDK and HTTP exceptions into clear, actionable user messages
    handling specific HTTP error codes (400, 401, 403, 404, 429, 500, 503, 504)
    and network timeout/connection errors separately.
    Never exposes API keys.
    """
    target_key = api_key or get_api_key()
    target_model = model or get_selected_model()
    clean_msg = sanitize_error_message(exc, target_key)
    exc_type = type(exc).__name__

    # 401 / 403: Authentication or permission issue
    if (
        "UNAUTHENTICATED" in clean_msg
        or "401" in clean_msg
        or "ACCESS_TOKEN_TYPE_UNSUPPORTED" in clean_msg
        or "API key not valid" in clean_msg
    ):
        return (
            "Authentication failed (401): Invalid or unrecognized Gemini API key. "
            "Please verify GEMINI_API_KEY in your .env file or obtain a fresh key from "
            "https://aistudio.google.com/app/apikey"
        )
    elif "PERMISSION_DENIED" in clean_msg or "403" in clean_msg:
        return (
            "Permission denied (403): Your Gemini API key does not have permission to access "
            f"model '{target_model}'. Check API project permissions in Google AI Studio / Google Cloud."
        )

    # 400: Invalid request
    elif "INVALID_ARGUMENT" in clean_msg or "400" in clean_msg:
        return (
            "Invalid request (400): The prompt or request parameters were rejected by Google Gemini. "
            "Please verify the input format."
        )

    # 404: Model or endpoint unavailable
    elif "NOT_FOUND" in clean_msg or "404" in clean_msg:
        return (
            f"Model '{target_model}' was not found or is discontinued by Google (404). "
            f"Please switch to '{FALLBACK_MODEL}' or 'gemini-3.8-flash' in the Settings page."
        )

    # 429: API quota or rate limit exceeded
    elif "RESOURCE_EXHAUSTED" in clean_msg or "429" in clean_msg or "quota" in clean_msg.lower():
        return (
            "API rate limit or quota exceeded (429): The request limit for this model has been reached. "
            "Please wait a few moments before retrying or verify your quota limits in Google AI Studio."
        )

    # 500 / 503 / 504: Gemini server error
    elif (
        "500" in clean_msg
        or "503" in clean_msg
        or "504" in clean_msg
        or "UNAVAILABLE" in clean_msg
        or "DEADLINE_EXCEEDED" in clean_msg
        or "high demand" in clean_msg.lower()
    ):
        return (
            f"Gemini server error ({'504' if '504' in clean_msg else '503'}): Google's model servers are experiencing "
            f"temporary high demand or deadline timeouts for '{target_model}'. "
            f"The system will automatically try fallback model '{FALLBACK_MODEL}'."
        )

    # Network timeout and connection failures
    elif (
        "ConnectError" in exc_type
        or "NameResolutionError" in clean_msg
        or "nodename" in clean_msg
        or "APIConnectionError" in exc_type
    ):
        return (
            "Network connection failed: Unable to reach Google Gemini API servers. "
            "Please check your internet connection or proxy settings."
        )
    elif "Timeout" in exc_type or "TimeoutError" in exc_type:
        return (
            f"Connection timed out while waiting for Google Gemini API response ({target_model})."
        )

    return f"Gemini API request failed: {clean_msg}"


def verify_model_availability(
    model_name: str,
    client: Optional[genai.Client] = None,
    timeout_seconds: float = 8.0,
) -> Tuple[bool, str]:
    """
    Verify if a specific Gemini model is currently available and responding to the configured API key.
    Returns (is_available, diagnostic_message).
    """
    resolved_model = DEPRECATED_MODEL_MAP.get(model_name, model_name)
    try:
        active_client = client or get_gemini_client(timeout_seconds=timeout_seconds)
        response = active_client.models.generate_content(
            model=resolved_model,
            contents="Respond with only: OK",
        )
        if response and response.text:
            return True, f"Model '{resolved_model}' is active and operational."
        return False, f"Model '{resolved_model}' returned an empty test response."
    except Exception as exc:
        clean = classify_gemini_error(exc, model=resolved_model)
        return False, clean


def test_gemini_connection(
    api_key: Optional[str] = None, model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Performs a live test of the Gemini API with detailed diagnostic reporting.
    Never exposes raw API keys.
    """
    target_key = api_key or get_api_key()
    raw_model = model or get_selected_model()
    target_model = DEPRECATED_MODEL_MAP.get(raw_model, raw_model)

    if not target_key:
        return {
            "success": False,
            "status": "Missing API Key",
            "message": "No API key found. Please configure GEMINI_API_KEY in .env or Settings.",
            "model": target_model,
            "latency_ms": 0,
        }

    start_time = time.time()
    try:
        client = get_gemini_client(api_key=target_key, timeout_seconds=12.0)
        response = client.models.generate_content(
            model=target_model,
            contents="Respond with only the single word: OK",
        )
        latency = int((time.time() - start_time) * 1000)

        if response and response.text:
            return {
                "success": True,
                "status": "Connected",
                "message": f"Successfully connected to Google Gemini API using model '{target_model}'.",
                "model": target_model,
                "latency_ms": latency,
                "response_sample": response.text.strip(),
            }
        else:
            return {
                "success": False,
                "status": "Empty Response",
                "message": f"Connected to Google GenAI, but '{target_model}' returned an empty response.",
                "model": target_model,
                "latency_ms": latency,
            }

    except Exception as exc:
        latency = int((time.time() - start_time) * 1000)
        clean_msg = sanitize_error_message(exc, target_key)
        human_msg = classify_gemini_error(exc, target_key, target_model)
        status_name = (
            "Authentication Error"
            if "401" in clean_msg or "UNAUTHENTICATED" in clean_msg
            else "Server/Quota Error"
            if "503" in clean_msg or "504" in clean_msg or "429" in clean_msg
            else "API Error"
        )

        return {
            "success": False,
            "status": status_name,
            "message": human_msg,
            "model": target_model,
            "latency_ms": latency,
            "raw_error": clean_msg,
        }


def save_api_credentials(api_key: str, model: Optional[str] = None) -> bool:
    """Save updated API key and optional model choice to root .env securely."""
    try:
        if not ENV_PATH.exists():
            with open(ENV_PATH, "w") as f:
                f.write("# LedgerLens AI Environment Configuration\n")

        cleaned_key = api_key.strip().strip("'\"")
        set_key(str(ENV_PATH), "GEMINI_API_KEY", cleaned_key)
        if model and (model in SUPPORTED_MODELS or model in DEPRECATED_MODEL_MAP):
            final_model = DEPRECATED_MODEL_MAP.get(model, model)
            set_key(str(ENV_PATH), "GEMINI_MODEL", final_model)
        reload_environment()
        return True
    except Exception as exc:
        logger_msg = sanitize_error_message(exc, api_key)
        print(f"Failed to update .env: {logger_msg}")
        return False


def _execute_gemini_prompt(prompt: str, preferred_model: Optional[str] = None) -> str:
    """
    Executes a prompt against Gemini with intelligent model fallback:
    Tries the configured model first, and if unavailable/failing with server/quota issues,
    falls back to healthy candidate models.
    """
    client = get_gemini_client()
    selected_model = preferred_model or get_selected_model()
    target_model = DEPRECATED_MODEL_MAP.get(selected_model, selected_model)

    # Build candidates: target model first, followed by available fallbacks
    candidate_models = [target_model]
    for alt in [FALLBACK_MODEL, "gemini-3.5-flash-lite", "gemini-3.8-flash"]:
        if alt not in candidate_models:
            candidate_models.append(alt)

    last_exc = None
    for model in candidate_models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            if response and response.text:
                return response.text
        except Exception as exc:
            last_exc = exc
            clean_err = sanitize_error_message(exc, get_api_key())
            # Fall back on 404 (model retired/missing), 503/504 (demand/deadline), 429, or network timeout
            if (
                "404" in clean_err
                or "503" in clean_err
                or "504" in clean_err
                or "NOT_FOUND" in clean_err
                or "UNAVAILABLE" in clean_err
                or "DEADLINE_EXCEEDED" in clean_err
                or "RESOURCE_EXHAUSTED" in clean_err
                or "Timeout" in type(exc).__name__
                or "timeout" in clean_err.lower()
            ):
                continue
            # Break immediately on client/auth errors (e.g. 400 or 401)
            break

    if last_exc:
        human_readable_error = classify_gemini_error(last_exc, get_api_key(), target_model)
        raise RuntimeError(human_readable_error) from last_exc
    raise ValueError("Gemini returned an empty response.")


def generate_ai_insights(financial_context: str) -> str:
    """
    Generate professional, grounded financial insights based strictly on actual database records.
    Never invents facts or hallucinates transactions.
    """
    system_instruction = (
        "You are LedgerLens AI's senior financial analyst. "
        "Analyze the provided financial data with rigor, precision, and clarity. "
        "Strict rules:\n"
        "1. Never invent or assume numbers, transactions, dates, or counterparties not present in the data.\n"
        "2. If data is limited or zero, clearly acknowledge the data size without fabricating trends.\n"
        "3. All calculations must match the provided numbers exactly.\n"
        "4. Net Balance is defined as Total Income minus Total Expenses.\n"
        "5. Format your output with clear markdown headings, bullet points, and key takeaways.\n"
        "6. Provide 3 specific sections: Executive Summary, Category & Spending Observations, and Strategic Recommendations."
    )

    prompt = f"""{system_instruction}

Financial Records for Selected Period:
{financial_context}

Please provide your financial analysis:"""

    return _execute_gemini_prompt(prompt)


def chat_with_financial_assistant(
    user_query: str,
    conversation_history: List[Dict[str, str]],
    financial_context: str,
) -> str:
    """
    Process interactive Q&A grounded strictly in the user's ledger data.
    """
    recent_history = conversation_history[-6:] if conversation_history else []
    history_lines = []
    for turn in recent_history:
        role = "User" if turn.get("role") == "user" else "Assistant"
        content = turn.get("content", "")
        history_lines.append(f"{role}: {content}")
    history_str = "\n".join(history_lines) if history_lines else "No previous conversation."

    prompt = f"""You are LedgerLens AI, an intelligent, professional financial assistant.
You help users understand their financial ledger, spending patterns, income, and cash flow.

Rules:
- Strictly base all factual answers on the provided financial records.
- Do not fabricate numbers, dates, or transactions.
- If data is missing or insufficient to answer the question, politely explain what data is available and what is missing.
- Net balance is defined as Total Income minus Total Expenses.
- Use currency formatting (₹) matching the records.
- Keep answers concise, helpful, and professional.

Ledger Data for Current Filter:
{financial_context}

Recent Chat Context:
{history_str}

User Question:
{user_query}

Your Response:"""

    return _execute_gemini_prompt(prompt)
