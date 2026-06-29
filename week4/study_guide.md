# Glades Road SUMO Simulation — Study Guide

---

## 1. What Is This Project?

You built a **traffic microsimulation** of the **Glades Road corridor** in Boca Raton, FL (near the Boca Raton Airport interchange) using **SUMO** (Simulation of Urban MObility), version 1.27.0.

The goal is to create a **calibrated base scenario** — a model that accurately reflects real-world traffic volumes — which will then serve as the foundation for comparing alternative scenarios (Scenario A and Scenario B).

---

## 2. What Is SUMO?

SUMO is an open-source traffic microsimulation tool. "Micro" means it simulates **individual vehicles** — each car or truck has its own position, speed, and behavior — rather than just aggregate flow numbers.

Key files you work with in SUMO:

| File | Purpose |
|---|---|
| `.sumocfg` | Config file — points to all other files, sets simulation time |
| `.net.xml` | The road network (lanes, signals, geometry) |
| `.rou.xml` | Routes — defines where vehicles come from, go to, and how many |
| `edge_dump.add.xml` | Tells SUMO to record vehicle counts per edge per time interval |
| `base_edgedata.xml` | Output — the actual counts SUMO produced after running |

---

## 3. The Study Corridor

**Road:** Glades Road (east-west arterial)  
**Location:** Boca Raton, near the airport interchange  
**Intersection type:** Signalized 4-approach interchange

### The 4 Approaches (where vehicles enter the network)

| Edge ID | Road | Lanes |
|---|---|---|
| `1234122485#0` | Glades Rd **Westbound** | 5 lanes |
| `543692100#0` | Glades Rd **Eastbound** | 6 lanes |
| `1234122500#0` | Airport Road **South** | 4 lanes |
| `480427144#0` | Airport Road **West** | 2 lanes |

### Turn splits used (all approaches)
- 75% go straight
- 15% turn right
- 10% turn left

---

## 4. What Are You Calibrating Against?

**FDOT** (Florida Department of Transportation) provides **ground-truth hourly traffic counts** for the corridor:

| Direction | FDOT Target |
|---|---|
| Westbound (WB) | **2,700 vehicles/hour** |
| Eastbound (EB) | **2,500 vehicles/hour** |

Calibration means: adjust the simulation until its output matches these real-world counts.

---

## 5. How Calibration Is Measured — GEH Statistic

The industry standard metric is the **GEH statistic** (named after Geoffrey E. Havers). It's a formula that compares simulated volume (S) to observed volume (O):

```
GEH = sqrt( 2 × (S - O)² / (S + O) )
```

It's not just a percentage — it penalizes large absolute errors on low-volume roads more than high-volume ones.

**FDOT/FHWA acceptance thresholds:**

| GEH Value | Meaning |
|---|---|
| < 1 | Excellent |
| < 3 | Good |
| **< 5** | **Acceptable (minimum standard)** |
| ≥ 5 | Fails calibration |

---

## 6. Problems Encountered and How They Were Fixed

### Problem 1 — Wrong Route Structure
**What happened:** The original routes were set up as single corridor flows (vehicles just drove straight down Glades), ignoring the real intersection geometry with turn movements.

**Fix:** Replaced with a **4-approach turn-split model** — each approach gets vehicles that split into right turns, straight, and left turns according to real proportions. Total: **6,458 vehicles** in the simulation.

---

### Problem 2 — Gridlock
**What happened:** At FDOT demand levels, the network locked up completely — vehicles couldn't move because every lane was blocked.

**Fix applied:**
- `departLane="random"` — vehicles don't all pile into the same lane at entry
- `speedDev="0.1"` and `sigma="0.5"` — adds slight variation to driver behavior so they don't all act identically (breaks up platoon bunching)
- `departSpeed="max"` — vehicles enter at full speed instead of accelerating from zero
- Deleted conflicting/broken additional files that were interfering

---

### Problem 3 — Signals Failing (Actuated → Static)
**What happened:** 3 signals in the network were set to **actuated** control (responds to detectors), but their detectors were missing. SUMO fell back to minimum green time on every phase — starving the main Glades arterial of green time and causing spillback.

**Fix:** Converted all 3 signals from actuated to **static** (fixed timing) with a **90-second cycle**, then rebalanced the phases:

| Signal | Change Made |
|---|---|
| Main cluster (Glades × Airport) | Arterial green raised from 29s → 44s; cross-street cut from 29s → 14s |
| `GS_627948357` | WB through = 36s, EB approach = 44s |
| `GS_4600210165` | Static 40/40 split (WB exit gate) |

Arterial green share went from **32% → 49%** of cycle time.

---

## 7. Final Calibration Results

| Direction | FDOT Target | SUMO Output | Error | GEH | Status |
|---|---|---|---|---|---|
| Westbound | 2,700 | 2,700 | 0% | ~0 | ✅ Excellent |
| Eastbound | 2,500 | 2,263 | -9.5% | ~4.8 | ⚠️ Passes (barely) |

**Verdict:** Meets FDOT/FHWA acceptance criteria. WB is perfect. EB is at the edge of passing.

---

## 8. Why Can't EB Hit 2,500?

This is important to understand — it's not a tuning failure, it's a **geometric constraint**.

The eastbound approach (`464986841#0`) is only **3 lanes wide**. No matter how long you give it green time, 3 lanes can only physically pass so many vehicles per hour. The ceiling is approximately **2,300–2,350 veh/hr**.

There's also a conflict at the shared signal `GS_627948357`:
- WB needs **short cycle** (90s) to prevent spillback through 3 signals in series
- EB needs **long green** to push more vehicles through
- These two needs are **in direct conflict** at the same signal

When a 120s cycle was tested to give EB more green (61s green → EB got 2,349), WB collapsed to 1,886 due to backward spillback. Net result: worse overall.

**To truly reach 2,500 EB, you would need:**
1. Widen the `464986841#0` approach to 4+ lanes (geometry change), OR
2. A full coordinated retime with offsets across all 3 signals (major redesign)

---

## 9. How to Explain the Calibration Quality Honestly

> "The base scenario meets FDOT/FHWA calibration acceptance criteria. The westbound direction is calibrated to within 0% of the FDOT count target with a GEH near zero. The eastbound direction achieves 90.5% of target volume with a GEH of approximately 4.8, which is below the 5.0 threshold required by FDOT/FHWA guidelines. The residual eastbound gap is attributable to a geometric bottleneck on the approach — a 3-lane constraint that limits throughput regardless of signal timing — rather than a modeling error."

---

## 10. What's Next — Scenarios

The base scenario is the **locked baseline**. Two alternative scenarios will be branched from it:

- **Scenario A** — (to be defined)
- **Scenario B** — (to be defined)

The point of scenarios is to test interventions (e.g., adding a lane, changing signal timing, rerouting traffic) and compare them against the base.

---

## 11. Key Files Location

```
C:\Users\fau_msenhoury\Documents\SUMO_Project\Week2-PR\week4\
├── ttestingW3.sumocfg        ← main config (run this)
├── ttestingW3.net.xml        ← road network + signals
├── custom_flows.rou.xml      ← vehicle routes and volumes
├── edge_dump.add.xml         ← tells SUMO to record counts
├── base_edgedata.xml         ← output: what SUMO actually counted
├── fdot_config.py            ← FDOT targets + edge IDs
└── scenario_engine.py        ← builds flows for scenarios
```

---

## 12. Glossary

| Term | Meaning |
|---|---|
| **Edge** | A directed road segment in SUMO (one direction of travel) |
| **GEH** | Calibration accuracy metric — must be < 5 to pass FDOT standard |
| **Actuated signal** | Traffic light that responds to vehicle detectors |
| **Static signal** | Traffic light on a fixed timed cycle |
| **Spillback** | When queue grows so long it blocks upstream intersections |
| **veh/hr** | Vehicles per hour — the unit for traffic volume |
| **FDOT** | Florida Dept. of Transportation — provides the real-world target counts |
| **Microsimulation** | Individual vehicle-level simulation (vs. aggregate/macro models) |
| **Base scenario** | The calibrated existing-conditions model, before any changes |
