import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "connections": {
        "omniroute": {
            "provider": "omniroute",
            "url": "http://localhost:8080/v1",
            "api_key": "",
        }
    },
    "model_mapping": {
        "PO": {"connection": "omniroute", "model": "best-reasoning"},
        "QA": {"connection": "omniroute", "model": "best-reasoning"},
        "DEVELOPER": {"connection": "omniroute", "model": "best-coding"},
        "SCRUM_MASTER": {"connection": "omniroute", "model": "chat"},
        "REVIEWER": {"connection": "omniroute", "model": "chat"},
    },
}


def normalize_config(data):
    """Normalize current and legacy config into the connection registry shape."""
    if not isinstance(data, dict):
        return DEFAULT_CONFIG.copy()
    if "connections" not in data:
        legacy = data.get("omniroute", {})
        data = {"connections": {"omniroute": {
            "provider": "omniroute",
            "url": legacy.get("url", "http://localhost:8080/v1"),
            "api_key": legacy.get("api_key", ""),
        }}, "model_mapping": data.get("model_mapping", {})}
    connections = data.get("connections", {})
    normalized_mapping = {}
    for role, value in data.get("model_mapping", {}).items():
        if isinstance(value, str):
            value = {"connection": "omniroute", "model": value}
        normalized_mapping[role] = value
    result = {"connections": connections, "model_mapping": normalized_mapping}
    return result


def config_path():
    return Path(__file__).parent / "config.yaml"

def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        logger.warning(f"Config file not found at {config_path}. Using defaults.")
        return DEFAULT_CONFIG
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return normalize_config(data)
    except Exception as e:
        logger.error(f"Error reading config.yaml: {e}. Falling back to defaults.")
        return DEFAULT_CONFIG

config = load_config()
