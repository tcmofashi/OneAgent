
import json
import uuid
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

class SessionManager:
    def __init__(self, session_id: Optional[str] = None):
        self.session_dir = Path("logs/sessions")
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        if session_id:
            self.session_id = session_id
            self.loaded = self._load()
        else:
            self.session_id = str(uuid.uuid4())
            self.loaded = False
            
        if not self.loaded:
            # New Session State
            self.trace_id = str(uuid.uuid4())
            self.history: List[Dict[str, Any]] = []
            self.task_list: str = "(No tasks yet)"
            self.variables: Dict[str, Any] = {}
            self.created_at = datetime.now().isoformat()
            self._save() # Initial Save
        
    def _get_file_path(self) -> Path:
        return self.session_dir / f"{self.session_id}.json"

    def _load(self) -> bool:
        path = self._get_file_path()
        if not path.exists():
            print(f"[Session] Session file {path} not found. Starting new.")
            return False
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.trace_id = data.get("trace_id", str(uuid.uuid4()))
                self.history = data.get("history", [])
                self.task_list = data.get("task_list", "")
                self.variables = data.get("variables", {})
                self.created_at = data.get("created_at", "")
                print(f"[Session] Loaded session {self.session_id}")
                return True
        except Exception as e:
            print(f"[Session] Failed to load session: {e}")
            return False

    def _save(self):
        path = self._get_file_path()
        data = {
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "updated_at": datetime.now().isoformat(),
            "created_at": self.created_at,
            "task_list": self.task_list,
            "variables": self.variables,
            "history": self.history
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Session] Failed to save session: {e}")

    def add_history(self, message: Dict[str, Any]):
        self.history.append(message)
        self._save()

    def update_task_list(self, new_list: str):
        self.task_list = new_list
        self._save()
        
    
    def truncate_history(self, index: int):
        """
        Rewind history to a specific index (keep 0..index-1).
        """
        if 0 <= index < len(self.history):
            self.history = self.history[:index]
            self._save()
            print(f"[Session] Rewound to index {index}")
            
    def get_history_summary(self) -> str:
        """Helper to get last user message or brief summary."""
        for msg in reversed(self.history):
            if msg["role"] == "user":
                return msg["content"][:50] + "..."
        return "Empty Session"
            
    @classmethod
    def list_sessions(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List all available sessions sorted by updated_at desc.
        """
        session_dir = Path("logs/sessions")
        if not session_dir.exists():
            return []
            
        sessions = []
        for f in session_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    sessions.append({
                        "id": data.get("session_id"),
                        "updated_at": data.get("updated_at"),
                        "created_at": data.get("created_at"),
                        # We could add a summary later
                    })
            except:
                pass
                
        # Sort by updated_at desc
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions[:limit]
        
    def get_history(self) -> List[Dict[str, Any]]:
        return self.history
