# \# MEDF Service Access and Repayment Risk Map

# 

# A database-driven web GIS (PostgreSQL/PostGIS + Flask + Leaflet) that shows which

# areas served by the Malawi Enterprise Development Fund (MEDF) are underserved,

# and how repayment performance relates to distance from the nearest service point.

# 

# \*\*Note:\*\* all client and loan data is synthetic. No real MEDF data is included.

# 

# \## Problem

# 

# Many rural Malawians are not fully served by MEDF loan products. Long distances to

# the nearest branch or field officer raise the cost of accessing loans and making

# repayments, which limits loan uptake and contributes to repayment problems.

# MEDF lacks a spatial decision-support tool to show which areas are underserved and

# where new mobile banking points or satellite offices should be placed.

# 

# \## What the system does

# 

# 1\. Measures each client's distance to the nearest service point

# 2\. Classifies clients as served or underserved (more than 10 km from a service point)

# 3\. Compares repayment performance across distance bands (0-5, 5-10, 10+ km)

# 4\. Helps identify candidate sites for new service points

# 

# \## Setup (work in progress)

# 

# 1\. Install PostgreSQL and PostGIS

# 2\. Create a database named `medf\_gis`

# 3\. Enable PostGIS and run `database/db\_setup.sql` in pgAdmin's Query Tool

# 4\. Backend and frontend instructions will be added

# 

# \## Project structure

# 

# \- `database/` : schema and synthetic data script

# \- `backend/`  : Flask API (in progress)

# \- `frontend/` : Leaflet map (in progress)

# \- `docs/`     : screenshots

