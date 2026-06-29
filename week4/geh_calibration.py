"""
geh_calibration.py
GEH-statistic calibration report for the Glades Rd x Airport Rd SUMO baseline.

Industry standard (UK DfT / FHWA): GEH < 5.0 = good calibration.
  GEH = sqrt( 2 x (M - C)^2 / (M + C) )
  M = modelled (SUMO simulated count, veh/hr)
  C = counted  (FDOT field observation, veh/hr)

Usage
-----
  # After running ttestingW3.sumocfg which writes base_edgedata.xml:
  python geh_calibration.py

  # Point at a different edgedata file:
  python geh_calibration.py --edgedata path/to/base_edgedata.xml

  # Print sensitivity sweep around each target:
  python geh_calibration.py --sensitivity
"""
from __future__ import annotations

import argparse
import math
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from fdot_config import EDGES, USE_FDOT_MATH, MANUAL_TARGETS, DirectionalDemand

DEFAULT_EDGEDATA = "base_edgedata.xml"


# -- FDOT field targets (count locations) -------------------------------------
def _build_targets() -> dict[str, int]:
    """
    Return {edge_id: FDOT_hourly_target} for each instrumented count location.
    Respects USE_FDOT_MATH flag from fdot_config.
    """
    glades  = DirectionalDemand.from_site("glades")
    airport = DirectionalDemand.from_site("airport")

    if USE_FDOT_MATH:
        wb_target = glades.peak
        eb_target = glades.opposing
    else:
        wb_target = MANUAL_TARGETS["wb"]
        eb_target = MANUAL_TARGETS["eb"]

    return {
        EDGES["wb_count"]:     wb_target,
        EDGES["eb_count"]:     eb_target,
        EDGES["arpt_sb_from"]: airport.peak,
    }


# -- Core GEH formula ---------------------------------------------------------
def geh(simulated: float, observed: float) -> float:
    """
    Geoffrey E. Havers statistic.
    Returns infinity when both values are zero (undefined -- flag for review).
    """
    if simulated + observed == 0:
        return math.inf
    return math.sqrt(2.0 * (simulated - observed) ** 2 / (simulated + observed))


# -- Edgedata parser ----------------------------------------------------------
def read_first_hour_counts(edgedata_path: str) -> dict[str, int]:
    """
    Parse base_edgedata.xml and return {edge_id: entered_count} for the
    first interval only (0-3600 s). Ignores drain-down tail intervals.
    """
    try:
        tree = ET.parse(edgedata_path)
    except FileNotFoundError:
        raise SystemExit(
            f"[ERROR] {edgedata_path} not found.\n"
            "Run the SUMO simulation first, then re-run this script."
        )
    except ET.ParseError:
        raise SystemExit(
            f"[ERROR] {edgedata_path} is incomplete.\n"
            "Let the SUMO simulation finish before parsing."
        )

    root = tree.getroot()
    intervals = root.findall("interval")
    if not intervals:
        raise SystemExit(f"[ERROR] No <interval> elements found in {edgedata_path}.")

    first = intervals[0]
    counts: dict[str, int] = {}
    for edge in first.findall("edge"):
        eid      = edge.get("id", "")
        departed = int(float(edge.get("departed", 0)))
        # All measurement edges in this model are departure edges (vehicles
        # originate there). Use departed, not entered, to avoid counting
        # unrelated pass-through traffic on the same edge.
        counts[eid] = departed

    return counts


# -- Calibration report -------------------------------------------------------
@dataclass
class GEHResult:
    edge_id:   str
    label:     str
    observed:  int
    simulated: int
    geh_value: float

    @property
    def status(self) -> str:
        if self.geh_value < 5.0:
            return "PASS"
        if self.geh_value < 10.0:
            return "WARN"
        return "FAIL"

    @property
    def error_pct(self) -> float:
        if self.observed == 0:
            return math.inf
        return 100.0 * (self.simulated - self.observed) / self.observed


def run_calibration_report(edgedata_path: str = DEFAULT_EDGEDATA) -> list[GEHResult]:
    targets = _build_targets()
    counts  = read_first_hour_counts(edgedata_path)

    edge_labels = {
        EDGES["wb_count"]:     "Glades WB (Site 930041 peak)",
        EDGES["eb_count"]:     "Glades EB (Site 930041 opposing)",
        EDGES["arpt_sb_from"]: "Airport Rd SB (Site 937414 peak)",
    }

    results: list[GEHResult] = []
    for edge_id, observed in targets.items():
        simulated = counts.get(edge_id, 0)
        g = geh(simulated, observed)
        results.append(GEHResult(
            edge_id=edge_id,
            label=edge_labels.get(edge_id, edge_id),
            observed=observed,
            simulated=simulated,
            geh_value=g,
        ))

    # Print formatted report
    sep  = "=" * 62
    dash = "-" * 62
    print(f"\n{sep}")
    print("  GEH CALIBRATION REPORT -- Glades Rd x Airport Rd")
    print(f"  Source   : {edgedata_path}")
    print(f"  Standard : GEH < 5.0 (UK DfT / FHWA)")
    print(f"{sep}")
    print(f"  {'Corridor':<34} {'Obs':>5} {'Sim':>5} {'Delta%':>7} {'GEH':>6}  Status")
    print(f"  {dash}")

    all_pass = True
    for r in results:
        delta = f"{r.error_pct:+.1f}%" if r.error_pct != math.inf else "   N/A"
        geh_s = f"{r.geh_value:.2f}"   if r.geh_value != math.inf else "   inf"
        flag  = "[OK]" if r.status == "PASS" else ("[!!]" if r.status == "WARN" else "[XX]")
        print(f"  {r.label:<34} {r.observed:>5} {r.simulated:>5} {delta:>7} {geh_s:>6}  {flag} {r.status}")
        if r.geh_value >= 5.0:
            all_pass = False

    print(f"  {dash}")
    outcome = "ALL PASS -- baseline is calibrated." if all_pass \
              else "FAIL -- adjust demand or signal timing (see notes below)."
    print(f"  {outcome}")

    if not all_pass:
        print()
        print("  Calibration notes:")
        for r in results:
            if r.geh_value >= 5.0:
                gap = r.observed - r.simulated
                direction = "add" if gap > 0 else "remove"
                print(f"    {r.label}: need to {direction} ~{abs(gap)} veh/hr "
                      f"(GEH={r.geh_value:.2f})")

    print(f"{sep}\n")
    return results


# -- Sensitivity helper -------------------------------------------------------
def geh_sensitivity(observed: int, sim_range: range) -> None:
    """
    Print GEH for a sweep of simulated values around a target.
    Useful for knowing how many vehicles to add/remove to reach GEH < 5.

    Example:
        geh_sensitivity(observed=2619, sim_range=range(2400, 2800, 50))
    """
    print(f"\n  GEH sensitivity  (FDOT target = {observed} veh/hr)")
    print(f"  {'Simulated':>10}  {'GEH':>6}  Status")
    print(f"  {'-'*28}")
    for sim in sim_range:
        g      = geh(sim, observed)
        status = "PASS" if g < 5.0 else ("WARN" if g < 10.0 else "FAIL")
        marker = " <-- GEH crosses 5.0" if abs(g - 5.0) < 0.3 else ""
        print(f"  {sim:>10}  {g:>6.2f}  {status}{marker}")
    print()


# -- CLI ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GEH calibration report for SUMO Glades/Airport baseline."
    )
    parser.add_argument(
        "--edgedata", default=DEFAULT_EDGEDATA, metavar="FILE",
        help=f"Path to SUMO edge-data XML output. Default: {DEFAULT_EDGEDATA}",
    )
    parser.add_argument(
        "--sensitivity", action="store_true",
        help="Also print a GEH sensitivity sweep around each FDOT target.",
    )
    args = parser.parse_args()

    results = run_calibration_report(args.edgedata)

    if args.sensitivity:
        targets = _build_targets()
        for edge_id, observed in targets.items():
            low  = max(0, observed - 400)
            high = observed + 401
            geh_sensitivity(observed, range(low, high, 50))
