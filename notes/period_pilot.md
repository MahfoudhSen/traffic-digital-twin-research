# period_pilot.md

I tested different `--period` values in randomTrips.py to see how traffic changes in the simulation.

## period = 4

Traffic becomes heavy fast and the intersection gets congested early.

## period = 6

Best balance. You get visible traffic and realistic congestion around ~600s without overloading the network.

## period = 10

Traffic is too light and doesn’t create meaningful congestion.

## final choice

I chose period = 6 because it gives the most realistic and useful traffic behavior for analysis.
