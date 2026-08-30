import logging

import httpx
from langchain_openai import ChatOpenAI


def list_models(connection: dict) -> list[str]:
    """Return model IDs from OpenAI-compatible endpoints; hosted providers remain manual."""
    provider = connection.get("provider", "").lower()
    if provider not in {"openai", "omniroute", "local"} or not connection.get("url"):
        return []
    headers = {}
    if connection.get("api_key"):
        headers["Authorization"] = f"Bearer {connection['api_key']}"
    try:
        response = httpx.get(connection["url"].rstrip("/") + "/models", headers=headers, timeout=5)
        response.raise_for_status()
        return sorted(item["id"] for item in response.json().get("data", []) if item.get("id"))
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return []


from langchain_openai import ChatOpenAI

from config.settings import load_config

logger = logging.getLogger(__name__)


def build_llm(connection: dict, model: str):
    provider = connection.get("provider", "openai").lower()
    kwargs = {"model": model, "api_key": connection.get("api_key", ""), "timeout": 60, "max_retries": 2}
    if provider in {"openai", "omniroute", "local"}:
        if connection.get("url"):
            kwargs["base_url"] = connection["url"]
        return ChatOpenAI(**kwargs)
    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise RuntimeError("Install langchain-anthropic to use Anthropic connections") from exc
        return ChatAnthropic(model=model, api_key=connection.get("api_key", ""), timeout=60, max_retries=2)
    if provider == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise RuntimeError("Install langchain-google-genai to use Google connections") from exc
        return ChatGoogleGenerativeAI(model=model, google_api_key=connection.get("api_key", ""), max_retries=2)
    raise ValueError(f"Unsupported provider: {provider}")


def get_llm(role: str):
    cfg = load_config()
    mapping = cfg.get("model_mapping", {})
    assignment = mapping.get(role, mapping.get("SCRUM_MASTER", {}))
    if isinstance(assignment, str):
        assignment = {"connection": "omniroute", "model": assignment}
    name = assignment.get("connection")
    model = assignment.get("model")
    connection = cfg.get("connections", {}).get(name)
    if not connection:
        raise ValueError(f"No connection configured for role {role}: {name}")
    if not model:
        raise ValueError(f"No model configured for role {role}")
    return build_llm(connection, model)
