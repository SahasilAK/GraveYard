# User Guide

## Start the app

1. Run `first_run.bat` once to create the virtual environment and install dependencies.
2. Run `start_app.bat` to open the Streamlit dashboard.
3. Configure provider credentials before running live agent workflows.

## Create a project

1. Open the Chat tab.
2. Describe the product or feature in concrete terms.
3. Submit the brief and watch the Logs tab for agent activity.
4. Review Developer output when the graph pauses for human approval.
5. Choose Approve to continue or Request Rework to send feedback back into the workflow.

## Manage memory

Use the Memory Manager tab to inspect or delete long-term memories stored in `data/memory.db`. Delete memories that are stale, too rigid, or contradicted by current project requirements.

## Read generated output

Generated source code is written under `projects/<project_name>/`. Check the Logs tab for validation-gate events, retries, QA smoke checks, and review comments.