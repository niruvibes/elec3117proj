from pathlib import Path
import sys

import pcbnew

from complete_routes import F_LAYER, B_LAYER, pt


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tmp/layout-analysis/project.finalized5.kicad_pcb"
OUTPUT = ROOT / "tmp/layout-analysis/project.guideline.kicad_pcb"


def add_zone(
    board: pcbnew.BOARD,
    net_name: str,
    layer: int,
    points: list[tuple[float, float]],
    name: str,
    priority: int,
    clearance: float,
    full_pad_connection: bool,
) -> None:
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNet(board.FindNet(net_name))
    zone.SetZoneName(name)
    zone.SetAssignedPriority(priority)
    zone.SetLocalClearance(pcbnew.FromMM(clearance))
    zone.SetMinThickness(pcbnew.FromMM(0.20))
    zone.SetThermalReliefGap(pcbnew.FromMM(0.25))
    zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.30))
    zone.SetPadConnection(
        pcbnew.ZONE_CONNECTION_FULL
        if full_pad_connection
        else pcbnew.ZONE_CONNECTION_THERMAL
    )
    zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in points:
        outline.Append(pt(x, y))
    board.Add(zone)


def add_via(
    board: pcbnew.BOARD,
    net_name: str,
    position: tuple[float, float],
    diameter: float = 0.50,
    drill: float = 0.30,
) -> None:
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pt(*position))
    via.SetWidth(pcbnew.FromMM(diameter))
    via.SetDrill(pcbnew.FromMM(drill))
    via.SetLayerPair(F_LAYER, B_LAYER)
    via.SetNet(board.FindNet(net_name))
    board.Add(via)


def expand_outline(board: pcbnew.BOARD) -> None:
    def remap(value: float) -> float:
        mapping = {20.0: 18.0, 90.0: 92.0, 50.0: 48.0, 115.0: 117.0}
        return mapping.get(round(value, 4), value)

    for shape in board.GetDrawings():
        if shape.GetLayer() != pcbnew.Edge_Cuts:
            continue
        sx = pcbnew.ToMM(shape.GetStart().x)
        sy = pcbnew.ToMM(shape.GetStart().y)
        ex = pcbnew.ToMM(shape.GetEnd().x)
        ey = pcbnew.ToMM(shape.GetEnd().y)
        shape.SetStart(pt(remap(sx), remap(sy)))
        shape.SetEnd(pt(remap(ex), remap(ey)))


def add_fiducial(
    board: pcbnew.BOARD, reference: str, position: tuple[float, float]
) -> None:
    library = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints\Fiducial.pretty")
    footprint = pcbnew.FootprintLoad(str(library), "Fiducial_1mm_Mask2mm")
    if footprint is None:
        raise RuntimeError("Unable to load the standard KiCad fiducial footprint")
    footprint.SetReference(reference)
    footprint.SetValue("Fiducial_1mm_Mask2mm")
    footprint.SetPosition(pt(*position))
    footprint.SetBoardOnly(True)
    footprint.SetExcludedFromBOM(True)
    footprint.GetField("Reference").SetVisible(False)
    footprint.GetField("Value").SetVisible(False)
    board.Add(footprint)


def main() -> int:
    board = pcbnew.LoadBoard(str(INPUT))
    expand_outline(board)

    # Continuous return planes.  F.Cu is useful for local component returns;
    # B.Cu is the primary uninterrupted return plane.
    ground_boundary = [(18.5, 48.5), (91.5, 48.5), (91.5, 116.5), (18.5, 116.5)]
    add_zone(board, "GND", B_LAYER, ground_boundary, "GND_B_PLANE", 0, 0.15, False)
    add_zone(board, "GND", F_LAYER, ground_boundary, "GND_F_POUR", 0, 0.15, True)

    # Guideline-width copper regions.  These pours cover the actual
    # high-current sections while the 0.4 mm-pitch WLC1115 escapes remain
    # narrow until they clear adjacent pins.
    power_zones = [
        ("PVIN_0", [(26.8, 51.2), (33.7, 51.2), (33.7, 54.3), (34.0, 54.8), (34.0, 57.6), (32.0, 57.6), (30.8, 54.0), (26.8, 54.0)], "PVIN_INPUT"),
        ("/IIN_CSN_0", [(32.3, 54.3), (33.7, 54.3), (39.3, 57.0), (39.3, 59.8), (35.8, 59.8), (32.3, 55.8)], "BUCK_INPUT"),
        ("/SW1_0", [(36.8, 55.2), (39.3, 55.2), (45.5, 58.7), (45.5, 60.3), (43.8, 60.3), (36.8, 57.0)], "BUCK_SW_HIGH"),
        ("/SW1_0", [(36.8, 61.0), (39.3, 61.0), (45.5, 58.7), (45.5, 60.3), (39.3, 64.3), (36.8, 64.3)], "BUCK_SW_LOW"),
        ("/IOUT_CSP_0", [(53.5, 58.6), (58.8, 58.6), (58.8, 60.4), (53.5, 60.4)], "BUCK_OUTPUT"),
        ("/IOUT_CSP_0", [(56.3, 51.0), (61.6, 51.0), (61.6, 53.5), (58.8, 58.8), (56.3, 58.8)], "BUCK_OUTPUT_CAPS"),
        ("/IOUT_CSN_0", [(59.3, 58.7), (60.6, 58.7), (68.5, 62.7), (72.5, 62.2), (80.3, 65.8), (80.3, 69.3), (77.0, 69.3), (71.5, 64.3), (67.6, 64.8), (59.3, 60.3)], "BRIDGE_SUPPLY_UPPER"),
        ("/IOUT_CSN_0", [(67.4, 63.2), (69.0, 63.2), (69.0, 78.8), (67.4, 78.8)], "BRIDGE_SUPPLY_SPINE"),
        ("/IOUT_CSN_0", [(67.4, 76.4), (72.5, 76.4), (77.0, 79.9), (80.3, 79.9), (80.3, 81.3), (77.0, 81.3), (71.5, 78.3), (67.4, 78.3)], "BRIDGE_SUPPLY_LOWER"),
        ("/SW2_1", [(77.8, 64.7), (80.3, 64.7), (80.3, 74.3), (77.8, 74.3)], "INVERTER_SW2_HALFBRIDGE"),
        ("/SW2_1", [(74.9, 72.9), (78.2, 72.9), (78.2, 74.3), (76.3, 74.3), (76.3, 104.2), (74.9, 104.2)], "INVERTER_SW2_RESONANT"),
        ("/SW1_1", [(77.8, 76.7), (80.3, 76.7), (80.3, 86.3), (77.8, 86.3)], "INVERTER_SW1_HALFBRIDGE"),
        ("/SW1_1", [(79.8, 84.9), (81.2, 84.9), (84.9, 95.7), (84.9, 97.2), (83.5, 97.2), (79.8, 86.3)], "INVERTER_SW1_COIL"),
        ("/COIL_SNS", [(76.8, 91.3), (78.2, 91.3), (78.2, 100.8), (84.9, 100.8), (84.9, 102.2), (76.8, 104.2)], "COIL_RETURN"),
    ]
    for index, (net_name, points, name) in enumerate(power_zones):
        add_zone(board, net_name, F_LAYER, points, name, 10 + index, 0.20, True)

    # Sixteen through thermal vias in the WLC1115 exposed pad (guideline >=15).
    thermal_vias = [
        (50.0, 79.0), (50.0, 79.5), (50.0, 80.0), (50.0, 80.5),
        (51.0, 78.0), (51.0, 78.5), (51.0, 79.0), (51.0, 79.5),
        (52.0, 77.5), (52.0, 78.0), (52.0, 78.5), (52.0, 79.0),
        (53.5, 77.0), (53.5, 77.5), (53.5, 78.0), (53.5, 78.5),
    ]
    for position in thermal_vias:
        add_via(board, "GND", position)

    add_fiducial(board, "FID1", (20.5, 50.5))
    add_fiducial(board, "FID2", (89.5, 50.5))
    add_fiducial(board, "FID3", (89.5, 114.5))

    pcbnew.SaveBoard(str(OUTPUT), board)
    print(f"Wrote {OUTPUT} with {len(power_zones)} power zones and {len(thermal_vias)} U1 thermal vias")
    return 0


if __name__ == "__main__":
    sys.exit(main())
