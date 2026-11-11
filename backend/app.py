import os

# Let Python find PostgreSQL's libpq.dll (needed before importing psycopg)
if os.name == "nt":
    for p in (r"C:\Program Files\PostgreSQL\18\bin",
              r"C:\Program Files\PostgreSQL\17\bin",
              r"C:\Program Files\PostgreSQL\16\bin"):
        if os.path.isdir(p):
            os.add_dll_directory(p)
            os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]

from flask import Flask, jsonify, request, send_from_directory
import psycopg
from psycopg.rows import dict_row

app = Flask(__name__, static_folder="../frontend", static_url_path="/static")


def get_conn():
    return psycopg.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "medf_gis"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", ""),
    )


def run(sql, params=None):
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def feature_collection(inner_sql, params=None):
    """Wrap a query that returns a 'geom' column into a GeoJSON FeatureCollection."""
    sql = f"""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(t.geom)::json,
                'properties', to_jsonb(t) - 'geom'
            )), '[]'::json)
        ) AS fc
        FROM ({inner_sql}) t
    """
    return run(sql, params)[0]["fc"]


@app.route("/")
def home():
    return send_from_directory("../frontend", "index.html")


@app.route("/api/service-points")
def service_points():
    return jsonify(feature_collection(
        "SELECT service_point_id, name, point_type, district, geom FROM service_points"))


@app.route("/api/clients")
def clients():
    return jsonify(feature_collection("""
        SELECT client_id, name, group_name, nearest_point, district,
               dist_km::float AS dist_km, dist_band, underserved, status,
               amount::float AS amount, arrears_amount::float AS arrears_amount, geom
        FROM client_access"""))


@app.route("/api/stats/bands")
def stats_bands():
    return jsonify(run("""
        SELECT dist_band,
               COUNT(*)::int AS clients,
               COUNT(*) FILTER (WHERE status <> 'performing')::int AS in_arrears,
               ROUND(100.0 * COUNT(*) FILTER (WHERE status <> 'performing') / COUNT(*), 1)::float AS pct_in_arrears,
               COALESCE(SUM(arrears_amount), 0)::float AS total_arrears_mk
        FROM client_access
        GROUP BY dist_band ORDER BY dist_band"""))

def execute(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


@app.route("/api/stats/districts")
def stats_districts():
    thr = float(request.args.get("threshold", 10))
    return jsonify(run("""
        SELECT district,
               COUNT(*)::int AS total_clients,
               COUNT(*) FILTER (WHERE dist_km > %s)::int AS underserved_clients,
               COALESCE(SUM(arrears_amount), 0)::float AS total_arrears_mk
        FROM client_access
        GROUP BY district ORDER BY underserved_clients DESC""", (thr,)))


@app.route("/api/candidate")
def candidate():
    try:
        lon = float(request.args["lon"])
        lat = float(request.args["lat"])
        radius_km = float(request.args.get("radius_km", 8))
        thr = float(request.args.get("threshold", 10))
    except (KeyError, ValueError):
        return jsonify({"error": "lon and lat are required numbers"}), 400
    pt = "ST_SetSRID(ST_MakePoint(%s, %s), 4326)"
    row = run(f"""
        SELECT COUNT(*)::int AS underserved_reached,
               COALESCE(SUM(arrears_amount), 0)::float AS arrears_mk
        FROM client_access
        WHERE dist_km > %s
          AND ST_DWithin(geom::geography, {pt}::geography, %s)""",
        (thr, lon, lat, radius_km * 1000))[0]
    near = run(f"""
        SELECT name, (ST_Distance(geom::geography, {pt}::geography) / 1000.0)::float AS km
        FROM service_points
        WHERE point_type IN ('branch','mobile')
        ORDER BY geom <-> {pt} LIMIT 1""", (lon, lat, lon, lat))[0]
    row.update(nearest_point=near["name"], nearest_km=near["km"], radius_km=radius_km)
    return jsonify(row)


@app.route("/api/recommend")
def recommend():
    import math
    thr = float(request.args.get("threshold", 10))
    radius_km = float(request.args.get("radius_km", 8))
    n = int(request.args.get("n", 3))
    rows = run("""
        WITH u AS (SELECT client_id, geom, arrears_amount FROM client_access WHERE dist_km > %s)
        SELECT ST_X(a.geom) AS lon, ST_Y(a.geom) AS lat,
               COUNT(*)::int AS reached,
               COALESCE(SUM(b.arrears_amount), 0)::float AS arrears_mk
        FROM u a JOIN u b ON ST_DWithin(a.geom::geography, b.geom::geography, %s)
        GROUP BY a.client_id, a.geom
        ORDER BY reached DESC, arrears_mk DESC LIMIT 100""", (thr, radius_km * 1000))
    picks = []
    for r in rows:   # keep picks apart so they don't overlap
        far = all(math.hypot((r["lon"] - p["lon"]) * 111 * math.cos(math.radians(r["lat"])),
                             (r["lat"] - p["lat"]) * 111) >= radius_km * 1.5 for p in picks)
        if far:
            picks.append(r)
        if len(picks) == n:
            break
    return jsonify(picks)


@app.route("/api/save-candidate", methods=["POST"])
def save_candidate():
    d = request.get_json(force=True)
    try:
        lon, lat = float(d["lon"]), float(d["lat"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "lon and lat required"}), 400
    name = (d.get("name") or "Candidate site")[:80]
    execute("""INSERT INTO service_points (name, point_type, geom)
               VALUES (%s, 'candidate', ST_SetSRID(ST_MakePoint(%s, %s), 4326))""",
            (name, lon, lat))
    return jsonify({"saved": True})


@app.route("/api/clear-candidates", methods=["POST"])
def clear_candidates():
    execute("DELETE FROM service_points WHERE point_type = 'candidate'")
    return jsonify({"cleared": True})


if __name__ == "__main__":
    app.run(debug=True)