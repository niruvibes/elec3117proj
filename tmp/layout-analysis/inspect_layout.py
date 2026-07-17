import json
from collections import Counter
from pathlib import Path


root = Path(__file__).resolve().parents[2]
schematic = json.loads((root / "tmp/layout-analysis/schematic-before.json").read_text(encoding="utf-8"))
pcb = json.loads((root / "tmp/layout-analysis/pcb-before.json").read_text(encoding="utf-8"))

print("SCHEMATIC STATISTICS")
print(json.dumps(schematic.get("statistics", {}), indent=2))
print("PCB STATISTICS")
print(json.dumps(pcb.get("statistics", {}), indent=2))
print("BOARD OUTLINE")
print(json.dumps(pcb.get("board_outline", {}), indent=2))
print("TRACKS")
print(json.dumps({k: v for k, v in pcb.get("tracks", {}).items() if k not in {"segments", "arcs"}}, indent=2))
print("VIAS", len(pcb.get("vias", [])), "ZONES", len(pcb.get("zones", [])))

positions = Counter((round(fp.get("x", 0), 1), round(fp.get("y", 0), 1)) for fp in pcb.get("footprints", []))
print("MOST COMMON FOOTPRINT POSITIONS")
for pos, count in positions.most_common(10):
    print(pos, count)

print("FOOTPRINTS")
for fp in sorted(pcb.get("footprints", []), key=lambda item: item.get("reference", "")):
    print(
        f"{fp.get('reference','?'):6s} {fp.get('value','')[:28]:28s} "
        f"({fp.get('x',0):8.3f},{fp.get('y',0):8.3f}) a={fp.get('rotation', 0):6.1f} "
        f"layer={fp.get('layer','')} nets={','.join(fp.get('connected_nets', []))}"
    )

print("NET CLASSES")
print(json.dumps(pcb.get("net_classes", {}), indent=2))
print("HIGH-SEVERITY PCB FINDINGS")
for finding in pcb.get("findings", []):
    if finding.get("severity") in {"critical", "error", "high", "warning"}:
        print(f"{finding.get('severity')}: {finding.get('rule_id')} {finding.get('summary')}")
