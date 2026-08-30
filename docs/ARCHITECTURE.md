# Architecture

## Overview

AI Scrum Team is a local multi-agent workflow that turns a user brief into backlog, implementation, QA, review, and human approval steps.

## Agent roles

- Prompt Agent: converts unstructured input into a structured brief.
- Product Owner: creates backlog and concrete implementation plans.
- Scrum Master: routes workflow state.
- Developer: researches and writes scoped project files.
- QA Engineer: runs smoke checks and reports results.
- Reviewer: inspects generated files before completion.

## Prompt templates

Canonical role prompts live in `scrum_team/agents/prompts/` and are loaded by `scrum_team/agents/prompt_loader.py`. Prompt edits must pass the prompt regression gate documented in `docs/TESTING.md`.

## State and storage

- Checkpoints: `data/checkpoints.db`
- Long-term memory: `data/memory.db`
- Generated projects: `projects/<project_name>/`

## Validation gate

Developer output is checked by `scrum_team.nodes.dev_agent.validate_generated_code()` before QA. Placeholder, mock, pseudo, print-only, and missing-operation implementations are rejected and regenerated within the configured retry limit.