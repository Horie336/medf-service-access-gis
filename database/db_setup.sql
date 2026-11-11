-- MEDF Service Access & Repayment Risk: database setup (PostgreSQL + PostGIS)
-- Branch locations are MEDF Eastern Region branches.
-- ALL CLIENT AND LOAN DATA IS SYNTHETIC. Arrears levels are set to reflect the
-- scale of the repayment challenge, and the distance-arrears pattern is built in
-- to illustrate the method. It is not a finding about real clients.

CREATE EXTENSION IF NOT EXISTS postgis;

DROP VIEW  IF EXISTS client_access;
DROP TABLE IF EXISTS loans;
DROP TABLE IF EXISTS clients;
DROP TABLE IF EXISTS service_points;

CREATE TABLE service_points (
  service_point_id SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  point_type  TEXT NOT NULL DEFAULT 'branch'
              CHECK (point_type IN ('branch','mobile','candidate')),
  district    TEXT,
  region      TEXT,
  geom        GEOMETRY(Point, 4326) NOT NULL
);

CREATE TABLE clients (
  client_id   SERIAL PRIMARY KEY,
  name        TEXT,
  group_name  TEXT,
  geom        GEOMETRY(Point, 4326) NOT NULL
);

CREATE TABLE loans (
  loan_id        SERIAL PRIMARY KEY,
  client_id      INT NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
  amount         NUMERIC(14,2) NOT NULL,
  status         TEXT NOT NULL
                 CHECK (status IN ('performing','late','default')),
  arrears_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
  disbursed_date DATE
);

CREATE INDEX idx_sp_geom      ON service_points USING GIST (geom);
CREATE INDEX idx_clients_geom ON clients        USING GIST (geom);
CREATE INDEX idx_loans_client ON loans (client_id);

INSERT INTO service_points (name, point_type, district, region, geom) VALUES
 ('Zomba Branch',    'branch', 'Zomba',    'Eastern', ST_SetSRID(ST_MakePoint(35.3149392, -15.3865634), 4326)),
 ('Liwonde Branch',  'branch', 'Machinga', 'Eastern', ST_SetSRID(ST_MakePoint(35.2280368, -15.0690576), 4326)),
 ('Balaka Branch',   'branch', 'Balaka',   'Eastern', ST_SetSRID(ST_MakePoint(34.9553063, -14.9894658), 4326)),
 ('Mangochi Branch', 'branch', 'Mangochi', 'Eastern', ST_SetSRID(ST_MakePoint(35.271537,  -14.480091),  4326)),
 ('Ntcheu Branch',   'branch', 'Ntcheu',   'Eastern', ST_SetSRID(ST_MakePoint(34.6372881, -14.8162265), 4326));

SELECT setseed(0.42);

-- 300 synthetic clients, 1-25 km from the branches
WITH numbered AS (
  SELECT service_point_id, geom,
         ROW_NUMBER() OVER (ORDER BY service_point_id) AS rn,
         COUNT(*) OVER () AS total
  FROM service_points
  WHERE point_type = 'branch'
),
raw AS (
  SELECT g,
         n.geom AS bgeom,
         1 + 24 * random()        AS d_km,
         2 * pi() * random()      AS ang
  FROM generate_series(1, 300) AS g
  JOIN numbered n ON n.rn = 1 + (g % n.total)
  OFFSET 0
)
INSERT INTO clients (name, group_name, geom)
SELECT 'Client ' || g,
       'Group ' || (1 + floor(random() * 40))::int,
       ST_SetSRID(ST_MakePoint(
         ST_X(bgeom) + d_km * sin(ang) / (111.0 * cos(radians(ST_Y(bgeom)))),
         ST_Y(bgeom) + d_km * cos(ang) / 111.0
       ), 4326)
FROM raw;

-- Synthetic loans. Chance of arrears = 33% + 3% per km, capped at 88%.
-- Clients in arrears owe 50-90% of their loan; 40% of them are in default.
WITH base AS (
  SELECT c.client_id,
         n.km,
         round((50000 + random() * 1450000)::numeric, -3)  AS amount,
         random()                                          AS r_status,
         random()                                          AS r_default,
         0.5 + random() * 0.4                              AS arrears_share,
         (CURRENT_DATE - (random() * 730)::int)            AS disbursed
  FROM clients c
  CROSS JOIN LATERAL (
    SELECT ST_Distance(c.geom::geography, sp.geom::geography) / 1000.0 AS km
    FROM service_points sp
    ORDER BY c.geom <-> sp.geom
    LIMIT 1
  ) n
  OFFSET 0
)
INSERT INTO loans (client_id, amount, status, arrears_amount, disbursed_date)
SELECT client_id,
       amount,
       CASE WHEN r_status < LEAST(0.33 + 0.03 * km, 0.88)
            THEN CASE WHEN r_default < 0.40 THEN 'default' ELSE 'late' END
            ELSE 'performing' END,
       CASE WHEN r_status < LEAST(0.33 + 0.03 * km, 0.88)
            THEN round((amount * arrears_share)::numeric, -2)
            ELSE 0 END,
       disbursed
FROM base;

CREATE VIEW client_access AS
SELECT c.client_id,
       c.name,
       c.group_name,
       c.geom,
       n.service_point_id,
       n.sp_name        AS nearest_point,
       n.district,
       ROUND(n.km::numeric, 2) AS dist_km,
       CASE WHEN n.km < 5  THEN '0-5 km'
            WHEN n.km < 10 THEN '5-10 km'
            ELSE '10+ km' END AS dist_band,
       (n.km > 10)      AS underserved,
       l.amount,
       l.status,
       l.arrears_amount
FROM clients c
JOIN loans l ON l.client_id = c.client_id
CROSS JOIN LATERAL (
  SELECT sp.service_point_id, sp.name AS sp_name, sp.district,
         ST_Distance(c.geom::geography, sp.geom::geography) / 1000.0 AS km
  FROM service_points sp
  WHERE sp.point_type IN ('branch','mobile')
  ORDER BY c.geom <-> sp.geom
  LIMIT 1
) n;