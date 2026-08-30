# Testing

## Fast offline checks

```bash
python -m pytest tests/unit -q
```

## Prompt regression gate

Run this after editing anything under `scrum_team/agents/prompts/`:

```bash
python -m pytest tests/unit/test_prompt_templates.py tests/unit/test_step25_validation_gate.py tests/unit/test_step27_prompt_regression.py -q
```

These checks should stay offline unless a test explicitly targets OmniRoute.

## Live provider testing policy

Only test the local OmniRoute connection. Allowed live model targets are `auto` and `auto/best-coding`. Tests for OpenAI, DeepSeek, Anthropic, Google, or any other direct provider/model route should stay skipped or commented out unless the project is explicitly reconfigured to support them.

## Full suite

```bash
python -m pytest tests -q
```

Some end-to-end tests require the local OmniRoute service and approved model routes. If credentials or model routes are missing, failures mentioning provider authentication or unavailable non-OmniRoute models are environment/configuration failures, not prompt-regression failures.

## Windows helper

```bat
run_tests.bat
```