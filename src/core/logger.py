
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "extra_data"):
            log_obj.update(record.extra_data)
            
        return json.dumps(log_obj, ensure_ascii=False)

class OneAgentLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OneAgentLogger, cls).__new__(cls)
            cls._instance._init_logger()
        return cls._instance
    
    def _init_logger(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Log file name based on date: logs/2023-10-27.log
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"{today}.log"
        
        self.logger = logging.getLogger("OneAgent")
        self.logger.setLevel(logging.INFO)
        
        # File Handler (JSONL)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(JsonFormatter())
        self.logger.addHandler(file_handler)
        
        # Console Handler (Text for dev)
        # console_handler = logging.StreamHandler()
        # console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        # self.logger.addHandler(console_handler)

    def log(self, event: str, content: Any, agent: str = "System", trace_id: str = "", span_id: str = "", parent_span_id: str = ""):
        """
        Structured Log Event.
        """
        extra = {
            "event": event,
            "agent": agent,
            "content": content,
        }
        if trace_id: extra["trace_id"] = trace_id
        if span_id: extra["span_id"] = span_id
        if parent_span_id: extra["parent_span_id"] = parent_span_id
        
        self.logger.info(event, extra={"extra_data": extra})

# Global Instance
logger = OneAgentLogger()
