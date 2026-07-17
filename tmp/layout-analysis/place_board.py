from pathlib import Path
import sys

import pcbnew


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "project.kicad_pcb"
OUTPUT = ROOT / "tmp/layout-analysis/project.placed.kicad_pcb"

BOARD_X0 = 20.0
BOARD_Y0 = 50.0
BOARD_X1 = 90.0
BOARD_Y1 = 115.0


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def add_outline_segment(board: pcbnew.BOARD, start: tuple[float, float], end: tuple[float, float]) -> None:
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
    shape.SetStart(point(*start))
    shape.SetEnd(point(*end))
    shape.SetLayer(pcbnew.Edge_Cuts)
    shape.SetWidth(mm(0.05))
    board.Add(shape)


def add_missing_l1(board: pcbnew.BOARD) -> None:
    if any(fp.GetReference() == "L1" for fp in board.GetFootprints()):
        return

    library = ROOT / "components/PA4342.682NLT/PA4342.682NLT.pretty"
    footprint = pcbnew.FootprintLoad(str(library), "Yageo_Pulse_PA4342_10.3x11.5mm")
    if footprint is None:
        raise RuntimeError("Unable to load the PA4342.682NLT footprint")

    footprint.SetReference("L1")
    footprint.SetValue("PA4342.682NLT")
    footprint.SetPath(pcbnew.KIID_PATH("/33a823af-4429-4071-b4e7-afb3002c718c"))
    footprint.SetSheetname("/")
    footprint.SetSheetfile("project.kicad_sch")
    board.Add(footprint)

    net_map = {"1": "/SW1_0", "2": "/IOUT_CSP_0"}
    for pad in footprint.Pads():
        net = board.FindNet(net_map[pad.GetNumber()])
        if net is None:
            raise RuntimeError(f"Unable to find net {net_map[pad.GetNumber()]} for L1")
        pad.SetNet(net)


def configure_routing_rules(board: pcbnew.BOARD) -> None:
    """Install manufacturable fine-pitch rules and guideline-aware route classes.

    Power nets use a 0.5 mm escape width here so the router can reach the
    controller pins.  The high-current portions are widened to the guideline
    widths after the escape routing is complete.
    """
    settings = board.GetDesignSettings()
    settings.m_MinClearance = mm(0.10)
    settings.m_TrackMinWidth = mm(0.15)
    settings.m_HoleClearance = mm(0.20)
    settings.m_CopperEdgeClearance = mm(0.50)
    settings.m_ViasMinSize = mm(0.50)
    settings.m_MinThroughDrill = mm(0.25)

    net_settings = settings.m_NetSettings
    default = net_settings.GetDefaultNetclass()
    default.SetClearance(mm(0.10))
    default.SetTrackWidth(mm(0.20))
    default.SetViaDiameter(mm(0.60))
    default.SetViaDrill(mm(0.30))
    net_settings.SetDefaultNetclass(default)

    classes = {
        "Ground": (0.25, 0.10, 0.80, 0.40),
        "PowerEscape": (0.50, 0.15, 0.80, 0.40),
        "Supply": (0.75, 0.15, 0.80, 0.40),
        "GateDrive": (0.50, 0.15, 0.70, 0.35),
        "KelvinSense": (0.15, 0.10, 0.60, 0.30),
    }
    for name, (width, clearance, via, drill) in classes.items():
        netclass = pcbnew.NETCLASS(name)
        netclass.SetTrackWidth(mm(width))
        netclass.SetClearance(mm(clearance))
        netclass.SetViaDiameter(mm(via))
        netclass.SetViaDrill(mm(drill))
        net_settings.SetNetclass(name, netclass)

    assignments = {
        "GND": "Ground",
        "VDDD": "Supply",
        "/IOUT_CSP_0": "PowerEscape",
        "/IOUT_CSN_0": "PowerEscape",
        "/IIN_CSN_0": "PowerEscape",
        "/SW1_0": "PowerEscape",
        "/SW1_1": "PowerEscape",
        "/SW2_1": "PowerEscape",
        "PVIN_0": "PowerEscape",
        "/HG1_0": "GateDrive",
        "/LG1_0": "GateDrive",
        "/HG2_1": "GateDrive",
        "/LG2_1": "GateDrive",
        "/HG1_1": "GateDrive",
        "/LG1_1": "GateDrive",
        "/BST1_0": "GateDrive",
        "/BST2_1": "GateDrive",
        "/BST1_1": "GateDrive",
        "/ASK_P": "KelvinSense",
        "/ASK_N": "KelvinSense",
        "/ASK_I_P": "KelvinSense",
        "/ASK_I_N": "KelvinSense",
    }
    for net_name, class_name in assignments.items():
        net_settings.SetNetclassPatternAssignment(net_name, class_name)
    net_settings.ClearAllCaches()
    net_settings.RecomputeEffectiveNetclasses()


PLACEMENT: dict[str, tuple[float, float, float]] = {
    # Main ICs, connectors, magnetics, and power devices.
    "U1": (52.0, 79.0, 0),
    "U2": (52.0, 91.0, 0),
    "U3": (34.0, 94.0, 0),
    "Q1": (24.5, 68.0, 270),
    "Q2": (37.5, 57.5, 270),
    "Q3": (37.5, 62.0, 270),
    "Q4": (78.5, 67.0, 270),
    "Q5": (78.5, 72.0, 270),
    "Q6": (78.5, 79.0, 270),
    "Q7": (78.5, 84.0, 270),
    "Q8": (69.0, 109.0, 0),
    "L1": (49.5, 59.5, 90),
    "L2": (84.3, 101.5, 90),
    "J1": (23.0, 108.5, 0),
    "J3": (88.0, 110.0, 0),
    "J4": (49.0, 112.0, 90),

    # Buck power stage and current shunts.
    "C20": (28.5, 53.0, 0),
    "C21": (31.5, 53.0, 0),
    "R22": (33.0, 56.0, 90),
    "C27": (30.5, 56.5, 0),
    "C28": (30.5, 59.0, 0),
    "C23": (58.0, 52.5, 0),
    "C24": (61.0, 52.5, 0),
    "C25": (58.0, 66.5, 0),
    "C26": (61.0, 66.5, 0),
    "R23": (59.0, 59.5, 0),
    "C29": (69.0, 64.0, 0),
    "C30": (72.0, 64.0, 0),
    "C31": (69.0, 78.0, 0),
    "C32": (72.0, 78.0, 0),

    # WLC1115 close-in support ring.
    "D8": (43.0, 70.5, 0),
    "D9": (43.0, 75.0, 0),
    "C22": (47.0, 72.2, 0),
    "R25": (47.0, 69.5, 0),
    "C42": (50.0, 69.5, 0),
    "C43": (50.0, 72.2, 0),
    "C1": (53.0, 72.2, 0),
    "C44": (56.0, 69.5, 0),
    "C45": (56.0, 72.2, 0),
    "R26": (59.0, 69.5, 0),
    "C40": (59.0, 72.2, 0),
    "D11": (63.0, 71.5, 90),
    "C39": (59.0, 77.0, 90),
    "D10": (62.0, 77.0, 90),
    "C53": (59.0, 81.0, 90),
    "C54": (62.0, 81.0, 90),
    "C9": (59.0, 84.5, 0),
    "R10": (62.0, 84.5, 0),
    "C55": (49.0, 86.0, 0),
    "C56": (52.0, 86.0, 0),
    "C57": (55.0, 86.0, 0),
    "C58": (58.0, 86.0, 0),
    "C4": (40.0, 78.0, 90),
    "R1": (42.0, 78.0, 90),
    "C3": (44.0, 78.0, 90),
    "R8": (40.0, 73.5, 90),
    "R9": (40.0, 76.0, 90),
    "R27": (42.0, 82.0, 0),
    "R28": (42.0, 84.0, 0),
    "C2": (45.0, 83.0, 90),
    "R29": (42.0, 86.0, 0),
    "R30": (42.0, 88.0, 0),
    "C7": (45.0, 86.0, 0),
    "C8": (45.0, 88.0, 0),

    # Inverter power components, ZVS networks, and resonant bank.
    "C33": (83.0, 73.0, 90),
    "R3": (86.0, 73.0, 90),
    "C41": (83.0, 85.0, 90),
    "R24": (86.0, 85.0, 90),
    "C34": (77.0, 92.0, 0),
    "C35": (77.0, 95.0, 0),
    "C36": (77.0, 98.0, 0),
    "C37": (77.0, 101.0, 0),
    "C38": (77.0, 104.0, 0),

    # LMV358 ASK demodulator and gain/comparator network.
    "D5": (25.5, 90.0, 0),
    "D6": (25.5, 96.0, 0),
    "R12": (29.0, 87.5, 0),
    "R13": (30.0, 91.0, 90),
    "R14": (30.0, 96.0, 90),
    "R15": (38.0, 96.0, 90),
    "R16": (35.0, 89.0, 0),
    "R17": (35.0, 99.0, 0),
    "R18": (40.0, 99.0, 90),
    "C13": (40.0, 96.0, 90),
    "C14": (38.0, 89.0, 0),
    "C15": (41.0, 89.0, 0),
    "C16": (38.0, 99.0, 90),
    "C10": (27.0, 102.0, 0),
    "C11": (30.0, 102.0, 0),
    "C12": (33.0, 102.0, 0),
    "R11": (36.0, 102.0, 0),

    # ASK current/voltage filter next to the controller but outside the power path.
    "C46": (61.0, 88.0, 0),
    "C47": (64.0, 88.0, 0),
    "C48": (67.0, 88.0, 0),
    "R32": (61.0, 91.0, 0),
    "R34": (64.0, 91.0, 0),
    "R33": (67.0, 91.0, 0),
    "R35": (61.0, 94.0, 0),
    "R36": (67.0, 94.0, 0),
    "C49": (61.0, 97.0, 0),
    "C50": (64.0, 97.0, 0),
    "R37": (67.0, 97.0, 0),
    "C51": (61.0, 100.0, 0),
    "R38": (67.0, 100.0, 0),

    # Secure element, digital pull-ups, programming, LEDs, and auxiliary I/O.
    "C17": (49.0, 89.0, 0),
    "C18": (55.0, 89.0, 0),
    "C5": (49.0, 94.0, 0),
    "C6": (55.0, 94.0, 0),
    "R19": (58.0, 89.0, 90),
    "R20": (58.0, 92.0, 90),
    "R21": (58.0, 95.0, 90),
    "R2": (54.0, 105.0, 0),
    "R31": (57.0, 105.0, 0),
    "D7": (53.0, 108.0, 0),
    "C19": (56.0, 108.0, 0),
    "R4": (28.0, 106.0, 0),
    "R5": (28.0, 109.0, 0),
    "D1": (32.0, 109.0, 0),
    "R6": (35.0, 109.0, 0),
    "D2": (38.0, 109.0, 0),
    "R7": (41.0, 109.0, 0),

    # Q-factor measurement and clamp network.
    "C52": (72.0, 103.0, 90),
    "R39": (72.0, 106.0, 90),
    "D12": (68.0, 104.0, 90),
    "R40": (65.0, 103.0, 90),
    "D13": (62.0, 103.0, 90),
    "R41": (65.0, 106.0, 90),
    "R42": (62.0, 106.0, 90),
    "R43": (64.0, 109.0, 90),

    # Accessible edge test points.
    "TP5": (21.5, 54.0, 0),
    "TP6": (21.5, 58.0, 0),
    "TP7": (21.5, 62.0, 0),
    "TP8": (21.5, 66.0, 0),
    "TP1": (21.5, 84.0, 0),
    "TP2": (21.5, 88.0, 0),
    "TP3": (21.5, 92.0, 0),
    "TP4": (21.5, 96.0, 0),
    "TP21": (21.5, 100.0, 0),
    "TP22": (21.5, 104.0, 0),
    "TP16": (21.5, 108.0, 0),
    "TP9": (88.5, 58.0, 0),
    "TP10": (88.5, 62.0, 0),
    "TP14": (88.5, 66.0, 0),
    "TP12": (88.5, 70.0, 0),
    "TP13": (88.5, 74.0, 0),
    "TP15": (88.5, 78.0, 0),
    "TP18": (88.5, 82.0, 0),
    "TP17": (88.5, 86.0, 0),
    "TP11": (88.5, 92.0, 0),
    "TP19": (74.0, 112.0, 0),
    "TP20": (82.0, 112.0, 0),
}


FIXED_REFERENCES = {
    "U1", "U2", "U3", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7",
    "Q8", "L1", "L2", "J1", "J3", "J4", "R22", "R23", "TP19", "TP20",
}


def courtyard_bbox_mm(fp: pcbnew.FOOTPRINT) -> tuple[float, float, float, float] | None:
    try:
        fp.BuildCourtyardCaches()
        poly = fp.GetCourtyard(pcbnew.F_Cu)
        if poly.OutlineCount() == 0:
            return None
        bbox = poly.BBox()
        return (
            pcbnew.ToMM(bbox.GetLeft()),
            pcbnew.ToMM(bbox.GetTop()),
            pcbnew.ToMM(bbox.GetRight()),
            pcbnew.ToMM(bbox.GetBottom()),
        )
    except Exception:
        return None


def boxes_overlap(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
    gap: float,
) -> bool:
    return not (
        first[2] + gap <= second[0]
        or second[2] + gap <= first[0]
        or first[3] + gap <= second[1]
        or second[3] + gap <= first[1]
    )


def spiral_offsets(step: float = 0.25, max_radius: float = 24.0):
    yield 0.0, 0.0
    max_ring = int(max_radius / step)
    for ring in range(1, max_ring + 1):
        low = -ring
        high = ring
        for x_index in range(low, high + 1):
            yield x_index * step, low * step
            yield x_index * step, high * step
        for y_index in range(low + 1, high):
            yield low * step, y_index * step
            yield high * step, y_index * step


def legalize_placement(footprints: dict[str, pcbnew.FOOTPRINT]) -> None:
    margin = 0.30
    gap = 0.18
    placed_boxes: dict[str, tuple[float, float, float, float]] = {}

    # Power devices, main ICs, magnetics, shunts, and connectors retain the
    # exact intended topology. Validate that those fixed anchors do not clash.
    for reference in FIXED_REFERENCES:
        box = courtyard_bbox_mm(footprints[reference])
        if box is None:
            continue
        for other_ref, other_box in placed_boxes.items():
            if boxes_overlap(box, other_box, gap):
                raise RuntimeError(f"Fixed placement overlap: {reference} / {other_ref}")
        placed_boxes[reference] = box

    # Keep insertion order: close-in support parts are legalized before less
    # critical filters and test points, so the former remain nearest U1.
    for reference in PLACEMENT:
        if reference in FIXED_REFERENCES:
            continue
        fp = footprints[reference]
        desired_x, desired_y, _ = PLACEMENT[reference]
        desired_box = courtyard_bbox_mm(fp)
        if desired_box is None:
            continue
        relative_box = (
            desired_box[0] - desired_x,
            desired_box[1] - desired_y,
            desired_box[2] - desired_x,
            desired_box[3] - desired_y,
        )

        for dx, dy in spiral_offsets():
            candidate_x = desired_x + dx
            candidate_y = desired_y + dy
            candidate = (
                candidate_x + relative_box[0],
                candidate_y + relative_box[1],
                candidate_x + relative_box[2],
                candidate_y + relative_box[3],
            )
            if (
                candidate[0] < BOARD_X0 + margin
                or candidate[1] < BOARD_Y0 + margin
                or candidate[2] > BOARD_X1 - margin
                or candidate[3] > BOARD_Y1 - margin
            ):
                continue
            if any(boxes_overlap(candidate, box, gap) for box in placed_boxes.values()):
                continue

            fp.Move(point(candidate_x - desired_x, candidate_y - desired_y))
            fp.BuildCourtyardCaches()
            placed_boxes[reference] = candidate
            break
        else:
            raise RuntimeError(f"No legal placement site found for {reference}")


def main() -> int:
    board = pcbnew.LoadBoard(str(INPUT))
    add_missing_l1(board)
    configure_routing_rules(board)
    footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}

    missing = sorted(set(footprints) - set(PLACEMENT))
    extra = sorted(set(PLACEMENT) - set(footprints))
    if missing or extra:
        raise RuntimeError(f"Placement coverage mismatch. Unplaced={missing}; unknown={extra}")

    for reference, (x, y, angle) in PLACEMENT.items():
        fp = footprints[reference]
        fp.SetPosition(point(x, y))
        fp.SetOrientationDegrees(angle)
        try:
            fp.GetField("Value").SetVisible(False)
            ref_field = fp.GetField("Reference")
            ref_field.SetVisible(False)
            ref_field.SetTextSize(point(0.8, 0.8))
            ref_field.SetTextThickness(mm(0.10))
        except Exception:
            pass

    legalize_placement(footprints)

    # Start routing from a clean board after placement is finalized. Removing
    # owned board items earlier invalidates some KiCad 10 SWIG child proxies.
    for item in list(board.GetTracks()):
        board.Remove(item)
    for zone in list(board.Zones()):
        board.Remove(zone)
    board.RemoveAllItemsOnLayer(pcbnew.Edge_Cuts)

    add_outline_segment(board, (BOARD_X0, BOARD_Y0), (BOARD_X1, BOARD_Y0))
    add_outline_segment(board, (BOARD_X1, BOARD_Y0), (BOARD_X1, BOARD_Y1))
    add_outline_segment(board, (BOARD_X1, BOARD_Y1), (BOARD_X0, BOARD_Y1))
    add_outline_segment(board, (BOARD_X0, BOARD_Y1), (BOARD_X0, BOARD_Y0))

    pcbnew.SaveBoard(str(OUTPUT), board)
    print(f"Placed {len(footprints)} footprints and wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
