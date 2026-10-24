# 4-Agent Cooperative Architecture Package

This package contains the modular structure for the 4 dedicated cooperative agents:

## Models Breakdown

1. **`geospatial_model.py` (Agent 1: Geospatial & Transit)**
   - OSRM road network graph routing and $N \times N$ travel time matrix.

2. **`scheduling_model.py` (Agent 2: Itinerary Scheduling)**
   - Google OR-Tools (TSPTW constraint solver) for conflict-free morning, afternoon, and evening spot sequencing.

3. **`budget_model.py` (Agent 3: Budget & Expense)**
   - Mathematical allocation engine, fuel/toll calculations, and budget feasibility validator.

4. **`safety_model.py` (Agent 4: Accommodations & Safety)**
   - 2D KD-Tree spatial radius hotel search and OpenStreetMap emergency node (`hospital`, `police`) lookup.
