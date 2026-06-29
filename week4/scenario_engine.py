"""
scenario_engine.py
Automated SUMO route-file generator for the Glades Rd × Airport Rd digital twin.

Usage examples
--------------
  # Baseline (FDOT-derived demand):
  python scenario_engine.py

  # 15% mixed-use development surge:
  python scenario_engine.py --surge 1.15 --name dev_surge_15pct

  # Road diet on WB Glades (drop to 2 effective lanes, −30% capacity):
  python scenario_engine.py --block flow_west_cars:0.70 flow_west_trucks:0.70 --name wb_road_diet

  # Construction bottleneck — close SE minor approach:
  python scenario_engine.py --block flow_se_cars:0.0 flow_se_trucks:0.0 --name se_construction

  # Combined surge + infrastructure shift:
  python scenario_engine.py --surge 1.15 --block flow_east_cars:0.80 --name scenario_a
"""
from __future__ import annotations

import argparse
import math
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

from fdot_config import (
    EDGES, FDOT_SITES, VTYPES, USE_FDOT_MATH, MANUAL_TARGETS,
    DirectionalDemand,
)

# ── Simulation window (seconds) ────────────────────────────────────────────────
SIM_BEGIN = 0
SIM_END   = 3600   # 1 peak hour


# ── Turn-split helper ─────────────────────────────────────────────────────────
def _approach_flows(
    prefix: str,
    from_edge: str,
    str_to: str,
    rt_to: str,
    lt_to: str,
    total: int,
    truck_factor: float,
) -> list[dict]:
    """
    Produce 6 flow dicts (str/rt/lt × car/truck) for one intersection approach.
    Split order: straight first, left second, right = remainder — avoids
    half-integer rounding errors on the 15% bucket.
    departPos="base" spawns vehicles at the upstream end of the approach edge
    so they drive the full ~100 m and are visible queueing/turning.
    """
    s   = round(total * 0.75)
    lt  = round(total * 0.10)
    rt  = total - s - lt

    def split(n: int) -> tuple[int, int]:
        trucks = round(n * truck_factor)
        return n - trucks, trucks

    s_car,  s_tr  = split(s)
    rt_car, rt_tr = split(rt)
    lt_car, lt_tr = split(lt)

    base = {"departLane": "best", "departPos": "base"}
    return [
        {**base, "id": f"flow_{prefix}_str_cars",   "type": "car",   "vph": s_car,
         "from": from_edge, "to": str_to},
        {**base, "id": f"flow_{prefix}_str_trucks",  "type": "truck", "vph": s_tr,
         "from": from_edge, "to": str_to},
        {**base, "id": f"flow_{prefix}_rt_cars",    "type": "car",   "vph": rt_car,
         "from": from_edge, "to": rt_to},
        {**base, "id": f"flow_{prefix}_rt_trucks",   "type": "truck", "vph": rt_tr,
         "from": from_edge, "to": rt_to},
        {**base, "id": f"flow_{prefix}_lt_cars",    "type": "car",   "vph": lt_car,
         "from": from_edge, "to": lt_to},
        {**base, "id": f"flow_{prefix}_lt_trucks",   "type": "truck", "vph": lt_tr,
         "from": from_edge, "to": lt_to},
    ]


# ── Baseline flow table ────────────────────────────────────────────────────────
def build_baseline_flows(glades: DirectionalDemand,
                         airport: DirectionalDemand) -> list[dict]:
    """
    4-approach turn-split model.  Each approach uses 75% straight / 15% right /
    10% left with the road-specific truck factor.  Volumes respect USE_FDOT_MATH.
    """
    t_g = FDOT_SITES["glades"]["t"]
    t_a = FDOT_SITES["airport"]["t"]

    if USE_FDOT_MATH:
        wb_total = glades.peak
        eb_total = glades.opposing
    else:
        wb_total = MANUAL_TARGETS["wb"]
        eb_total = MANUAL_TARGETS["eb"]

    arpt_s_total = airport.peak
    arpt_w_total = airport.opposing
    nb_cars      = airport.opp_cars
    nb_trucks    = airport.opp_trucks

    return [
        # ── Glades Rd WB (1234122485#0) ──────────────────────────────────────
        *_approach_flows("wb_glades", EDGES["wb_from"],
                         EDGES["wb_str_to"], EDGES["wb_rt_to"], EDGES["wb_lt_to"],
                         wb_total, t_g),
        # ── Glades Rd EB (543692100#0) ───────────────────────────────────────
        *_approach_flows("eb_glades", EDGES["eb_from"],
                         EDGES["eb_str_to"], EDGES["eb_rt_to"], EDGES["eb_lt_to"],
                         eb_total, t_g),
        # ── Airport South (1234122500#0) ──────────────────────────────────────
        *_approach_flows("arpt_south", EDGES["arpt_s_from"],
                         EDGES["arpt_s_str_to"], EDGES["arpt_s_rt_to"], EDGES["arpt_s_lt_to"],
                         arpt_s_total, t_a),
        # ── Airport West (480427144#0) ────────────────────────────────────────
        *_approach_flows("arpt_west", EDGES["arpt_w_from"],
                         EDGES["arpt_w_str_to"], EDGES["arpt_w_rt_to"], EDGES["arpt_w_lt_to"],
                         arpt_w_total, t_a),
        # ── Minor movements ───────────────────────────────────────────────────
        {"id": "flow_se_cars",   "type": "car",   "vph": nb_cars,   "departLane": "best",
         "from": EDGES["se_from"], "to": EDGES["se_to"]},
        {"id": "flow_se_trucks", "type": "truck", "vph": nb_trucks, "departLane": "best",
         "from": EDGES["se_from"], "to": EDGES["se_to"]},
        {"id": "flow_sw_cars",   "type": "car",   "vph": nb_cars,   "departLane": "best",
         "from": EDGES["sw_from"], "to": EDGES["sw_to"]},
    ]


# ── Route-file writer ──────────────────────────────────────────────────────────
def write_route_file(
    flows: list[dict],
    output_path: str,
    scenario_name: str = "baseline",
) -> None:
    """
    Render flows + vTypes into a SUMO-compliant .rou.xml file.
    Uses vehsPerHour (rate-based injection) rather than fixed vehicle counts.
    """
    root = ET.Element("routes")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set(
        "xsi:noNamespaceSchemaLocation",
        "http://sumo.dlr.de/xsd/routes_file.xsd",
    )

    root.append(ET.Comment(f" Scenario: {scenario_name} "))
    root.append(ET.Comment(
        " FDOT 2025 | Site 930041 (Glades Rd) | Site 937414 (Airport Rd) "
    ))
    root.text = "\n    "

    # vType definitions
    for vtype_id, params in VTYPES.items():
        el = ET.SubElement(root, "vType")
        el.set("id", vtype_id)
        for attr, val in params.items():
            el.set(attr, val)

    # Flow elements
    for f in flows:
        vph = f["vph"]
        if vph <= 0:
            continue    # skip flows zeroed out by infra_shift

        el = ET.SubElement(root, "flow")
        el.set("id",           f["id"])
        el.set("type",         f["type"])
        el.set("begin",        str(SIM_BEGIN))
        el.set("end",          str(SIM_END))
        el.set("vehsPerHour",  str(vph))
        el.set("from",         f["from"])
        el.set("to",           f["to"])
        el.set("departLane",   f.get("departLane", "best"))
        el.set("departPos",    f.get("departPos", "last"))
        el.set("departSpeed",  "max")
        el.set("maxDepartDelay", str(SIM_END))

    _indent(root)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")
    tree.write(output_path, encoding="unicode", xml_declaration=True)
    print(f"  [OK] Route file written -> {output_path}")


def _indent(elem: ET.Element, level: int = 0) -> None:
    """Add pretty-print whitespace (fallback for Python < 3.9)."""
    indent = "\n" + "    " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "    "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent


# ── Scenario application ───────────────────────────────────────────────────────
def apply_demand_surge(flows: list[dict], surge: float) -> list[dict]:
    """
    Scale every flow uniformly by `surge`.
    surge=1.15 simulates a 15% mixed-use development footprint increase.
    Result is rounded to the nearest integer vehicle/hr.
    """
    result = []
    for f in flows:
        scaled = dict(f)
        scaled["vph"] = max(0, round(f["vph"] * surge))
        result.append(scaled)
    return result


def apply_infra_shifts(flows: list[dict],
                       shifts: dict[str, float]) -> list[dict]:
    """
    Apply per-flow capacity scale factors.

    shifts: {flow_id: scale_factor}
      scale_factor = 0.0  → remove flow entirely (road closed / approach blocked)
      scale_factor = 0.70 → reduce to 70 % of demand (lane reduction / road diet)

    Example: road diet on WB Glades (3 lanes → 2 lanes, −30% capacity):
      shifts = {"flow_west_cars": 0.70, "flow_west_trucks": 0.70}
    """
    result = []
    for f in flows:
        modified = dict(f)
        if f["id"] in shifts:
            modified["vph"] = max(0, round(f["vph"] * shifts[f["id"]]))
        result.append(modified)
    return result


# ── CLI ────────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate SUMO route files for Glades/Airport scenario testing."
    )
    p.add_argument(
        "--surge", type=float, default=1.0, metavar="FACTOR",
        help="Demand surge multiplier (e.g. 1.15 = +15%% development growth). Default: 1.0",
    )
    p.add_argument(
        "--block", nargs="*", default=[], metavar="FLOW_ID:SCALE",
        help=(
            "Infrastructure shift: one or more 'flow_id:scale' pairs. "
            "scale=0.0 removes the flow; scale=0.70 reduces it to 70%%. "
            "Example: --block flow_west_cars:0.70 flow_se_cars:0.0"
        ),
    )
    p.add_argument(
        "--name", type=str, default=None, metavar="SCENARIO",
        help="Scenario label used in the output filename. Default: auto-generated.",
    )
    p.add_argument(
        "--out-dir", type=str, default=".", metavar="DIR",
        help="Output directory for the generated .rou.xml file. Default: current dir.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    glades  = DirectionalDemand.from_site("glades")
    airport = DirectionalDemand.from_site("airport")

    # Print validation report
    glades.print_report()
    airport.print_report()
    print()

    flows = build_baseline_flows(glades, airport)

    # Demand surge
    if args.surge != 1.0:
        print(f"  Demand surge ×{args.surge:.2f} applied to all flows.")
        flows = apply_demand_surge(flows, args.surge)

    # Infrastructure shifts
    shifts: dict[str, float] = {}
    for token in args.block or []:
        try:
            flow_id, scale_str = token.split(":")
            shifts[flow_id] = float(scale_str)
        except ValueError:
            raise SystemExit(
                f"  [ERROR] --block argument '{token}' must be 'flow_id:scale' "
                f"(e.g. flow_west_cars:0.70)"
            )

    if shifts:
        print(f"  Infrastructure shifts: {shifts}")
        flows = apply_infra_shifts(flows, shifts)

    # Derive scenario name
    if args.name:
        scenario_name = args.name
    elif args.surge != 1.0 and shifts:
        scenario_name = f"surge_{args.surge:.2f}_infra_shift"
    elif args.surge != 1.0:
        scenario_name = f"surge_{args.surge:.2f}"
    elif shifts:
        scenario_name = "infra_shift"
    else:
        scenario_name = "baseline"

    # Write route file
    filename    = f"custom_flows_{scenario_name}.rou.xml"
    output_path = os.path.join(args.out_dir, filename)
    print(f"\n  Scenario : {scenario_name}")
    write_route_file(flows, output_path, scenario_name)

    # Print flow summary table
    print(f"\n  {'Flow ID':<35} {'veh/hr':>8}")
    print(f"  {'-'*44}")
    for f in flows:
        label = f["id"]
        vph   = f["vph"]
        bar   = "#" * min(40, vph // 60)
        print(f"  {label:<35} {vph:>8}  {bar}")
    print()


if __name__ == "__main__":
    main()
