import xml.etree.ElementTree as ET 
tree = ET.parse("ttestingW3.net.xml") 
root = tree.getroot() 
edges = [e.get("id") for e in root.findall("edge") if not e.get("id").startswith(":")] 
print("Valid edges found:", edges[:30]) 
