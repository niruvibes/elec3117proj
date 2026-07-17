from pathlib import Path
import sys

import pcbnew


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tmp/layout-analysis/project.finalized4.kicad_pcb"
OUTPUT = ROOT / "tmp/layout-analysis/project.finalized5.kicad_pcb"
UUID = "fd6b165d-3ef9-4a19-a88c-6f0aefd40ec5"


def main() -> int:
    board = pcbnew.LoadBoard(str(INPUT))
    matches = [item for item in board.GetTracks() if item.m_Uuid.AsString() == UUID]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one dangling VDDD track, found {len(matches)}")
    board.Remove(matches[0])
    pcbnew.SaveBoard(str(OUTPUT), board)
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
