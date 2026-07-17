from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from math import ceil, floor, hypot, sqrt
from pathlib import Path
import sys

import pcbnew


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tmp/layout-analysis/project.routed.kicad_pcb"
OUTPUT = ROOT / "tmp/layout-analysis/project.completed-signals.kicad_pcb"

X0, Y0, X1, Y1 = 20.5, 50.5, 89.5, 114.5
STEP = 0.1
F_LAYER = pcbnew.F_Cu
B_LAYER = pcbnew.B_Cu
LAYERS = (F_LAYER, B_LAYER)
CLEARANCE = 0.10
VIA_CLEARANCE = 0.10
ROUTE_WIDTH = 0.15
VIA_DIAMETER = 0.50
VIA_DRILL = 0.25


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def pt(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def xy(position: pcbnew.VECTOR2I) -> tuple[float, float]:
    return pcbnew.ToMM(position.x), pcbnew.ToMM(position.y)


def grid_xy(ix: int, iy: int) -> tuple[float, float]:
    return X0 + ix * STEP, Y0 + iy * STEP


NX = int(floor((X1 - X0) / STEP)) + 1
NY = int(floor((Y1 - Y0) / STEP)) + 1


def grid_index(x: float, y: float) -> tuple[int, int]:
    return (
        max(0, min(NX - 1, int(round((x - X0) / STEP)))),
        max(0, min(NY - 1, int(round((y - Y0) / STEP)))),
    )


def point_segment_distance(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom == 0:
        return hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    return hypot(px - (ax + t * dx), py - (ay + t * dy))


def add_circle(blocked: set[tuple[int, int]], x: float, y: float, radius: float) -> None:
    ix0, iy0 = grid_index(x - radius, y - radius)
    ix1, iy1 = grid_index(x + radius, y + radius)
    for ix in range(ix0, ix1 + 1):
        for iy in range(iy0, iy1 + 1):
            gx, gy = grid_xy(ix, iy)
            if hypot(gx - x, gy - y) <= radius:
                blocked.add((ix, iy))


def add_rect(
    blocked: set[tuple[int, int]], left: float, top: float, right: float, bottom: float
) -> None:
    ix0, iy0 = grid_index(left, top)
    ix1, iy1 = grid_index(right, bottom)
    for ix in range(min(ix0, ix1), max(ix0, ix1) + 1):
        for iy in range(min(iy0, iy1), max(iy0, iy1) + 1):
            gx, gy = grid_xy(ix, iy)
            if left <= gx <= right and top <= gy <= bottom:
                blocked.add((ix, iy))


def add_segment(
    blocked: set[tuple[int, int]],
    start: tuple[float, float],
    end: tuple[float, float],
    radius: float,
) -> None:
    ax, ay = start
    bx, by = end
    ix0, iy0 = grid_index(min(ax, bx) - radius, min(ay, by) - radius)
    ix1, iy1 = grid_index(max(ax, bx) + radius, max(ay, by) + radius)
    for ix in range(min(ix0, ix1), max(ix0, ix1) + 1):
        for iy in range(min(iy0, iy1), max(iy0, iy1) + 1):
            gx, gy = grid_xy(ix, iy)
            if point_segment_distance(gx, gy, ax, ay, bx, by) <= radius:
                blocked.add((ix, iy))


def obstacle_map(
    board: pcbnew.BOARD, net_code: int
) -> tuple[dict[int, set[tuple[int, int]]], dict[int, set[tuple[int, int]]]]:
    blocked = {F_LAYER: set(), B_LAYER: set()}
    via_blocked = {F_LAYER: set(), B_LAYER: set()}
    route_radius = ROUTE_WIDTH / 2 + CLEARANCE
    via_route_radius = VIA_DIAMETER / 2 + VIA_CLEARANCE

    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == net_code or pad.GetNetCode() == 0:
                continue
            bbox = pad.GetBoundingBox()
            left = pcbnew.ToMM(bbox.GetLeft()) - route_radius
            top = pcbnew.ToMM(bbox.GetTop()) - route_radius
            right = pcbnew.ToMM(bbox.GetRight()) + route_radius
            bottom = pcbnew.ToMM(bbox.GetBottom()) + route_radius
            for layer in LAYERS:
                if pad.IsOnLayer(layer):
                    add_rect(blocked[layer], left, top, right, bottom)
                    add_rect(
                        via_blocked[layer],
                        pcbnew.ToMM(bbox.GetLeft()) - via_route_radius,
                        pcbnew.ToMM(bbox.GetTop()) - via_route_radius,
                        pcbnew.ToMM(bbox.GetRight()) + via_route_radius,
                        pcbnew.ToMM(bbox.GetBottom()) + via_route_radius,
                    )

    for item in board.GetTracks():
        if item.GetNetCode() == net_code or item.GetNetCode() == 0:
            continue
        if isinstance(item, pcbnew.PCB_VIA):
            x, y = xy(item.GetPosition())
            radius = pcbnew.ToMM(item.GetWidth(F_LAYER)) / 2 + route_radius
            via_radius = pcbnew.ToMM(item.GetWidth(F_LAYER)) / 2 + via_route_radius
            for layer in LAYERS:
                add_circle(blocked[layer], x, y, radius)
                add_circle(via_blocked[layer], x, y, via_radius)
        else:
            layer = item.GetLayer()
            if layer not in LAYERS:
                continue
            radius = pcbnew.ToMM(item.GetWidth()) / 2 + route_radius
            via_radius = pcbnew.ToMM(item.GetWidth()) / 2 + via_route_radius
            add_segment(blocked[layer], xy(item.GetStart()), xy(item.GetEnd()), radius)
            add_segment(
                via_blocked[layer], xy(item.GetStart()), xy(item.GetEnd()), via_radius
            )

    return blocked, via_blocked


def target_cells(
    board: pcbnew.BOARD,
    net_code: int,
    source_fp: str,
    source_pad_number: str,
) -> tuple[dict[tuple[int, int, int], tuple[float, float]], tuple[float, float]]:
    targets: dict[tuple[int, int, int], tuple[float, float]] = {}
    source = board.FindFootprintByReference(source_fp).FindPadByNumber(source_pad_number)
    source_position = xy(source.GetPosition())

    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if (
                pad.GetNetCode() != net_code
                or pad.m_Uuid.AsString() == source.m_Uuid.AsString()
            ):
                continue
            px, py = xy(pad.GetPosition())
            ix, iy = grid_index(px, py)
            for layer in LAYERS:
                if pad.IsOnLayer(layer):
                    targets[(ix, iy, layer)] = (px, py)

    for item in board.GetTracks():
        if item.GetNetCode() != net_code:
            continue
        if isinstance(item, pcbnew.PCB_VIA):
            px, py = xy(item.GetPosition())
            ix, iy = grid_index(px, py)
            for layer in LAYERS:
                targets[(ix, iy, layer)] = (px, py)
            continue
        ax, ay = xy(item.GetStart())
        bx, by = xy(item.GetEnd())
        length = hypot(bx - ax, by - ay)
        samples = max(1, int(ceil(length / STEP)))
        for index in range(samples + 1):
            ratio = index / samples
            px = ax + ratio * (bx - ax)
            py = ay + ratio * (by - ay)
            ix, iy = grid_index(px, py)
            gx, gy = grid_xy(ix, iy)
            targets[(ix, iy, item.GetLayer())] = (gx, gy)

    return targets, source_position


def route_astar(
    blocked: dict[int, set[tuple[int, int]]],
    via_blocked: dict[int, set[tuple[int, int]]],
    source: tuple[float, float],
    targets: dict[tuple[int, int, int], tuple[float, float]],
    relaxed_vias: bool = False,
    start_layer: int = F_LAYER,
) -> tuple[list[tuple[int, int, int]], tuple[float, float]]:
    sx, sy = grid_index(*source)
    starts = [(sx, sy, start_layer)]
    target_keys = set(targets)

    for key in starts:
        blocked[key[2]].discard((key[0], key[1]))
    for ix, iy, layer in target_keys:
        blocked[layer].discard((ix, iy))

    target_xy = [(ix, iy) for ix, iy, _ in target_keys]
    target_min_x = min(ix for ix, _ in target_xy)
    target_max_x = max(ix for ix, _ in target_xy)
    target_min_y = min(iy for _, iy in target_xy)
    target_max_y = max(iy for _, iy in target_xy)

    def heuristic(ix: int, iy: int) -> float:
        # Distance to the target-set bounding box is a cheap admissible bound.
        dx = max(target_min_x - ix, 0, ix - target_max_x)
        dy = max(target_min_y - iy, 0, iy - target_max_y)
        return hypot(dx, dy)

    queue: list[tuple[float, float, tuple[int, int, int]]] = []
    came_from: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    cost: dict[tuple[int, int, int], float] = {}
    for start in starts:
        cost[start] = 0.0
        heappush(queue, (heuristic(start[0], start[1]), 0.0, start))

    directions = (
        (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
        (-1, -1, sqrt(2)), (-1, 1, sqrt(2)), (1, -1, sqrt(2)), (1, 1, sqrt(2)),
    )

    found: tuple[int, int, int] | None = None
    while queue:
        _, current_cost, current = heappop(queue)
        if current_cost != cost.get(current):
            continue
        if current in target_keys:
            found = current
            break
        ix, iy, layer = current
        for dx, dy, move_cost in directions:
            nx, ny = ix + dx, iy + dy
            if not (0 <= nx < NX and 0 <= ny < NY):
                continue
            if (nx, ny) in blocked[layer]:
                continue
            nxt = (nx, ny, layer)
            new_cost = current_cost + move_cost
            if new_cost < cost.get(nxt, float("inf")):
                cost[nxt] = new_cost
                came_from[nxt] = current
                heappush(queue, (new_cost + heuristic(nx, ny), new_cost, nxt))

        other_layer = B_LAYER if layer == F_LAYER else F_LAYER
        via_site_clear = (
            (ix, iy) not in blocked[other_layer]
            and (
                relaxed_vias
                or (
                    (ix, iy) not in via_blocked[layer]
                    and (ix, iy) not in via_blocked[other_layer]
                )
            )
        )
        if via_site_clear:
            nxt = (ix, iy, other_layer)
            new_cost = current_cost + 8.0
            if new_cost < cost.get(nxt, float("inf")):
                cost[nxt] = new_cost
                came_from[nxt] = current
                heappush(queue, (new_cost + heuristic(ix, iy), new_cost, nxt))

    if found is None:
        raise RuntimeError(f"No route found from {source} to {len(targets)} target cells")

    path = [found]
    while path[-1] not in starts:
        path.append(came_from[path[-1]])
    path.reverse()
    return path, targets[found]


def add_track(
    board: pcbnew.BOARD,
    net: pcbnew.NETINFO_ITEM,
    start: tuple[float, float],
    end: tuple[float, float],
    layer: int,
) -> None:
    if hypot(end[0] - start[0], end[1] - start[1]) < 0.01:
        return
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(pt(*start))
    track.SetEnd(pt(*end))
    track.SetWidth(mm(ROUTE_WIDTH))
    track.SetLayer(layer)
    track.SetNet(net)
    board.Add(track)


def commit_route(
    board: pcbnew.BOARD,
    net: pcbnew.NETINFO_ITEM,
    path: list[tuple[int, int, int]],
    source: tuple[float, float],
    target: tuple[float, float],
) -> None:
    points = [(grid_xy(ix, iy), layer) for ix, iy, layer in path]
    add_track(board, net, source, points[0][0], F_LAYER)

    segment_start = points[0][0]
    segment_layer = points[0][1]
    previous = points[0][0]
    previous_direction: tuple[int, int] | None = None
    for index in range(1, len(points)):
        current, layer = points[index]
        if layer != segment_layer:
            add_track(board, net, segment_start, previous, segment_layer)
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pt(*previous))
            via.SetWidth(mm(VIA_DIAMETER))
            via.SetDrill(mm(VIA_DRILL))
            via.SetLayerPair(F_LAYER, B_LAYER)
            via.SetNet(net)
            board.Add(via)
            segment_start = previous
            segment_layer = layer
            previous_direction = None
        direction = (
            int(round((current[0] - previous[0]) / STEP)),
            int(round((current[1] - previous[1]) / STEP)),
        )
        if previous_direction is not None and direction != previous_direction:
            add_track(board, net, segment_start, previous, segment_layer)
            segment_start = previous
        previous_direction = direction
        previous = current
    add_track(board, net, segment_start, previous, segment_layer)
    add_track(board, net, previous, target, segment_layer)


ROUTES = (
    ("/IIN_CSN_0", "U1", "66"),
    ("PVIN_0", "U1", "65"),
    ("/ASK_P", "U1", "41"),
    ("Net-(J3-Pin_1)", "U1", "58"),
    ("/IOUT_CSN_0", "U1", "46"),
    ("/HG2_1", "U1", "44"),
    ("/LG1_0", "U1", "2"),
    ("/LG1_1", "U1", "50"),
    ("VDDD", "U1", "48"),
    ("VDDD", "U1", "4"),
    ("/OPTIGA_I2C_SCL", "U1", "30"),
    ("Net-(D1-A)", "U1", "26"),
    ("Net-(D2-A)", "U1", "27"),
)

ESCAPE_PATHS = {
    "/HG2_1": ((56.5, 78.6),),
    "/IIN_CSN_0": ((49.6, 74.5),),
    "/IOUT_CSN_0": ((56.5, 77.8),),
    "PVIN_0": ((50.0, 74.5), (51.0, 74.5)),
}


def neck_down_controller_escapes(board: pcbnew.BOARD) -> None:
    """Keep the 0.4 mm-pitch QFN fan-out narrow until clear of adjacent pins."""
    via_moves = {
        "/SW2_1": (58.5, 78.2),
        "/SW1_0": (45.5, 75.8),
        "/SW1_1": (59.5, 75.8),
    }
    for item in list(board.GetTracks()):
        if not isinstance(item, pcbnew.PCB_VIA) or item.GetNetname() not in via_moves:
            continue
        old_x, old_y = xy(item.GetPosition())
        if not (45.0 <= old_x <= 59.0 and 74.0 <= old_y <= 79.0):
            continue
        new_x, new_y = via_moves[item.GetNetname()]
        old_position = item.GetPosition()
        new_position = pt(new_x, new_y)
        for track in board.GetTracks():
            if isinstance(track, pcbnew.PCB_VIA) or track.GetNetCode() != item.GetNetCode():
                continue
            if track.GetStart() == old_position:
                track.SetStart(new_position)
            if track.GetEnd() == old_position:
                track.SetEnd(new_position)
        item.SetPosition(new_position)

    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA):
            continue
        start_x, start_y = xy(item.GetStart())
        end_x, end_y = xy(item.GetEnd())
        near_u1 = any(
            46.0 <= x <= 58.0 and 73.0 <= y <= 85.0
            for x, y in ((start_x, start_y), (end_x, end_y))
        )
        if near_u1 and pcbnew.ToMM(item.GetWidth()) > ROUTE_WIDTH:
            item.SetWidth(mm(ROUTE_WIDTH))


def relocate_aux_connector(board: pcbnew.BOARD) -> None:
    # J3 is a single low-speed auxiliary pin.  The original lower-right site
    # forced its route through the inverter and sensing channels; the free top
    # edge is both accessible and electrically quieter.
    board.FindFootprintByReference("J3").SetPosition(pt(72.0, 52.5))


def main() -> int:
    board = pcbnew.LoadBoard(str(INPUT))
    relocate_aux_connector(board)
    neck_down_controller_escapes(board)
    for net_name, reference, pad_number in ROUTES:
        net = board.FindNet(net_name)
        if net is None:
            raise RuntimeError(f"Missing net {net_name}")
        targets, source = target_cells(board, net.GetNetCode(), reference, pad_number)
        blocked, via_blocked = obstacle_map(board, net.GetNetCode())
        astar_source = source
        for escape_point in ESCAPE_PATHS.get(net_name, ()): 
            add_track(board, net, astar_source, escape_point, F_LAYER)
            astar_source = escape_point
        path, target = route_astar(
            blocked,
            via_blocked,
            astar_source,
            targets,
            relaxed_vias=(
                net_name in {"/ASK_P", "/IOUT_CSN_0", "Net-(J3-Pin_1)"}
            ),
        )
        commit_route(board, net, path, astar_source, target)
        print(
            f"Routed {net_name}: {reference}.{pad_number}, {len(path)} grid nodes",
            flush=True,
        )

    bst_net = board.FindNet("/BST2_1")
    bst_source = xy(board.FindFootprintByReference("U1").FindPadByNumber("43").GetPosition())
    bst_target = xy(board.FindFootprintByReference("C39").FindPadByNumber("1").GetPosition())
    add_track(board, bst_net, bst_source, (56.5, 79.0), F_LAYER)
    add_track(board, bst_net, (56.5, 79.0), (58.5, 78.0), F_LAYER)
    add_track(board, bst_net, (58.5, 78.0), bst_target, F_LAYER)
    print("Routed /BST2_1 with a direct local bootstrap escape", flush=True)

    pcbnew.SaveBoard(str(OUTPUT), board)
    print(f"Wrote {OUTPUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
