
import sys
import os
sys.path.insert(0, os.path.abspath("/home/tcmofashi/proj/OneAgent"))

from src.capabilities.agents.autoglm_gui_agent.phone_agent.adb.input import type_text, detect_and_set_adb_keyboard

# Assuming device is available or default
# The user's device ID from previous logs: QV7127F73E
DEVICE_ID = "QV7127F73E"

def test_input():
    print(f"Detecting keyboard on {DEVICE_ID}...")
    original_ime = detect_and_set_adb_keyboard(DEVICE_ID)
    print(f"Original IME: {original_ime}")
    
    print("Typing 'Hello World'...")
    type_text("Hello World", DEVICE_ID)
    print("Done.")

if __name__ == "__main__":
    test_input()
