DEVELOPER_CASES = [
    {
        "name": "csv_reader",
        "file_path": "csv_reader.py",
        "task_description": "Parse CSV records into dictionaries",
        "good_code": """import csv


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
""",
        "required_markers": ("csv.DictReader", "open("),
        "missing_operation_code": """import csv


def read_rows(path):
    return []
""",
    },
    {
        "name": "json_loader",
        "file_path": "json_loader.py",
        "task_description": "Load JSON configuration from disk",
        "good_code": """import json


def load_config(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
""",
        "required_markers": ("json.load", "open("),
        "missing_operation_code": """import json


def load_config(path):
    return {}
""",
    },
    {
        "name": "api_endpoint",
        "file_path": "api.py",
        "task_description": "Create an API endpoint that returns health status",
        "good_code": """from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}
""",
        "required_markers": ("@app.get", "status"),
        "missing_operation_code": """from fastapi import FastAPI

app = FastAPI()


def health():
    return {"status": "ok"}
""",
    },
]

BAD_PLACEHOLDER_CODE = "def run():\n    print('Atomic step 1 executed.')\n"