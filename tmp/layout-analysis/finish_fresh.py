from pathlib import Path
import sys

import pcbnew

from complete_routes import (
    B_LAYER,
    F_LAYER,
    add_track,
    commit_route,
    obstacle_map,
    route_astar,
    target_cells,
)


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tmp/layout-analysis/project.fresh-routed.kicad_pcb"
OUTPUT = ROOT / "tmp/layout-analysis/project.fresh-complete.kicad_pcb"


ROUTES = (
    ("Net-(D1-A)", "U1", "26", ((52.0, 84.0), (51.0, 84.0))),
    ("PVIN_0", "U1", "39", ((56.5, 80.6),)),
    ("PVIN_0", "U1", "38", ((56.5, 81.0),)),
    ("/Q_COMP", "U1", "37", ((56.5, 81.4),)),
    ("/Q_COMP", "R43", "2", ()),
    ("Net-(D5-C)", "R12", "2", ()),
    ("/IOUT_CSP_0", "TP18", "1", ()),
)


def main() -> int:
    board = pcbnew.LoadBoard(str(INPUT))
    for net_name, reference, pad_number, escape_points in ROUTES:
        net = board.FindNet(net_name)
        targets, source = target_cells(board, net.GetNetCode(), reference, pad_number)
        blocked, via_blocked = obstacle_map(board, net.GetNetCode())
        astar_source = source
        for escape_point in escape_points:
            add_track(board, net, astar_source, escape_point, F_LAYER)
            astar_source = escape_point
        path, target = route_astar(
            blocked,
            via_blocked,
            astar_source,
            targets,
            relaxed_vias=False,
        )
        commit_route(board, net, path, astar_source, target)
        print(
            f"Routed {net_name}: {reference}.{pad_number}, {len(path)} grid nodes",
            flush=True,
        )

    pcbnew.SaveBoard(str(OUTPUT), board)
    print(f"Wrote {OUTPUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
