from typing import Dict, List, Any, Optional
from src.core.capability import Capability

class Registry:
    _instance = None

    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, capability: Capability):
        """
        Register a new capability.
        """
        if capability.name in self._capabilities:
            print(f"Warning: Overwriting capability '{capability.name}'")
        self._capabilities[capability.name] = capability
        print(f"Registered capability: {capability.name}")

    def get_capability(self, name: str) -> Optional[Capability]:
        return self._capabilities.get(name)

    def get_all_tool_schemas(self, whitelist: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get all registered capabilities as OpenAI function schemas.
        If whitelist is provided, only return those tools.
        """
        if whitelist is None:
             return [cap.to_function_schema() for cap in self._capabilities.values()]
        
        filtered = []
        for name in whitelist:
            cap = self.get_capability(name)
            if cap:
                filtered.append(cap.to_function_schema())
            else:
                 print(f"Warning: Whitelisted tool '{name}' not found in registry.")
        return filtered

global_registry = Registry.get_instance()
