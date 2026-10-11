import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from models import ResearchRun


class Library:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created TEXT, payload TEXT);
                CREATE TABLE IF NOT EXISTS saved (id TEXT PRIMARY KEY, payload TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS feedback (id TEXT PRIMARY KEY, verdict TEXT);
            """)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def add_run(self, run: ResearchRun):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO runs VALUES (?, ?, ?)", (run.id, run.created_at, run.model_dump_json()))

    def runs(self) -> list[ResearchRun]:
        with self.connect() as db:
            return [ResearchRun.model_validate_json(row[0]) for row in db.execute("SELECT payload FROM runs ORDER BY created DESC LIMIT 30")]

    def save(self, run: ResearchRun, topic_id: str):
        topic = next(t for t in run.topics if t.id == topic_id)
        payload = {"topic": topic.model_dump(), "mode": run.mode, "sources": [s.model_dump() for s in run.sources if s.id in topic.source_ids]}
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO saved(id, payload) VALUES (?, ?)", (topic.id, json.dumps(payload, ensure_ascii=False)))

    def saved(self) -> list[dict]:
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM saved ORDER BY created DESC")]

    def remove(self, topic_id: str):
        with self.connect() as db:
            db.execute("DELETE FROM saved WHERE id = ?", (topic_id,))

    def feedback(self, topic_id: str, verdict: str):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO feedback VALUES (?, ?)", (topic_id, verdict))

    def verdicts(self) -> dict[str, str]:
        with self.connect() as db:
            return dict(db.execute("SELECT id, verdict FROM feedback"))
