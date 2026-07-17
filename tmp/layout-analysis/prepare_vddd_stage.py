from pathlib import Path
import sys

import pcbnew

from complete_routes import pt, xy


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tmp/layout-analysis/project.finalized.kicad_pcb"
OUTPUT = ROOT / "tmp/layout-analysis/project.vddd-stage.kicad_pcb"


def rounded_segment(track: pcbnew.PCB_TRACK) -> frozenset[tuple[float, float]]:
    return frozenset(
        (
            (round(xy(track.GetStart())[0], 4), round(xy(track.GetStart())[1], 4)),
            (round(xy(track.GetEnd())[0], 4), round(xy(track.GetEnd())[1], 4)),
        )
    )


def main() -> int:
    board = pcbnew.LoadBoard(str(INPUT))
    d2_vias = [
        item
        for item in board.GetTracks()
        if isinstance(item, pcbnew.PCB_VIA)
        and item.GetNetname() == "Net-(D2-A)"
        and abs(xy(item.GetPosition())[0] - 52.4) < 0.1
        and abs(xy(item.GetPosition())[1] - 85.0) < 0.1
    ]
    if len(d2_vias) != 1:
        raise RuntimeError(f"Expected one D2 via, found {len(d2_vias)}")
    d2_via = d2_vias[0]
    old_position = d2_via.GetPosition()
    new_position = pt(52.4, 84.5)
    for track in board.GetTracks():
        if isinstance(track, pcbnew.PCB_VIA) or track.GetNetCode() != d2_via.GetNetCode():
            continue
        if track.GetStart() == old_position:
            track.SetStart(new_position)
        if track.GetEnd() == old_position:
            track.SetEnd(new_position)
    d2_via.SetPosition(new_position)
    d2_via.SetWidth(pcbnew.FromMM(0.40))
    d2_via.SetDrill(pcbnew.FromMM(0.20))

    local_vddd_segments = {
        frozenset(((51.6, 82.8965), (51.6, 83.4772))),
        frozenset(((51.6, 83.4772), (51.6, 84.547))),
        frozenset(((51.6, 84.547), (52.8947, 84.547))),
        frozenset(((52.8947, 84.547), (53.5977, 85.25))),
    }
    removed = 0
    for item in list(board.GetTracks()):
        if (
            not isinstance(item, pcbnew.PCB_VIA)
            and item.GetNetname() == "VDDD"
            and rounded_segment(item) in local_vddd_segments
        ):
            board.Remove(item)
            removed += 1
    if removed != 4:
        raise RuntimeError(f"Expected to remove 4 VDDD escape segments, removed {removed}")

    pcbnew.SaveBoard(str(OUTPUT), board)
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
