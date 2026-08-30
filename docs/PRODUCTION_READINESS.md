# Production Readiness

## Required before real use

- Configure provider credentials and model routing.
- Run the prompt regression gate after every prompt edit.
- Run the full test suite before releasing changes.
- Review generated code before approving workflow continuation.
- Monitor Logs for validation-gate retries and failed agent calls.

## Operational data

The app stores checkpoint and memory data locally under `data/`. Back up this directory if workflow continuity and learned preferences matter for your deployment.

## Security boundaries

Agent file access is scoped to generated project directories. Keep secrets out of project briefs and generated project folders. Do not approve generated code that writes outside `projects/<project_name>/`.

## Known limits

Live end-to-end tests need provider credentials. The validation gate is heuristic and catches common placeholder patterns; QA and human review remain required for production-grade confidence.