"""Central settings for Project Luna Argus."""
import os

DB_PATH = os.environ.get("DATABASE_PATH", "parking.db")
ZONES = "ABC"            # A1..A8, B1..B8, C1..C8 (24 bays)
BAYS_PER_ZONE = 8
OCCUPIED_BELOW_CM = 30   # Below this distance = vehicle present
STALE_AFTER_SECONDS = 15
EVENT_LOG_LIMIT = 30
