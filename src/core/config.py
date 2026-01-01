import os
import sys
import toml
from typing import Any, Dict, Optional
from pathlib import Path
from pydantic import BaseModel

class LLMProvider(BaseModel):
    api_base: str
    api_key: str

class LLMModelConfig(BaseModel):
    provider: str
    model_name: str
    model_config = {"protected_namespaces": ()}

class Config:
    _instance = None
    
    def __init__(self):
        self.config_data: Dict[str, Any] = {}
        self.root_path = Path(__file__).parent.parent.parent
        self.config_path = self.root_path / "config" / "config.toml"
        self.template_path = self.root_path / "config" / "config.template.toml"
        self._load_config()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_config(self):
        if not self.config_path.exists():
            if self.template_path.exists():
                print(f"Config file not found. Creating from template: {self.config_path}")
                import shutil
                shutil.copy(self.template_path, self.config_path)
            else:
                raise FileNotFoundError(f"Config template not found at {self.template_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config_data = toml.load(f)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self.config_data
        try:
            for k in keys:
                value = value[k]
            return value
        except KeyError:
            return default

    def get_model_config(self, label: str) -> tuple[str, str, str]:
        """
        获取指定模型标签的配置 (api_base, api_key, model_name)。
        Returns (api_base, api_key, model_name) for a specific model label.
        """
        model_info = self.get(f"llm.models.{label}")
        
        if not model_info:
            raise ValueError(f"Model label '{label}' not found in [llm.models]")
            
        provider_name = model_info["provider"]
        model_name = model_info["model_name"]
        
        provider_config = self.get(f"llm.providers.{provider_name}")
        if not provider_config:
            raise ValueError(f"Provider '{provider_name}' not found in [llm.providers]")
            
        return provider_config["api_base"], provider_config["api_key"], model_name

    def get_llm_config(self) -> tuple[str, str, str]:
        """
        获取当前激活模型的配置。
        Returns (api_base, api_key, model_name) for the active model.
        """
        active_label = self.get("llm.active_model_label")
        return self.get_model_config(active_label)

global_config = Config.get_instance()
