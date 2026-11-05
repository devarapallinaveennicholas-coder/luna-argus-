"""Project Luna Argus - Smart Parking IoT Simulator.
Flask backend: validates telemetry, stores records in SQLite, serves the dashboard.
"""
import csv
import io
import sqlite3
from datetime import datetime, timezone

from flask import Flask, Response, g, jsonify, render_template, request

import config

app = Flask(__name__)
app.config["DB_PATH"] = config.DB_PATH


def db():
    if "db" not in g:
        conn = sqlite3.connect(app.config["DB_PATH"])
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def all_bay_ids():
    return [f"{z}{n}" for z in config.ZONES for n in range(1, config.BAYS_PER_ZONE + 1)]


def init_db():
    conn = sqlite3.connect(app.config["DB_PATH"])
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bays(
            bay_id TEXT PRIMARY KEY,
            occupied INTEGER NOT NULL DEFAULT 0,
            distance_cm REAL,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bay_id TEXT NOT NULL,
            occupied INTEGER NOT NULL,
            distance_cm REAL,
            source TEXT,
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
    """)
    for bay in all_bay_ids():
        conn.execute(
            "INSERT OR IGNORE INTO bays(bay_id, occupied, updated_at) VALUES(?,0,?)",
            (bay, now()),
        )
    conn.commit()
    conn.close()


def parse_reading(data):
    """Return (bay_id, occupied, distance, error)."""
    bay = str(data.get("bay_id", "")).strip().upper()
    if bay not in all_bay_ids():
        return None, None, None, ("unknown bay_id", 404)

    distance = data.get("distance_cm")
    if distance is not None:
        try:
            distance = float(distance)
        except (TypeError, ValueError):
            return None, None, None, ("distance_cm must be a number", 400)
        if not 0 <= distance <= 500:
            return None, None, None, ("distance_cm must be between 0 and 500", 400)
        return bay, int(distance < config.OCCUPIED_BELOW_CM), distance, None

    if "occupied" in data:
        return bay, int(bool(data["occupied"])), None, None
    return None, None, None, ("send distance_cm or occupied", 400)


def summary(rows):
    total = len(rows)
    occupied = sum(r["occupied"] for r in rows)
    return {
        "total": total,
        "occupied": occupied,
        "available": total - occupied,
        "utilisation": round(100 * occupied / total, 1) if total else 0,
    }


@app.route("/")
def index():
    return render_template("index.html", stale_after=config.STALE_AFTER_SECONDS)


@app.post("/api/telemetry")
def telemetry():
    payload = request.get_json(silent=True) or {}
    bay, occupied, distance, error = parse_reading(payload)
    if error:
        return jsonify(error=error[0]), error[1]

    previous = db().execute(
        "SELECT occupied FROM bays WHERE bay_id=?", (bay,)
    ).fetchone()["occupied"]
    changed = previous != occupied
    ts = now()
    db().execute(
        "UPDATE bays SET occupied=?, distance_cm=?, updated_at=? WHERE bay_id=?",
        (occupied, distance, ts, bay),
    )
    if changed:
        source = str(payload.get("source", "sensor"))[:20]
        db().execute(
            "INSERT INTO events(bay_id, occupied, distance_cm, source, ts) VALUES(?,?,?,?,?)",
            (bay, occupied, distance, source, ts),
        )
    db().commit()
    return jsonify(bay_id=bay, occupied=bool(occupied), changed=changed)


@app.get("/api/bays")
def bays():
    rows = [dict(r) for r in db().execute("SELECT * FROM bays ORDER BY bay_id")]
    latest = max((r["updated_at"] for r in rows), default=None)
    return jsonify(
        bays=rows,
        last_update=latest,
        server_time=now(),
        **summary(rows),
    )


@app.get("/api/bays/<bay_id>")
def bay_detail(bay_id):
    bay = bay_id.upper()
    row = db().execute("SELECT * FROM bays WHERE bay_id=?", (bay,)).fetchone()
    if not row:
        return jsonify(error="unknown bay_id"), 404
    history = db().execute(
        "SELECT occupied, distance_cm, source, ts FROM events "
        "WHERE bay_id=? ORDER BY id DESC LIMIT 20",
        (bay,),
    ).fetchall()
    return jsonify(bay=dict(row), history=[dict(h) for h in history])


@app.get("/api/events")
def events():
    rows = db().execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT ?",
        (config.EVENT_LOG_LIMIT,),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/api/history")
def history():
    rows = db().execute(
        "SELECT substr(ts, 12, 2) AS hour, COUNT(*) AS arrivals "
        "FROM events WHERE occupied=1 GROUP BY hour ORDER BY hour"
    ).fetchall()
    counts = {r["hour"]: r["arrivals"] for r in rows}
    return jsonify([
        {"hour": f"{h:02d}", "arrivals": counts.get(f"{h:02d}", 0)}
        for h in range(24)
    ])


@app.get("/api/export.csv")
def export_csv():
    rows = db().execute(
        "SELECT ts, bay_id, occupied, distance_cm, source FROM events ORDER BY id"
    ).fetchall()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["timestamp_utc", "bay_id", "state", "distance_cm", "source"])
    for r in rows:
        writer.writerow([
            r["ts"], r["bay_id"],
            "occupied" if r["occupied"] else "available",
            r["distance_cm"], r["source"],
        ])
    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=luna_argus_events.csv"},
    )


@app.post("/api/reset")
def reset():
    db().execute(
        "UPDATE bays SET occupied=0, distance_cm=NULL, updated_at=?",
        (now(),),
    )
    db().execute("DELETE FROM events")
    db().commit()
    return jsonify(ok=True)


@app.get("/api/health")
def health():
    return jsonify(status="ok", time=now())


# Render starts the app through Gunicorn, which imports this module rather than
# running it as __main__. Initialise the SQLite tables during import as well.
init_db()


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
