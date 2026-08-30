import sqlite3
from pathlib import Path
from typing import Any

from langgraph.store.base import BaseStore
from langgraph.store.sqlite import SqliteStore

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STORE_PATH = ROOT_DIR / "data" / "memory.db"


def create_store(db_path: str | Path = DEFAULT_STORE_PATH) -> BaseStore:
    """Create a persistent SQLite-backed LangGraph BaseStore."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
    store = SqliteStore(conn)
    store.setup()
    return store


def put_memory(namespace: tuple[str, ...], key: str, value: dict[str, Any], db_path: str | Path = DEFAULT_STORE_PATH) -> None:
    store = create_store(db_path)
    store.put(namespace, key, value)


def get_memory(namespace: tuple[str, ...], key: str, db_path: str | Path = DEFAULT_STORE_PATH):
    store = create_store(db_path)
    return store.get(namespace, key)


def search_memory(namespace: tuple[str, ...], filter: dict[str, Any] | None = None, limit: int = 10, db_path: str | Path = DEFAULT_STORE_PATH):
    store = create_store(db_path)
    return store.search(namespace, filter=filter, limit=limit)


def delete_memory(namespace: tuple[str, ...], key: str, db_path: str | Path = DEFAULT_STORE_PATH) -> None:
    store = create_store(db_path)
    store.delete(namespace, key)
