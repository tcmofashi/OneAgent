"""
GUI Automation Agent - gelab-zero 封装

将阶跃星辰的 GELab-Zero GUI Agent 封装为 OneAgent 标准子 Agent。
该 Agent 可以通过 ADB 控制安卓设备执行 GUI 自动化任务。

动作映射：
- COMPLETE → report_status(status="success")
- ABORT → report_status(status="failure")  
- INFO → report_status(status="interrupted")

配置文件：
- 模型配置：config/config.toml (llm.functional_roles.gui_automation)
- Agent 配置：本目录下的 config.toml
"""
import sys
import os
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
LIB_DIR = AGENT_DIR / "lib"
AGENT_CONFIG_PATH = AGENT_DIR / "config.toml"

# 添加 lib 到 Python 路径（用于相对导入）
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))


def load_agent_config() -> dict:
    """加载 Agent 专属配置"""
    if AGENT_CONFIG_PATH.exists():
        with open(AGENT_CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    return {}


class GUIAutomationAgent(BaseAgent):
    """
    GUI 自动化子 Agent，封装 gelab-zero 的核心功能。
    
    通过安卓设备执行 GUI 自动化任务，支持：
    - 点击、输入、滑动等基本操作
    - 应用唤醒和切换
    - 人机交互确认（INFO 动作）
    
    配置来源：
    - 模型：config/config.toml -> llm.functional_roles.gui_automation
    - Agent 参数：本目录 config.toml
    """
    
    name: str = "gui_automation_agent"
    description: str = (
        "通过安卓设备执行 GUI 自动化任务。可以控制手机完成点击、输入、滑动等操作，"
        "适用于购物、发消息、领补贴等自动化场景。需要 ADB 连接和 ollama 本地模型。"
    )
    allowed_tools: list[str] = ["report_status"]
    
    # 模型角色（对应 config.toml 的 llm.functional_roles）
    model_role: str = "gui_automation"
    
    def _load_config(self) -> tuple[dict, dict, dict]:
        """
        加载配置
        
        Returns:
            (server_config, model_config, agent_config)
        """
        agent_config = load_agent_config()
        
        # Server 配置 - 使用 lib 目录作为基础路径
        logging_cfg = agent_config.get("logging", {})
        server_config = {
            "log_dir": str(LIB_DIR / logging_cfg.get("log_dir", "logs/traces")),
            "image_dir": str(LIB_DIR / logging_cfg.get("image_dir", "logs/images")),
            "debug": logging_cfg.get("debug", False)
        }
        
        # 确保日志目录存在
        os.makedirs(server_config["log_dir"], exist_ok=True)
        os.makedirs(server_config["image_dir"], exist_ok=True)
        
        # 从 OneAgent 配置获取模型信息
        model_label = global_config.get(f"llm.functional_roles.{self.model_role}")
        if not model_label:
            model_label = "gelab-zero"  # 默认值
        
        api_base, api_key, model_name = global_config.get_model_config(model_label)
        
        agent_cfg = agent_config.get("agent", {})
        model_config = {
            "task_type": "parser_0922_summary",
            "model_config": {
                "model_name": model_name,
                "model_provider": "local",
                "args": {
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "frequency_penalty": 0.0,
                    "max_tokens": 4096,
                },
            },
            "max_steps": agent_cfg.get("max_steps", 50),
            "delay_after_capture": agent_cfg.get("delay_after_capture", 2),
        }
        
        return server_config, model_config, agent_config
    
    def _get_device_id(self, device_config: dict) -> Optional[str]:
        """根据配置获取设备 ID"""
        try:
            from .lib.copilot_front_end.mobile_action_helper import list_devices
            
            selection = device_config.get("selection", "first")
            
            if selection == "specify":
                return device_config.get("device_id")
            
            # 默认使用第一个设备
            devices = list_devices()
            if devices:
                return devices[0]
            return None
        except Exception as e:
            print(f"[GUIAutomationAgent] 获取设备列表失败: {e}")
            return None
    
    def _map_stop_reason(self, stop_reason: str, final_action: dict) -> tuple[str, str]:
        """
        将 gelab-zero 的 stop_reason 映射为 OneAgent 的 status 和 summary
        """
        if stop_reason == "TASK_COMPLETED_SUCCESSFULLY":
            return_value = final_action.get("agent_action", {}).get("return", "任务完成")
            return ("success", f"GUI 任务成功完成: {return_value}")
        
        elif stop_reason == "TASK_ABORTED_BY_AGENT":
            abort_reason = final_action.get("agent_action", {}).get("explain", "Agent 终止了任务")
            return ("failure", f"GUI 任务被终止: {abort_reason}")
        
        elif stop_reason == "INFO_ACTION_NEEDS_REPLY":
            question = final_action.get("agent_action", {}).get("value", "需要用户确认")
            return ("interrupted", f"GUI Agent 需要用户确认: {question}")
        
        elif stop_reason == "MAX_STEPS_REACHED":
            return ("failure", "GUI 任务未能在最大步数内完成")
        
        elif stop_reason == "MANUAL_STOP_SCREEN_OFF":
            return ("failure", "设备屏幕关闭，任务中断")
        
        else:
            return ("failure", f"未知终止原因: {stop_reason}")
    
    def _ensure_model_config(self, api_base: str, api_key: str):
        """确保 model_config.yaml 配置正确"""
        import yaml
        
        config_path = LIB_DIR / "model_config.yaml"
        
        # 读取现有配置
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}
        
        # 更新 local provider 配置
        config["local"] = {
            "api_base": api_base,
            "api_key": api_key
        }
        
        # 写回配置
        with open(config_path, "w") as f:
            yaml.dump(config, f)
    
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
        print("🤖 [GUIAutomationAgent] 启动 GUI 自动化任务")
        print(f"{'='*60}")
        print(f"📋 任务: {instruction}")
        
        # 1. 加载配置
        server_config, model_config, agent_config = self._load_config()
        
        # 2. 获取模型配置并更新 model_config.yaml
        model_label = global_config.get(f"llm.functional_roles.{self.model_role}") or "gelab-zero"
        api_base, api_key, model_name = global_config.get_model_config(model_label)
        print(f"🤖 模型: {model_name} ({api_base})")
        
        self._ensure_model_config(api_base, api_key)
        
        # 3. 检查设备连接
        device_config = agent_config.get("device", {})
        device_id = self._get_device_id(device_config)
        if not device_id:
            return "[FAILURE] 没有检测到已连接的安卓设备，请检查 ADB 连接"
        
        print(f"📱 设备: {device_id}")
        
        # 4. 导入本地 gelab-zero 组件
        try:
            from .lib.copilot_agent_server.local_server import LocalServer
            from .lib.copilot_agent_client.mcp_agent_loop import gui_agent_loop
        except ImportError as e:
            return f"[FAILURE] 无法导入 GUI 自动化组件: {e}"
        
        # 5. 执行任务
        try:
            server = LocalServer(server_config)
            
            agent_cfg = agent_config.get("agent", {})
            print("🚀 开始执行任务...")
            result = gui_agent_loop(
                agent_server=server,
                agent_loop_config=model_config,
                device_id=device_id,
                max_steps=agent_cfg.get("max_steps", 50),
                enable_intermediate_logs=False,
                enable_final_screenshot=False,
                reset_environment=agent_cfg.get("reset_environment", True),
                reflush_app=agent_cfg.get("reflush_app", True),
                reply_mode="pass_to_client",
                task=instruction,
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"[FAILURE] GUI 任务执行出错: {e}"
        
        # 6. 映射结果
        stop_reason = result.get("stop_reason", "UNKNOWN")
        final_action = result.get("final_action", {})
        session_id = result.get("session_id", "unknown")
        steps = result.get("local_step_idx", 0)
        
        status, summary = self._map_stop_reason(stop_reason, final_action)
        
        print(f"\n{'='*60}")
        emoji = {"success": "✅", "failure": "❌", "interrupted": "⏸️"}.get(status, "❓")
        print(f"{emoji} [GUIAutomationAgent] 任务结束")
        print(f"   状态: {status.upper()}")
        print(f"   步数: {steps}")
        print(f"   会话: {session_id}")
        print(f"{'='*60}\n")
        
        # 7. 返回格式化结果
        if status == "interrupted":
            return f"[INTERRUPTED] {summary}\n\nSession ID: {session_id}\n（如需继续任务，请提供回复并使用相同 session_id）"
        elif status == "success":
            return f"[SUCCESS] {summary}"
        else:
            return f"[FAILURE] {summary}"
