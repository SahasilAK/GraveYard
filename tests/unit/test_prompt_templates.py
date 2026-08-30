from scrum_team.agents.prompt_loader import load_prompt

ROLES = ("PROMPT_AGENT", "PO", "SCRUM_MASTER", "DEVELOPER", "QA_ENGINEER", "REVIEWER")
SECTIONS = ("## Persona", "## Scope", "## Output Format", "## Hard Constraints")


def test_every_role_has_required_sections_and_example():
    for role in ROLES:
        prompt = load_prompt(role)
        assert all(section in prompt for section in SECTIONS)
        assert "Example:" in prompt


def test_loader_rejects_unknown_role():
    try:
        load_prompt("UNKNOWN")
    except KeyError:
        return
    raise AssertionError("unknown role must fail")


def test_templates_state_role_specific_contracts():
    assert "BriefSchema" in load_prompt("PROMPT_AGENT")
    assert "acceptance_criteria" in load_prompt("PO")
    assert "GeneratedCode" in load_prompt("DEVELOPER")
    assert "smoke" in load_prompt("QA_ENGINEER").lower()
    assert "inspecting" in load_prompt("REVIEWER").lower()
