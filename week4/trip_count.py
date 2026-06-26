import xml.etree.ElementTree as ET

#open this file and load it use sumo 

# tree is a varible that stroes the data of the file and root is the root element of the file

tree = ET.parse("trips.trips.xml")


root = tree.getroot()
# and root is a variable that stores the root element of the file 
# we need tree for parsing the file and root for accesing the data in the file
# we need to count the number of trips in the file and print it


#find all trip elements in the file and count them


trips = root.findall(".//trip")


#count the number of trips in the file 


total_trip = len(trips)

#print resuelt

print("total number of trips generated in the fle is :", total_trip)


