from typing import Dict, List, Any, Optional, Set
from src.core.capability import Capability

class Registry:
    _instance = None

    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}
        self._runtime_tools: Set[str] = set()  # Tools only for sub-agents, not Orchestrator

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, capability: Capability, is_runtime_tool: bool = False):
        """
        注册一个新的能力。
        Register a new capability.
        
        Args:
            capability: The capability to register
            is_runtime_tool: If True, this tool is only for sub-agents (excluded from Orchestrator)
        """
        if capability.name in self._capabilities:
            print(f"Warning: Overwriting capability '{capability.name}'")
        self._capabilities[capability.name] = capability
        
        if is_runtime_tool:
            self._runtime_tools.add(capability.name)
            
        print(f"Registered capability: {capability.name}")

    def get_capability(self, name: str) -> Optional[Capability]:
        return self._capabilities.get(name)
    
    def get_runtime_tools(self) -> List[str]:
        """获取所有 runtime tools 的名称列表"""
        return list(self._runtime_tools)

    def get_all_tool_schemas(
        self, 
        whitelist: Optional[List[str]] = None, 
        blacklist: Optional[List[str]] = None,
        exclude_runtime_tools: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取所有注册能力的 OpenAI 函数模式。
        如果提供了 whitelist，则仅返回白名单中的工具。
        如果提供了 blacklist，则排除黑名单中的工具。
        如果 exclude_runtime_tools=True，则排除所有 runtime tools。
        
        Get all registered capabilities as OpenAI function schemas.
        If whitelist is provided, only return those tools.
        If blacklist is provided, exclude those tools.
        If exclude_runtime_tools=True, exclude all runtime tools.
        """
        # Build effective blacklist
        effective_blacklist = set(blacklist) if blacklist else set()
        if exclude_runtime_tools:
            effective_blacklist.update(self._runtime_tools)
        
        if whitelist is not None:
            filtered = []
            for name in whitelist:
                if name in effective_blacklist:
                    continue
                cap = self.get_capability(name)
                if cap:
                    filtered.append(cap.to_function_schema())
                else:
                    print(f"Warning: Whitelisted tool '{name}' not found in registry.")
            return filtered
        
        # No whitelist: return all except blacklist
        result = []
        for name, cap in self._capabilities.items():
            if name in effective_blacklist:
                continue
            result.append(cap.to_function_schema())
        return result

    def get_capabilities_tree_string(self) -> str:
        """
        Generates a tree view string of all registered capabilities.
        Example:
        - [Tool] get_system_info: Get basic information...
        - [Agent] sample_agent: A sample agent... [Tools: tool1, tool2]
        """
        lines = []
        for name, cap in self._capabilities.items():
            # Prefix selection based on type
            prefix = "[Agent]" if hasattr(cap, "allowed_tools") else "[Tool]"
            lines.append(f"- {prefix} {cap.get_context_description()}")
        return "\n".join(lines)

global_registry = Registry.get_instance()
