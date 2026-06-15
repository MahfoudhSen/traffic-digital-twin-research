import xml.etree.ElementTree as ET

FILE = "base_edgedata.xml"

# Put ONLY the edge(s) that represent the FDOT count location
# (usually 1–3 straight-through edges max, not all splits)
COUNT_EDGES = {
    "1234122485#2",
    "741687503#0",
    "543692100#0",
    "534834577#1"
}

def main():
    tree = ET.parse(FILE)
    root = tree.getroot()

    edges = root.findall(".//edge")

    print("Total edges in file:", len(edges))

    total_flow = 0.0

    print("\n--- Selected FDOT edges ---")

    for edge in edges:
        edge_id = edge.get("id")

        if edge_id in COUNT_EDGES:
            flow = float(edge.get("flow", 0))

            print(f"edge: {edge_id} | flow: {flow}")

            total_flow += flow

    print("\n==============================")
    print("TOTAL FLOW (FDOT edges):", total_flow)
    print("==============================\n")

    # Optional: simple interpretation
    if total_flow < 1000:
        print(" Too LOW vs FDOT (likely under-generating demand)")
    elif total_flow > 6000:
        print(" Too HIGH vs FDOT (likely over-generating demand)")
    else:
        print(" Likely in reasonable FDOT range (check ±10% manually)")

if __name__ == "__main__":
    main()



