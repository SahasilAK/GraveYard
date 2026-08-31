from pathlib import Path
import sys
import json
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import config
from scrum_team.runner import get_project_state, run_project_graph, request_stop
from scrum_team.utils.llm_factory import list_models
from webapp.memory_ui import render_memory_manager

PROJECTS_DIR = ROOT_DIR / "projects"
AGENTS = [
    ("Prompt Agent", "Structures raw human input into a crisp project brief", "SCRUM_MASTER"),
    ("Product Owner", "Owns and prioritizes the product backlog and user stories", "PO"),
    ("Scrum Master", "Coordinates team workflow, sprint cadence, and routing", "SCRUM_MASTER"),
    ("Developer", "Implements backlog tasks and writes code for current project", "DEVELOPER"),
    ("QA Engineer", "Runs automated smoke checks and full QA verification", "QA"),
    ("Reviewer", "Performs code review, quality gatekeeping, and standards compliance", "REVIEWER"),
]


def list_projects():
    if not PROJECTS_DIR.exists():
        return []
    return sorted(path.name for path in PROJECTS_DIR.iterdir() if path.is_dir() and not path.name.startswith("."))


def add_log(message: str):
    st.session_state.logs.append(message)


st.set_page_config(
    page_title="GraveYard",
    page_icon=":material/groups:",
    layout="wide",
)

if "logs" not in st.session_state:
    st.session_state.logs = ["Workspace initialized"]
if "agent_drafts" not in st.session_state:
    st.session_state.agent_drafts = {
        name: {"role": role, "prompt": description, "model": config.get("model_mapping", {}).get(role, "")}
        for name, description, role in AGENTS
    }
if "omniroute_draft" not in st.session_state:
    st.session_state.omniroute_draft = {
        "url": config.get("omniroute", {}).get("url", ""),
        "api_key": config.get("omniroute", {}).get("api_key", ""),
    }

# Sidebar Navigation
with st.sidebar:
    st.title("GraveYard")
    st.caption("Local autonomous multi-agent orchestration")

    section = st.radio(
        "Navigation",
        [
            ":material/chat: Chat",
            ":material/list_alt: Logs",
            ":material/smart_toy: Agents",
            ":material/settings: API Setup",
            ":material/psychology: Memory Manager",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    projects = list_projects()
    st.metric("Active projects", len(projects))


# Title Header
st.title("AI GraveYard Workspace")
st.caption("Coordinate projects, review developer output, and automate quality assurance.")


def render_chat():
    st.header("Chat")

    # Initialize session state keys used in this view
    if "chat_mode" not in st.session_state:
        st.session_state.chat_mode = "new_project"
    if "chat_project_name" not in st.session_state:
        st.session_state.chat_project_name = ""

    mode = st.segmented_control(
        "Request mode",
        [
            "new_project",
            "fix_bug",
            "add_new_feature",
        ],
        format_func=lambda x: {
            "new_project": "New project",
            "fix_bug": "Fix bug",
            "add_new_feature": "Add new feature",
        }[x],
        default="new_project",
    )

    project_name = st.session_state.chat_project_name
    if mode == "new_project":
        project_name = st.text_input(
            "Project name",
            placeholder="e.g. workout-tracker",
            help="Name of the new workspace directory",
            value=st.session_state.chat_project_name,
            key="chat_project_name_widget",
        )
        st.session_state.chat_project_name = project_name
    else:
        existing_projects = list_projects()
        if existing_projects:
            project_name = st.selectbox(
                "Select target project",
                existing_projects,
                help="Choose an existing project from the workspace",
            )
        else:
            st.info("No projects available yet. Create a new project first.")

    request = st.text_area(
        "Request description",
        placeholder={
            "new_project": "Describe the product you want to build (e.g. 'Build a CLI workout logger in Python with file storage')...",
            "fix_bug": "Describe the issue and expected behavior...",
            "add_new_feature": "Describe the new feature and acceptance criteria...",
        }[mode],
        disabled=mode != "new_project" and not project_name,
        height=120,
    )

    col_run, col_stop = st.columns([3, 1])
    with col_run:
        if st.button("Run GraveYard Pipeline", type="primary", disabled=not project_name or not request.strip()):
            safe_name = project_name.strip().replace(" ", "-")
            (PROJECTS_DIR / safe_name).mkdir(parents=True, exist_ok=True)
            project_name = safe_name
            
            with st.spinner("GraveYard is executing graph workflow..."):
                run_project_graph(project_name, raw_input=request, log_callback=add_log)
            st.session_state.active_project = project_name
            st.rerun()

    with col_stop:
        if st.button("🛑 Emergency Stop Team"):
            request_stop()
            add_log("🛑 Emergency stop signal triggered by user.")
            st.warning("Emergency stop requested. The execution will halt after the current step.")

    # If a project is selected or active, inspect its graph checkpoint state
    active_project = project_name or st.session_state.get("active_project")
    if active_project:
        st.divider()
        st.subheader(f"Project: {active_project}")
        
        state_snap = get_project_state(active_project)
        values = state_snap.values if (state_snap and state_snap.values) else {}
        next_nodes = state_snap.next if state_snap else ()
        
        status = values.get("status", "not_started")
        is_paused = "human_review" in next_nodes or status == "qa_approval"
        
        if is_paused:
            st.warning("⚠️ **HUMAN-IN-THE-LOOP CHECKPOINT: Review Developer Output & QA Smoke Test**")
            with st.container(border=True):
                col_dev, col_qa = st.columns(2)
                with col_dev:
                    st.markdown("### Developer Output")
                    dev_out = values.get("dev_output", {})
                    st.json(dev_out)
                with col_qa:
                    st.markdown("### QA Smoke Test Results")
                    qa_out = values.get("qa_smoke_results", {})
                    st.json(qa_out)

                st.markdown("---")
                st.markdown("### Review Action")
                btn_col1, btn_col2 = st.columns([1, 2])
                with btn_col1:
                    if st.button("✅ Approve & Complete Project", type="primary"):
                        with st.spinner("Resuming pipeline with approval..."):
                            run_project_graph(active_project, resume_command={"approved": True}, log_callback=add_log)
                        st.rerun()
                with btn_col2:
                    rework_feedback = st.text_input("Rework Feedback", placeholder="Describe required changes (e.g. 'Fix function signature')...")
                    if st.button("🔄 Request Rework", disabled=not rework_feedback.strip()):
                        with st.spinner("Routing feedback to Prompt Agent for rework..."):
                            run_project_graph(active_project, resume_command={"approved": False, "feedback": rework_feedback}, log_callback=add_log)
                        st.rerun()
        else:
            st.info(f"**Current Status:** `{status.upper()}`")

        # Tabs for inspecting state details & files
        tab_backlog, tab_files, tab_qa, tab_agent_logs = st.tabs(["Brief & Backlog", "Project Files", "QA Results", "Agent Logs"])
        
        with tab_backlog:
            brief_raw = values.get("brief")
            if brief_raw:
                try:
                    brief_json = json.loads(brief_raw) if isinstance(brief_raw, str) else brief_raw
                    st.markdown("#### Product Brief")
                    st.json(brief_json)
                except Exception:
                    st.text(brief_raw)
            
            backlog = values.get("backlog", [])
            if backlog:
                st.markdown(f"#### Backlog ({len(backlog)} tasks)")
                for idx, task in enumerate(backlog):
                    if isinstance(task, dict):
                        title = task.get("title") or task.get("reason", f"Task #{idx+1}")
                        desc = task.get("description", "")
                        criteria = task.get("acceptance_criteria", [])
                    else:
                        title = str(task)
                        desc, criteria = "", []
                        
                    with st.expander(f"{idx+1}. {title}"):
                        if desc: st.write(desc)
                        if criteria:
                            st.markdown("**Acceptance Criteria:**")
                            for c in criteria: st.markdown(f"- {c}")

        with tab_files:
            proj_path = PROJECTS_DIR / active_project
            if proj_path.exists():
                file_list = [f.name for f in proj_path.iterdir() if f.is_file()]
                if file_list:
                    selected_file = st.selectbox("Select file to view", file_list)
                    if selected_file:
                        file_content = (proj_path / selected_file).read_text(encoding="utf-8")
                        st.code(file_content, language="python")
                else:
                    st.caption("No files generated in project folder yet.")

        with tab_qa:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Smoke Check")
                st.json(values.get("qa_smoke_results", {}))
            with col2:
                st.markdown("#### Full QA Results")
                st.json(values.get("qa_full_results", {}))

        with tab_agent_logs:
            st.markdown("#### Agent Outputs & Activity")
            selected_agent = st.selectbox(
                "Select Agent to inspect",
                ["Scrum Master", "Prompt Agent", "Product Owner", "Developer", "QA Engineer", "Reviewer"]
            )
            
            with st.container(border=True):
                if selected_agent == "Scrum Master":
                    st.markdown("**Agent Output: Graph Orchestration & Sprint Routing State**")
                    st.json({
                        "project_id": values.get("project_id", active_project),
                        "workflow_status": values.get("status", "planning"),
                        "current_checkpoint": state_snap.next if state_snap else (),
                        "has_brief": bool(values.get("brief")),
                        "backlog_count": len(values.get("backlog", []))
                    })

                elif selected_agent == "Prompt Agent":
                    st.markdown("**Agent Output: Structured Brief & Input Parsing**")
                    brief_raw = values.get("brief")
                    if brief_raw:
                        try:
                            st.json(json.loads(brief_raw) if isinstance(brief_raw, str) else brief_raw)
                        except Exception:
                            st.text(brief_raw)
                    else:
                        st.info("No brief generated yet by Prompt Agent.")
                        
                elif selected_agent == "Product Owner":
                    st.markdown("**Agent Output: Product Backlog & Acceptance Criteria**")
                    backlog = values.get("backlog", [])
                    if backlog:
                        st.json(backlog)
                    else:
                        st.info("No backlog generated yet by Product Owner.")
                        
                elif selected_agent == "Developer":
                    st.markdown("**Agent Output: Code Artifacts & Change Summary**")
                    dev_out = values.get("dev_output", {})
                    if dev_out:
                        st.json(dev_out)
                    else:
                        st.info("No developer output recorded yet.")
                        
                elif selected_agent == "QA Engineer":
                    st.markdown("**Agent Output: Smoke Check & Full QA Test Verification**")
                    st.markdown("##### Smoke Check")
                    st.json(values.get("qa_smoke_results", {}))
                    st.markdown("##### Full QA")
                    st.json(values.get("qa_full_results", {}))
                    
                elif selected_agent == "Reviewer":
                    st.markdown("**Agent Output: Code Review & Final Gatekeeper Assessment**")
                    status = values.get("status", "")
                    if status == "finished":
                        st.success("Reviewer Status: Approved & Complete")
                        st.json({"status": "approved", "full_qa": values.get("qa_full_results", {})})
                    else:
                        st.info(f"Reviewer assessment pending. Current status: `{status.upper()}`")

            # Filter workspace logs for the selected agent
            agent_log_keywords = {
                "Scrum Master": "[Scrum Master]",
                "Prompt Agent": "[Prompt Agent]",
                "Product Owner": "[Product Owner]",
                "Developer": "[Developer]",
                "QA Engineer": "[QA Engineer]",
                "Reviewer": "[Reviewer Agent]"
            }
            keyword = agent_log_keywords.get(selected_agent, "")
            matching_logs = [log for log in st.session_state.logs if keyword in log]
            
            st.markdown(f"##### Recent Execution Logs for `{selected_agent}`")
            if matching_logs:
                for log in reversed(matching_logs):
                    st.text(log)
            else:
                st.caption(f"No specific runtime logs recorded yet for {selected_agent}.")


def render_logs():
    st.header("Activity Logs")

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("Clear logs"):
            st.session_state.logs = []
            st.rerun()

    if not st.session_state.logs:
        st.info("No activity recorded yet.")
        return

    with st.container(border=True):
        for idx, entry in enumerate(reversed(st.session_state.logs)):
            log_num = len(st.session_state.logs) - idx
            st.text(f"[{log_num:03d}] {entry}")


def render_agents():
    st.header("Team Agents")
    st.caption("Manage agent definitions and OmniRoute model aliases.")

    cols = st.columns(2)
    for idx, (name, description, role) in enumerate(AGENTS):
        with cols[idx % 2]:
            with st.container(border=True):
                st.subheader(name)
                st.write(description)
                st.caption(f"Role: `{role}`")

                draft = st.session_state.agent_drafts[name]
                with st.expander("Configure agent"):
                    draft["role"] = st.text_input("Role identifier", draft["role"], key=f"role_{name}")
                    draft["model"] = st.text_input("Model alias", draft["model"], key=f"model_{name}")
                    draft["prompt"] = st.text_area("Base prompt instructions", draft["prompt"], key=f"prompt_{name}", height=90)

    st.divider()
    if st.button("Add new agent"):
        st.info("Adding custom agents is not available yet.")


def render_config():
    st.header("API Setup")
    st.caption("Configure providers and choose a connection for each model.")

    import yaml
    existing = config.get("connections", {})
    if "connection_draft" not in st.session_state:
        st.session_state.connection_draft = {name: dict(value) for name, value in existing.items()}
    drafts = st.session_state.connection_draft
    with st.container(border=True):
        st.subheader("Connections")
        name = st.text_input("Connection name")
        provider = st.selectbox("Provider", ["openai", "anthropic", "google", "omniroute", "local"])
        url = st.text_input("Base URL (optional for hosted providers)")
        api_key = st.text_input("API key", type="password")
        if st.button("Add or update connection"):
            if name.strip():
                drafts[name.strip()] = {"provider": provider, "url": url, "api_key": api_key}
                st.success("Connection staged. Save configuration to persist it.")
            else:
                st.error("Connection name is required.")
        for connection_name, value in list(drafts.items()):
            st.write(f"**{connection_name}** ({value.get('provider', 'openai')})")
            if st.button(f"Remove {connection_name}", key=f"remove_{connection_name}"):
                del drafts[connection_name]
                st.rerun()

    with st.container(border=True):
        st.subheader("Model Role Mappings")
        mapping = config.get("model_mapping", {})
        assignments = {}
        names = list(drafts)
        for role, old in mapping.items():
            old = old if isinstance(old, dict) else {"connection": "omniroute", "model": old}
            connection = st.selectbox(f"{role} connection", names, index=names.index(old.get("connection")) if old.get("connection") in names else 0, key=f"connection_{role}") if names else ""
            available = list_models(drafts.get(connection, {})) if connection else []
            model = st.selectbox(f"{role} model", available, index=available.index(old.get("model")) if old.get("model") in available else None, key=f"model_{role}") if available else st.text_input(f"{role} model", old.get("model", ""), key=f"model_{role}")
            assignments[role] = {"connection": connection, "model": model}

    if st.button("Save Configuration", type="primary"):
        invalid = [role for role, value in assignments.items() if not value["connection"] or not value["model"].strip() or value["connection"] not in drafts]
        if invalid:
            st.error(f"Fix model assignments for: {', '.join(invalid)}")
            return
        with open(ROOT_DIR / "config" / "config.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump({"connections": drafts, "model_mapping": assignments}, f, sort_keys=False)
        st.success("Configuration saved locally.")
        st.rerun()


def run_chat():
    if "Chat" in section:
        try:
            render_chat()
        except Exception as e:
            st.error(f"Error in Chat: {e}")
    elif "Logs" in section:
        try:
            render_logs()
        except Exception as e:
            st.error(f"Error in Logs: {e}")
    elif "Agents" in section:
        try:
            render_agents()
        except Exception as e:
            st.error(f"Error in Agents: {e}")
    elif "Memory" in section:
        try:
            render_memory_manager()
        except Exception as e:
            st.error(f"Error in Memory Manager: {e}")
    else:
        try:
            render_config()
        except Exception as e:
            st.error(f"Error in Config: {e}")

run_chat()
