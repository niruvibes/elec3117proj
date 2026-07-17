from pathlib import Path
import sys

import pcbnew

from place_board import configure_routing_rules


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tmp/layout-analysis/project.placed.kicad_pcb"
OUTPUT = ROOT / "tmp/layout-analysis/project.placed.dsn"


def main() -> int:
    board = pcbnew.LoadBoard(str(INPUT))
    configure_routing_rules(board)
    if not pcbnew.ExportSpecctraDSN(board, str(OUTPUT)):
        raise RuntimeError("Specctra DSN export failed")
    print(f"Exported {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
