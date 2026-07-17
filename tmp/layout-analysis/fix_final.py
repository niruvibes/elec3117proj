from pathlib import Path
import sys

import pcbnew

from complete_routes import (
    B_LAYER,
    F_LAYER,
    add_track,
    commit_route,
    grid_index,
    obstacle_map,
    pt,
    route_astar,
    xy,
)


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tmp/layout-analysis/project.fresh-complete.kicad_pcb"
OUTPUT = ROOT / "tmp/layout-analysis/project.finalized.kicad_pcb"
STAGE = ROOT / "tmp/layout-analysis/project.fix-stage.kicad_pcb"


def move_via_and_anchors(
    board: pcbnew.BOARD,
    via: pcbnew.PCB_VIA,
    destination: tuple[float, float],
) -> None:
    old_position = via.GetPosition()
    new_position = pt(*destination)
    for track in board.GetTracks():
        if isinstance(track, pcbnew.PCB_VIA) or track.GetNetCode() != via.GetNetCode():
            continue
        if track.GetStart() == old_position:
            track.SetStart(new_position)
        if track.GetEnd() == old_position:
            track.SetEnd(new_position)
    via.SetPosition(new_position)


def route_to_target(
    board: pcbnew.BOARD,
    net_name: str,
    source: tuple[float, float],
    target: tuple[float, float],
    target_layer: int,
    start_layer: int = F_LAYER,
) -> None:
    net = board.FindNet(net_name)
    blocked, via_blocked = obstacle_map(board, net.GetNetCode())
    tx, ty = grid_index(*target)
    targets = {(tx, ty, target_layer): target}
    path, reached = route_astar(
        blocked,
        via_blocked,
        source,
        targets,
        relaxed_vias=False,
        start_layer=start_layer,
    )
    commit_route(board, net, path, source, reached)
    print(f"Bridged {net_name} with {len(path)} grid nodes", flush=True)


def main() -> int:
    board = pcbnew.LoadBoard(str(STAGE))
    d1_source = xy(board.FindFootprintByReference("U1").FindPadByNumber("26").GetPosition())
    d1_target = xy(board.FindFootprintByReference("D1").FindPadByNumber("2").GetPosition())
    d1_net = board.FindNet("Net-(D1-A)")

    d1_layer_change = (52.0, 84.0)
    add_track(board, d1_net, d1_source, d1_layer_change, F_LAYER)
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pt(*d1_layer_change))
    via.SetWidth(pcbnew.FromMM(0.40))
    via.SetDrill(pcbnew.FromMM(0.20))
    via.SetLayerPair(F_LAYER, B_LAYER)
    via.SetNet(d1_net)
    board.Add(via)
    route_to_target(
        board,
        "Net-(D1-A)",
        d1_layer_change,
        d1_target,
        F_LAYER,
        start_layer=B_LAYER,
    )

    # Join the local WLC1115 pin clusters to their already-routed main trees.
    route_to_target(board, "PVIN_0", (56.5, 80.6), (59.7837, 81.1282), F_LAYER)
    route_to_target(board, "/Q_COMP", (56.5, 81.4), (63.25, 107.3375), F_LAYER)

    pcbnew.SaveBoard(str(OUTPUT), board)
    print(f"Wrote {OUTPUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
