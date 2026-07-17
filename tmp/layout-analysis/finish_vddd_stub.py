from pathlib import Path
import sys

import pcbnew

from complete_routes import F_LAYER, xy
from fix_final import route_to_target


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tmp/layout-analysis/project.finalized3.kicad_pcb"
OUTPUT = ROOT / "tmp/layout-analysis/project.finalized4.kicad_pcb"


def main() -> int:
    board = pcbnew.LoadBoard(str(INPUT))
    source = xy(board.FindFootprintByReference("C56").FindPadByNumber("2").GetPosition())
    target = xy(board.FindFootprintByReference("C55").FindPadByNumber("2").GetPosition())
    route_to_target(board, "VDDD", source, target, F_LAYER)
    pcbnew.SaveBoard(str(OUTPUT), board)
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
