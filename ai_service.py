"""
ai_service.py - Centralized Gemini service entry point for LedgerLens AI.
Delegates directly to gemini_service.py.
"""

from gemini_service import (
    DEFAULT_MODEL,
    DEPRECATED_MODEL_MAP,
    ENV_PATH,
    FALLBACK_MODEL,
    SUPPORTED_MODELS,
    chat_with_financial_assistant,
    classify_gemini_error,
    generate_ai_insights,
    get_api_key,
    get_gemini_client,
    get_selected_model,
    mask_key,
    reload_environment,
    sanitize_error_message,
    save_api_credentials,
    test_gemini_connection,
    verify_model_availability,
)

__all__ = [
    "DEFAULT_MODEL",
    "DEPRECATED_MODEL_MAP",
    "ENV_PATH",
    "FALLBACK_MODEL",
    "SUPPORTED_MODELS",
    "chat_with_financial_assistant",
    "classify_gemini_error",
    "generate_ai_insights",
    "get_api_key",
    "get_gemini_client",
    "get_selected_model",
    "mask_key",
    "reload_environment",
    "sanitize_error_message",
    "save_api_credentials",
    "test_gemini_connection",
    "verify_model_availability",
]
