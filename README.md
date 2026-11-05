# Project Luna Argus – Smart Parking IoT Simulator

A software-only smart parking demonstration built with Flask, SQLite, HTML, CSS and JavaScript. It simulates 24 parking bays across zones A, B and C.

## Deploy on Render

Create a **Python Web Service** connected to this repository and use:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`
- **Root directory:** leave blank

The Flask application initialises its SQLite tables when Gunicorn imports the app.

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in a browser. In a second terminal, run:

```bash
python simulator.py
```

## Send virtual sensor data to the deployed website

```bash
python simulator.py --url https://YOUR-RENDER-SERVICE.onrender.com
```

Keep the simulator terminal open while demonstrating the dashboard.

## API endpoints

- `GET /` – dashboard
- `GET /api/health` – health check
- `GET /api/bays` – current bay status and totals
- `POST /api/telemetry` – submit a sensor reading
- `GET /api/events` – recent state changes
- `GET /api/history` – arrivals grouped by hour (UTC)
- `GET /api/export.csv` – download event log
- `POST /api/reset` – reset all bays

Example telemetry JSON:

```json
{"bay_id":"A1","distance_cm":12.5,"source":"sensor"}
```

A distance below 30 cm marks the bay occupied.

## Note about storage

The included SQLite database is suitable for a classroom demonstration. Render's local filesystem may be ephemeral, so records can be lost when the service restarts or redeploys. Use a persistent disk or managed database if long-term storage is required.
