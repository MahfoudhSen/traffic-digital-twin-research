"""
fdot_config.py
Source-of-truth for all FDOT-derived demand parameters and SUMO network edge IDs.
Site data: FDOT 2025 Traffic Monitoring (Glades Rd × Airport Rd, Boca Raton FL).
"""
from __future__ import annotations
from dataclasses import dataclass

# ── Toggle ─────────────────────────────────────────────────────────────────────
# True  → use strictly FDOT-derived volumes (2619 WB / 1881 EB)
# False → use week-4 manually calibrated targets (2700 WB / 2500 EB)
USE_FDOT_MATH = False

# ── FDOT 2025 Raw Site Records ──────────────────────────────────────────────────
FDOT_SITES: dict[str, dict] = {
    "glades": {
        "site_id": "930041",
        "road":    "Glades Road",
        "aadt":    50_000,
        "k":       0.090,   # peak-hour factor        PHV  = AADT × K
        "d":       0.582,   # directional factor      Peak = PHV  × D
        "t":       0.041,   # truck factor            HCV  = Dir  × T
    },
    "airport": {
        "site_id": "937414",
        "road":    "Airport Road",
        "aadt":    7_700,
        "k":       0.090,
        "d":       0.582,
        "t":       0.051,
    },
}

# Week-4 manually calibrated overrides (used when USE_FDOT_MATH = False)
MANUAL_TARGETS = {
    "wb": 2619,
    "eb": 1881,
}

# ── SUMO Network Edge IDs ───────────────────────────────────────────────────────
# Network file: ttestingW3.net.xml (with airport_lane1.con.xml channelization fix)
EDGES: dict[str, str] = {
    # ── Glades Rd WB (1234122485#0, 5 lanes) ─────────────────────────────────
    # Verified connections: L0→rt 534832359#0 | L0-4→str 741687503#0 | L4→lt 1234122498#0
    "wb_from":    "1234122485#0",
    "wb_str_to":  "741687503#1",
    "wb_rt_to":   "534832359#0",
    "wb_lt_to":   "1234122498#0",
    "wb_count":   "1234122485#0",   # FDOT Site 930041 induction-loop location

    # ── Glades Rd EB (543692100#0, 6 lanes) ──────────────────────────────────
    # Verified connections: L0→rt 1234122498#0 | L1-4→str 534834577#0 | L5→lt 534832359#0
    "eb_from":    "543692100#0",
    "eb_str_to":  "534834577#0",
    "eb_rt_to":   "1234122498#0",
    "eb_lt_to":   "534832359#0",
    "eb_count":   "543692100#0",    # FDOT Site 930041 opposing count location

    # ── Airport Rd South (1234122500#0, 4 lanes) ──────────────────────────────
    # Verified connections: L0→rt 534834577#0 | L1-2→str 534832359#0 | L3→lt 741687503#0
    "arpt_s_from":    "1234122500#0",
    "arpt_s_str_to":  "534832359#0",
    "arpt_s_rt_to":   "534834577#0",
    "arpt_s_lt_to":   "741687503#0",
    "arpt_sb_from":   "1234122500#0",   # alias used by geh_calibration.py

    # ── Airport Rd West (480427144#0, 2 lanes) ────────────────────────────────
    # Verified connections: L0→rt 741687503#0 | L1→str 1234122498#0 | L1→lt 534834577#0
    "arpt_w_from":    "480427144#0",
    "arpt_w_str_to":  "1234122498#0",
    "arpt_w_rt_to":   "741687503#0",
    "arpt_w_lt_to":   "534834577#0",

    # ── Minor intersection movements ──────────────────────────────────────────
    "se_from": "49436629",
    "se_to":   "534832359#0",
    "sw_from": "1234122473#0",
    "sw_to":   "49436625",
}

# ── vType Physical + Lane-Change Parameters ────────────────────────────────────
# LC2013 model tuned to eliminate strategic dead-stop blocking:
#
#   lcStrategic  — how far upstream the vehicle begins its mandatory lane change.
#                  4.0-5.0 forces early maneuvering instead of last-second panic.
#   lcCooperative— probability that the ego vehicle yields to a neighbour's gap
#                  request. 1.0 = full cooperation (always create a gap for others).
#   lcSpeedGain  — eagerness to change lanes purely for speed. 0.0-0.3 prevents
#                  random weaving that blocks turning vehicles.
#   lcAssertive  — accepted gap = minGap / lcAssertive. >1.0 allows tighter gaps
#                  when the vehicle MUST change lanes, preventing the dead-stop.
#   lcImpatience — dynamic multiplier: assertiveness grows as wait time increases.
#                  Mimics real driver behaviour when stuck waiting for a gap.
#
# Truck physics: 12.5 m body occupies ~2.5x road space of a car; accel=1.0 m/s2
# extends saturation headway by ~40% vs cars; minGap=3.5 m lowers discharge rate.
VTYPES: dict[str, dict] = {
    # General passenger car — Glades WB/EB corridor and minor approaches
    "car": {
        "vClass":          "passenger",
        "length":          "4.8",
        "minGap":          "2.5",
        "maxSpeed":        "16.67",   # 60 km/h posted speed on Glades Rd
        "accel":           "2.6",
        "decel":           "4.5",
        "emergencyDecel":  "9.0",
        "speedDev":        "0.1",
        "sigma":           "0.5",
        "laneChangeModel": "LC2013",
        "lcStrategic":     "10.0",
        "lcCooperative":   "1.0",
        "lcSpeedGain":     "0.3",
        "lcAssertive":     "2.0",
        "lcImpatience":    "0.5",
    },
    # General heavy truck — Glades WB/EB corridor
    "truck": {
        "vClass":          "truck",
        "length":          "12.5",
        "minGap":          "3.5",
        "maxSpeed":        "13.89",   # 50 km/h HCV limit
        "accel":           "1.0",
        "decel":           "3.5",
        "emergencyDecel":  "7.0",
        "speedDev":        "0.05",
        "sigma":           "0.3",
        "laneChangeModel": "LC2013",
        "lcStrategic":     "10.0",
        "lcCooperative":   "1.0",
        "lcSpeedGain":     "0.1",
        "lcAssertive":     "1.5",
        "lcImpatience":    "0.3",
    },
    # Lane-keeper car — Airport Rd SB straight flows ONLY.
    # lcSpeedGain=0.0: will NEVER change lanes for speed (prevents drift into
    # Lane 0, which has right-turn connections only).
    "car_var": {
        "vClass":          "passenger",
        "length":          "4.8",
        "minGap":          "2.5",
        "maxSpeed":        "16.67",
        "accel":           "2.6",
        "decel":           "4.5",
        "emergencyDecel":  "9.0",
        "speedDev":        "0.1",
        "sigma":           "0.5",
        "laneChangeModel": "LC2013",
        "lcStrategic":     "10.0",
        "lcCooperative":   "1.0",
        "lcSpeedGain":     "0.0",
        "lcAssertive":     "1.5",
        "lcImpatience":    "0.2",
    },
    # Lane-keeper truck — Airport Rd SB straight flows ONLY.
    "truck_var": {
        "vClass":          "truck",
        "length":          "12.5",
        "minGap":          "3.5",
        "maxSpeed":        "13.89",
        "accel":           "1.0",
        "decel":           "3.5",
        "emergencyDecel":  "7.0",
        "speedDev":        "0.05",
        "sigma":           "0.3",
        "laneChangeModel": "LC2013",
        "lcStrategic":     "10.0",
        "lcCooperative":   "1.0",
        "lcSpeedGain":     "0.0",
        "lcAssertive":     "1.5",
        "lcImpatience":    "0.2",
    },
}


@dataclass
class DirectionalDemand:
    """Fully-derived demand volumes for one FDOT site, one hour."""
    site_id:     str
    road:        str
    aadt:        int
    phv:         int        # total peak-hour volume (both directions)
    peak:        int        # higher-volume direction
    opposing:    int        # lower-volume direction
    peak_cars:   int
    peak_trucks: int
    opp_cars:    int
    opp_trucks:  int

    @classmethod
    def from_site(cls, key: str) -> "DirectionalDemand":
        s = FDOT_SITES[key]
        aadt = s["aadt"]
        k, d, t = s["k"], s["d"], s["t"]

        phv      = round(aadt * k)
        peak     = round(phv * d)
        opposing = phv - peak

        peak_trucks = round(peak * t)
        peak_cars   = peak - peak_trucks
        opp_trucks  = round(opposing * t)
        opp_cars    = opposing - opp_trucks

        return cls(
            site_id=s["site_id"],
            road=s["road"],
            aadt=aadt,
            phv=phv,
            peak=peak,
            opposing=opposing,
            peak_cars=peak_cars,
            peak_trucks=peak_trucks,
            opp_cars=opp_cars,
            opp_trucks=opp_trucks,
        )

    def print_report(self) -> None:
        sep = "=" * 60
        print(f"\n{sep}")
        print(f"  {self.road}  (Site {self.site_id})")
        print(f"{sep}")
        print(f"  AADT                  = {self.aadt:>6,} veh/day")
        print(f"  Peak-Hour Volume      = {self.phv:>6,} veh/hr")
        print(f"  Peak Direction        = {self.peak:>6,} veh/hr")
        print(f"    Cars                = {self.peak_cars:>6,} veh/hr")
        print(f"    Trucks              = {self.peak_trucks:>6,} veh/hr")
        print(f"  Opposing Direction    = {self.opposing:>6,} veh/hr")
        print(f"    Cars                = {self.opp_cars:>6,} veh/hr")
        print(f"    Trucks              = {self.opp_trucks:>6,} veh/hr")


if __name__ == "__main__":
    for key in FDOT_SITES:
        DirectionalDemand.from_site(key).print_report()
