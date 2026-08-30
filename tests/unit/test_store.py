import subprocess
import sys
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable

def run_phase_1(test_db: Path, test_key: str):
    code = f"""
from pathlib import Path
from scrum_team.memory_store import create_store, put_memory, get_memory
from scrum_team.graph import create_graph

db_path = Path(r'{test_db}')
put_memory(("developer", "code_patterns"), "{test_key}", {{"language": "python", "pattern": "factory"}}, db_path=db_path)
item = get_memory(("developer", "code_patterns"), "{test_key}", db_path=db_path)
assert item is not None, "Phase 1 put failed"
assert item.value["pattern"] == "factory", "Phase 1 value mismatch"

graph = create_graph(r'{ROOT_DIR / "data" / "checkpoints.db"}')
assert getattr(graph, 'store', None) is not None, "Graph compilation missing bound store"
print("PHASE_1_SUCCESS")
"""
    result = subprocess.run([PYTHON_EXE, "-c", code], capture_output=True, text=True, check=True)
    assert "PHASE_1_SUCCESS" in result.stdout

def run_phase_2(test_db: Path, test_key: str):
    code = f"""
from pathlib import Path
from scrum_team.memory_store import get_memory, search_memory, delete_memory

db_path = Path(r'{test_db}')
item = get_memory(("developer", "code_patterns"), "{test_key}", db_path=db_path)
assert item is not None, "Phase 2 get after process restart failed"
assert item.value["language"] == "python"

results = search_memory(("developer", "code_patterns"), filter={{"language": "python"}}, db_path=db_path)
assert any(r.key == "{test_key}" for r in results), "Phase 2 search failed"

delete_memory(("developer", "code_patterns"), "{test_key}", db_path=db_path)
assert get_memory(("developer", "code_patterns"), "{test_key}", db_path=db_path) is None, "Phase 2 delete failed"
print("PHASE_2_SUCCESS")
"""
    result = subprocess.run([PYTHON_EXE, "-c", code], capture_output=True, text=True, check=True)
    assert "PHASE_2_SUCCESS" in result.stdout

def test_store_operations_and_persistence():
    test_db = ROOT_DIR / "data" / "test_memory.db"
    if test_db.exists():
        test_db.unlink()
    test_key = f"test_key_{uuid.uuid4().hex[:6]}"
    
    try:
        run_phase_1(test_db, test_key)
        run_phase_2(test_db, test_key)
        print("ALL_STORE_TESTS_PASSED")
    finally:
        if test_db.exists():
            test_db.unlink()

if __name__ == "__main__":
    test_store_operations_and_persistence()
