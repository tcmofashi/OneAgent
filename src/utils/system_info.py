"""
系统信息工具
获取运行环境的基础信息，包括系统、IP、主机名等
"""

import platform
import socket
from typing import Dict, Any


def get_system_info() -> Dict[str, Any]:
    """
    获取系统信息

    Returns:
        {
            "hostname": str,
            "platform": str,
            "system": str,
            "release": str,
            "version": str,
            "machine": str,
            "processor": str,
            "python_version": str,
            "ip_address": str,
        }
    """
    info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }

    try:
        ip = get_local_ip()
        info["ip_address"] = ip
    except Exception:
        info["ip_address"] = "unknown"

    return info


def get_local_ip() -> str:
    """
    获取本机 IP 地址

    Returns:
        本机 IP 地址
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def format_system_info_for_description() -> str:
    """
    格式化系统信息为描述字符串

    Returns:
        格式化的系统信息描述
    """
    info = get_system_info()
    return (
        f"Host: {info['hostname']} ({info['ip_address']})\n"
        f"System: {info['system']} {info['release']} ({info['machine']})\n"
        f"Platform: {info['platform']}\n"
        f"Python: {info['python_version']}"
    )
