from scrum_team.utils.llm_factory import get_llm
from scrum_team.utils.brief_schema import BriefSchema
from scrum_team.memory_retriever import get_prompt_agent_memory_context
from scrum_team.middleware.error_handler import execute_with_retry
from scrum_team.agents.prompt_loader import load_prompt
import logging
import json

logger = logging.getLogger(__name__)

def generate_brief(raw_input: str) -> BriefSchema:
    def _invoke_brief():
        llm = get_llm("SCRUM_MASTER")
        structured_llm = llm.with_structured_output(BriefSchema)
        
        memory_ctx = get_prompt_agent_memory_context()
        prompt = (
            f"{load_prompt('PROMPT_AGENT')}\n\n"
            "Convert the request into the declared schema.\n"
            f"Request: {raw_input}"
        )

        if memory_ctx:
            prompt += f"\n{memory_ctx}"
            
        try:
            return structured_llm.invoke(prompt)
        except Exception:
            res = llm.invoke(prompt)
            text = res.content if hasattr(res, "content") else str(res)
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            data = json.loads(text)
            return BriefSchema(**data)

    try:
        return execute_with_retry(_invoke_brief, max_retries=2, task_name="Prompt Agent Brief Generation")
    except Exception as e:
        logger.error(f"Prompt Agent error: {e}. Falling back to default structured brief.")
        return BriefSchema(
            goal=f"Process user request: {raw_input[:100]}",
            scope=[raw_input[:150]],
            constraints=["Local environment execution"],
            acceptance_criteria=["Functionality completes without error"],
            priorities=["Core implementation"]
        )
