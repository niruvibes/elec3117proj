from pathlib import Path
import sys

import pcbnew


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "tmp/layout-analysis/project.placed.kicad_pcb"
OUTPUT = ROOT / "tmp/layout-analysis/project.fresh-relaxed.dsn"


def main() -> int:
    board = pcbnew.LoadBoard(str(INPUT))
    settings = board.GetDesignSettings()
    settings.m_MinClearance = pcbnew.FromMM(0.10)
    net_settings = settings.m_NetSettings
    net_settings.ClearNetclasses()
    net_settings.ClearNetclassPatternAssignments()
    default = net_settings.GetDefaultNetclass()
    default.SetClearance(pcbnew.FromMM(0.10))
    default.SetTrackWidth(pcbnew.FromMM(0.15))
    default.SetViaDiameter(pcbnew.FromMM(0.60))
    default.SetViaDrill(pcbnew.FromMM(0.30))
    net_settings.SetDefaultNetclass(default)
    net_settings.ClearAllCaches()
    net_settings.RecomputeEffectiveNetclasses()
    if not pcbnew.ExportSpecctraDSN(board, str(OUTPUT)):
        raise RuntimeError("Second-pass Specctra DSN export failed")
    print(f"Exported {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
