
import sys
from pathlib import Path

# Add path
sys.path.insert(0, "/home/tcmofashi/proj/OneAgent/src/capabilities/agents/autoglm_gui_agent")
sys.path.insert(0, "/home/tcmofashi/proj/OneAgent")

try:
    from phone_agent.adb import list_devices
    print("Import successful")
    devices = list_devices()
    print(f"Devices: {devices}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
