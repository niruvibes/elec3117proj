import json
from pathlib import Path


root = Path(__file__).resolve().parents[2]
data = json.loads((root / "tmp/layout-analysis/schematic-before.json").read_text(encoding="utf-8"))

keys = [
    "GND", "PVIN_0", "VDDD", "VBB", "VBUS", "Vin", "SW1_0",
    "IOUT_CSP_0", "IOUT_CSN_0", "IIN_CSN_0", "SW1_1", "SW2_1",
    "COIL_SNS", "HG1_0", "LG1_0", "HG2_1", "LG2_1", "HG1_1",
    "LG1_1", "CSPO_0", "CSNO_0", "ASK_P", "ASK_N", "ASK_I_P",
    "ASK_I_N", "Q_COMP",
]

for key in keys:
    for name, net in data["nets"].items():
        normalized = name.strip("/").upper()
        if normalized == key.upper() or normalized.endswith(key.upper()):
            pins = ", ".join(
                f"{pin['component']}.{pin['pin_number']}({pin.get('pin_name', '')})"
                for pin in net.get("pins", [])
            )
            print(f"{name} => {pins}")
