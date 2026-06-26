import xml.etree.ElementTree as ET
import sys

try:
    tree = ET.parse('base_edgedata.xml') 
    root = tree.getroot()
except ET.ParseError:
    print("Error: base_edgedata.xml is incomplete. Please let the SUMO simulation finish running first.")
    sys.exit()

total_westbound = 0
total_eastbound = 0

# FDOT hourly targets (vehicles/hour)
TARGET_WB = 2700
TARGET_EB = 2500

# Measure TRUE hourly throughput: only the first interval (0 - 3600s).
# We intentionally ignore any later interval(s) (3600+) that only drain the
# backlog of vehicles still queued after the demand window closed.
intervals = root.findall('interval')
if not intervals:
    print("Error: no <interval> found in base_edgedata.xml.")
    sys.exit()

first_interval = intervals[0]

# Filter out everything except your Glades Road IDs (first hour only)
for edge in first_interval.findall('edge'):
    edge_id = edge.get('id')
    vehicles = int(float(edge.get('entered', 0)))

    # Westbound Glades Road
    if edge_id == "1234122485#0":
        total_westbound += vehicles

    # Eastbound Glades Road (checking your network's main EB IDs)
    elif edge_id == "543692100#0":
        total_eastbound += vehicles

# Clear output: Only printing Glades Road directions (first hour, 0-3600s)
i_begin = first_interval.get('begin')
i_end = first_interval.get('end')

print("\n====================================")
print("     GLADES ROAD VEHICLE TOTALS     ")
print(f"   interval {i_begin}-{i_end}s (1 hour)")
print("====================================")
print(f"Glades Westbound: {total_westbound} / {TARGET_WB}")
print(f"Glades Eastbound: {total_eastbound} / {TARGET_EB}")
print("====================================\n")