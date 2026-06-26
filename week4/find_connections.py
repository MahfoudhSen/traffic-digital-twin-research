import xml.etree.ElementTree as ET 
tree = ET.parse("ttestingW3.net.xml") 
root = tree.getroot() 
conn_west = [c.get("to") for c in root.findall("connection") if c.get("from") == "1234122485#0"] 
conn_east = [c.get("to") for c in root.findall("connection") if c.get("from") == "1234122500#0"] 
print("Westbound flows into:", list(set(conn_west))) 
print("Eastbound flows into:", list(set(conn_east))) 
