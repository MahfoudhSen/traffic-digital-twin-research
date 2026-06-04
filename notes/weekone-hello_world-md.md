In SUMO, a traffic simulation is built using several different types of files, each with a specific role. These files work together to define the road network, the vehicles, the simulation setup, and the results produced.

.net.xml (Network File)

The .net.xml file contains the road network used in the simulation. It defines the structure of the streets, including intersections, lanes, speed limits, traffic signals, and how roads are connected. This file represents the physical layout of the traffic system being simulated.

.rou.xml (Route File)

The .rou.xml file defines the vehicles in the simulation and the routes they take. It specifies how many vehicles exist, their departure times, and the paths they follow through the road network. This file controls the traffic demand in the simulation.

.sumocfg (Configuration File)

The .sumocfg file is the main configuration file that runs the simulation. It tells SUMO which network file and route file to use, along with other settings such as output options. It acts like the “control center” of the simulation.

.add.xml (Additional File)

The .add.xml file is used to include extra features that are not part of the main network or routes. This can include traffic detectors, edge data collection, traffic lights logic, or other advanced simulation elements. It helps extend the simulation without changing the main files.

Output Files (tripinfo and edgeData)

After running a simulation, SUMO generates output files. The tripinfo file contains information about each vehicle, such as travel time, waiting time, and distance traveled. The edgeData file contains aggregated data for each road segment, such as vehicle counts, average speed, and congestion levels.

Together, these files allow us to build, run, and analyze traffic simulations in a structured way.

