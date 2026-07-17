from pathlib import Path
import sys

import pcbnew


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tmp/layout-analysis/project.placed.kicad_pcb"
SESSION = ROOT / "tmp/layout-analysis/project.fresh-relaxed.ses"
OUTPUT = ROOT / "tmp/layout-analysis/project.fresh-routed.kicad_pcb"


def main() -> int:
    board = pcbnew.LoadBoard(str(INPUT))
    if not pcbnew.ImportSpecctraSES(board, str(SESSION)):
        raise RuntimeError("Specctra session import failed")
    pcbnew.SaveBoard(str(OUTPUT), board)
    print(f"Imported session and wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
