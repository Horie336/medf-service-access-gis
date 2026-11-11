# \# MEDF Service Access and Repayment Risk Map

# 

# A database-driven web GIS (PostgreSQL/PostGIS + Flask + Leaflet) that shows which

# areas served by the Malawi Enterprise Development Fund (MEDF) are underserved,

# and how repayment performance relates to distance from the nearest service point.

# 

# \*\*Note:\*\* All client and loan data is synthetic.** No real MEDF data is included. Arrears
levels are set to reflect the scale of the repayment challenge, and the
distance-arrears pattern is built into the data to illustrate the method. It is
not a finding about real clients or MEDF's actual portfolio..

# 

# \## Problem

# 

Many rural Malawians, both existing and potential clients of the Malawi Enterprise
Development Fund (MEDF), are not fully served by its loan products. Long distances
to the nearest branch or field officer service point raise the cost of accessing
loans, making repayments and attending group meetings, which limits loan uptake.
Even among those who are served, repayment is a serious challenge: management
reports significant loan arrears in the Eastern Region, and distance between
clients and service points is one contributing factor. MEDF currently lacks a
spatial decision-support tool that shows which areas are well served and which
are underserved, and how repayment performance relates to distance. As a result,
decisions on where to place new mobile banking points or satellite offices are
made without strong geographic evidence.

# 

# \## What the system does

# 

# 1. Measures each client's distance to the nearest service point (PostGIS `<->` and `ST_Distance`)
2. Classifies clients as underserved beyond an adjustable distance threshold (default 10 km)
3. Compares arrears rates across distance bands (0-5, 5-10, 10+ km)
4. Counts underserved clients by the district of their nearest service point
5. Candidate site tool: click the map to see how many underserved clients, and how
   much arrears exposure, fall within a chosen radius of a proposed new point
   (`ST_DWithin`), and the nearest existing service point
6. Saves chosen candidate sites to the database (`service_points` table)
7. Recommends the top 3 sites that reach the most underserved clients
# 

# \## Setup (work in progress)

# 
1. Install PostgreSQL and PostGIS, and create a database (this project used the
   name `MEDF GIS`; any name works if you set `DB_NAME` in step 4).
2. Run `database/db_setup.sql` in pgAdmin's Query Tool or with `psql`.
   It creates the tables, loads the service points, generates 300 synthetic clients
   and loans, and creates the `client_access` view.
   The five service points are MEDF Eastern Region branches (Zomba, Liwonde,
   Balaka, Mangochi and Ntcheu); the client and loan data around them is synthetic.
3. Make sure Python 3 has Flask and psycopg (version 3) installed:
   ```
   pip install flask "psycopg[binary]"
   ```
4. Set the database connection and start the app (Windows Command Prompt):
   ```
   cd backend
   set DB_NAME=MEDF GIS
   set DB_PASSWORD=your_password
   python app.py
   ```
   Optional settings: `DB_HOST`, `DB_PORT`, `DB_USER`. The defaults are localhost, 5432 and postgres.
5. Open http://127.0.0.1:5000

# \ ## API endpoints

| Endpoint | Returns |
|---|---|
| `/api/service-points` | Service points (GeoJSON) |
| `/api/clients` | Clients with distance, band and loan fields (GeoJSON) |
| `/api/stats/bands` | Arrears rate and totals by distance band |
| `/api/stats/districts?threshold=..` | Underserved clients and arrears by district of nearest service point |
| `/api/candidate?lon=..&lat=..&radius_km=..&threshold=..` | Underserved clients and arrears reached by a proposed point, and the nearest existing service point |
| `/api/recommend?threshold=..&radius_km=..&n=3` | Top suggested sites |
| `/api/save-candidate` (POST) | Saves a candidate site to the database |
| `/api/clear-candidates` (POST) | Removes saved candidate sites |
## Project structure

# 

# \- `database/` : schema and synthetic data script

# \- `backend/`  : Flask API (in progress)

# \- `frontend/` : Leaflet map (in progress)

# \- `docs/`     : screenshots

