from pathlib import Path
import sys

import pcbnew

from complete_routes import pt, xy


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tmp/layout-analysis/project.finalized.kicad_pcb"
OUTPUT = ROOT / "tmp/layout-analysis/project.finalized2.kicad_pcb"


def main() -> int:
    board = pcbnew.LoadBoard(str(INPUT))
    candidates = [
        item
        for item in board.GetTracks()
        if isinstance(item, pcbnew.PCB_VIA)
        and item.GetNetname() == "Net-(D2-A)"
        and abs(xy(item.GetPosition())[0] - 52.4) < 0.1
        and abs(xy(item.GetPosition())[1] - 85.0) < 0.1
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one relocated D2 via, found {len(candidates)}")
    via = candidates[0]
    old_position = via.GetPosition()
    new_position = pt(53.4, 85.0)
    for track in board.GetTracks():
        if isinstance(track, pcbnew.PCB_VIA) or track.GetNetCode() != via.GetNetCode():
            continue
        if track.GetStart() == old_position:
            track.SetStart(new_position)
        if track.GetEnd() == old_position:
            track.SetEnd(new_position)
    via.SetPosition(new_position)
    pcbnew.SaveBoard(str(OUTPUT), board)
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
