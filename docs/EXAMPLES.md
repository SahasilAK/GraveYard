# Examples

## Example project brief

```text
Build a small Python utility that reads a CSV file with name and age columns and returns a list of dictionaries. It should handle header-only files by returning an empty list and should raise a clear error for missing files.
```

## Expected team flow

1. Prompt Agent converts the brief into a structured project brief.
2. Product Owner creates backlog items with acceptance criteria.
3. Scrum Master routes the next ready task.
4. Developer writes real code and passes the Step 25 validation gate.
5. QA runs a smoke check.
6. Reviewer inspects changed files.
7. Human approval decides whether to continue or request rework.

## Example generated file location

```text
projects/csv_utility/csv_reader.py
```

## Example prompt-regression command

```bash
python -m pytest tests/unit/test_prompt_templates.py tests/unit/test_step25_validation_gate.py tests/unit/test_step27_prompt_regression.py -q
```