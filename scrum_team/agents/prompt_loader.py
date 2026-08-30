from functools import lru_cache
from pathlib import Path

PROMPT_FILES = {
    "PROMPT_AGENT": "prompt_agent.md",
    "PO": "product_owner.md",
    "SCRUM_MASTER": "scrum_master.md",
    "DEVELOPER": "developer.md",
    "QA_ENGINEER": "qa_engineer.md",
    "REVIEWER": "reviewer.md",
}


@lru_cache(maxsize=None)
def load_prompt(role: str) -> str:
    try:
        filename = PROMPT_FILES[role]
    except KeyError as exc:
        raise KeyError(f"Unknown agent role: {role}") from exc
    return (Path(__file__).parent / "prompts" / filename).read_text(encoding="utf-8").strip()
