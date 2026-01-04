"""
AutoGLM GUI Agent - 智谱 AutoGLM-Phone 封装

将智谱的 Open-AutoGLM 封装为 OneAgent 标准子 Agent。
该 Agent 可以通过 ADB/HDC 控制安卓/鸿蒙设备执行 GUI 自动化任务。

模型支持：
- 云端 API：智谱 BigModel / ModelScope
- 本地部署：vLLM / SGLang / Ollama

动作映射：
- finish → report_status(status="success")
- error → report_status(status="failure")
"""
import sys
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from src.core.capability import BaseAgent
from src.core.config import global_config

# 路径常量
AGENT_DIR = Path(__file__).resolve().parent
AGENT_CONFIG_PATH = AGENT_DIR / "config.toml"

# 添加 phone_agent 到 Python 路径
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))


def load_agent_config() -> dict:
    """加载 Agent 专属配置"""
    if AGENT_CONFIG_PATH.exists():
        with open(AGENT_CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    return {}


class AutoGLMGUIAgent(BaseAgent):
    """
    AutoGLM GUI 自动化子 Agent，封装 Open-AutoGLM 的核心功能。
    
    通过安卓/鸿蒙设备执行 GUI 自动化任务，支持：
    - 点击、输入、滑动等基本操作
    - 应用启动和切换
    - 敏感操作确认和人工接管
    - 多平台支持（Android/iOS/鸿蒙）
    
    配置来源：
    - 模型：config/config.toml -> llm.functional_roles.autoglm
    - Agent 参数：本目录 config.toml
    """
    
    name: str = "autoglm_gui_agent"
    description: str = (
        "[AutoGLM] 通过安卓/鸿蒙设备执行 GUI 自动化任务。使用 AutoGLM-Phone-9B 模型（支持云端API），"
        "可以控制手机完成点击、输入、滑动等操作。支持 Android、iOS、鸿蒙设备。"
    )
    allowed_tools: list[str] = ["report_status"]
    
    # 能力描述 - 简洁格式
    CAPABILITIES_SUMMARY = "手机GUI控制(点击/输入/滑动), 应用启动切换, 屏幕截图分析, 多平台支持(Android/iOS/鸿蒙)"
    
    def get_context_description(self) -> str:
        """返回简洁的能力描述"""
        return f"{self.name} (Agent): 手机GUI自动化代理 [{self.CAPABILITIES_SUMMARY}] [Tools: {', '.join(self.allowed_tools)}]"
    
    # 模型角色（对应 config.toml 的 llm.functional_roles）
    model_role: str = "autoglm"
    
    def _get_device_id(self, device_config: dict) -> Optional[str]:
        """根据配置获取设备 ID"""
        device_type = device_config.get("type", "adb")
        selection = device_config.get("selection", "first")
        
        if selection == "specify":
            return device_config.get("device_id")
        
        # 自动检测第一个设备
        try:
            if device_type == "adb":
                from phone_agent.adb import list_devices
            elif device_type == "hdc":
                from phone_agent.hdc import list_devices
            else:
                print(f"[AutoGLMGUIAgent] 不支持的设备类型: {device_type}")
                return None
            
            devices = list_devices()
            if devices:
                return devices[0].device_id
            return None
        except Exception as e:
            print(f"[AutoGLMGUIAgent] 获取设备列表失败: {e}")
            return None
    
    async def execute(
        self, 
        instruction: str, 
        context: Optional[str] = None,
        upstream_capabilities: Optional[str] = None
    ) -> str:
        """
        执行 GUI 自动化任务
        """
        print(f"\n{'='*60}")
        print("🤖 [AutoGLMGUIAgent] 启动 GUI 自动化任务")
        print(f"{'='*60}")
        print(f"📋 任务: {instruction}")
        
        # 1. 加载配置
        agent_config = load_agent_config()
        
        # 2. 获取模型配置
        model_label = global_config.get(f"llm.functional_roles.{self.model_role}")
        if not model_label:
            model_label = "autoglm-phone"  # 默认值
        
        api_base, api_key, model_name = global_config.get_model_config(model_label)
        print(f"🤖 模型: {model_name} ({api_base})")
        
        # 3. 检查设备连接
        device_config = agent_config.get("device", {})
        device_id = self._get_device_id(device_config)
        device_type = device_config.get("type", "adb")
        
        if not device_id:
            return f"[FAILURE] 没有检测到已连接的设备，请检查 {'ADB' if device_type == 'adb' else 'HDC'} 连接"
        
        print(f"📱 设备: {device_id} ({device_type.upper()})")
        
        # 4. 导入 AutoGLM 组件
        try:
            from phone_agent import PhoneAgent
            from phone_agent.model import ModelConfig
            from phone_agent.agent import AgentConfig
        except ImportError as e:
            return f"[FAILURE] 无法导入 AutoGLM 组件: {e}"
        
        # 5. 创建 Agent 配置
        agent_cfg = agent_config.get("agent", {})
        lang = agent_cfg.get("lang", "cn")
        
        model_config = ModelConfig(
            base_url=api_base,
            api_key=api_key,
            model_name=model_name,
            max_tokens=agent_cfg.get("max_tokens", 3000),
            temperature=agent_cfg.get("temperature", 0.1),
            lang=lang,
        )
        
        autoglm_agent_config = AgentConfig(
            max_steps=agent_cfg.get("max_steps", 100),
            device_id=device_id,
            lang=lang,
            verbose=agent_cfg.get("verbose", True),
        )
        
        # 6. 创建并运行 Agent
        print("🚀 开始执行任务...")
        try:
            agent = PhoneAgent(
                model_config=model_config,
                agent_config=autoglm_agent_config,
            )
            
            result = agent.run(instruction)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"[FAILURE] GUI 任务执行出错: {e}"
        
        # 7. 返回结果
        print(f"\n{'='*60}")
        print("✅ [AutoGLMGUIAgent] 任务完成")
        print(f"   结果: {result[:100]}..." if len(result) > 100 else f"   结果: {result}")
        print(f"{'='*60}\n")
        
        if "error" in result.lower() or "失败" in result:
            return f"[FAILURE] {result}"
        else:
            return f"[SUCCESS] {result}"
