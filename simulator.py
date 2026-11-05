"""Virtual ultrasonic sensors for Project Luna Argus.

Local use:
    python simulator.py

Hosted use:
    python simulator.py --url https://YOUR-SERVICE.onrender.com
"""
import argparse
import json
import random
import time
import urllib.request
from datetime import datetime

import config

BAYS = [
    f"{z}{n}"
    for z in config.ZONES
    for n in range(1, config.BAYS_PER_ZONE + 1)
]


def arrival_bias(hour):
    if 12 <= hour < 15:
        return 0.75
    if 9 <= hour < 18:
        return 0.5
    return 0.3


def read_distance(occupied):
    return round(
        random.uniform(5, 25) if occupied else random.uniform(80, 200),
        1,
    )


def send(url, bay, distance):
    payload = json.dumps({
        "bay_id": bay,
        "distance_cm": distance,
        "source": "virtual-sensor",
    }).encode()
    req = urllib.request.Request(
        url,
        payload,
        {"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        response.read()


def main():
    parser = argparse.ArgumentParser(description="Luna Argus virtual sensors")
    parser.add_argument("--url", default="http://127.0.0.1:5000",
                        help="Base URL of the Flask website")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="2.0 = twice as fast")
    parser.add_argument("--seed", type=int, help="Random seed for repeatable demos")
    args = parser.parse_args()

    if args.speed <= 0:
        parser.error("--speed must be greater than zero")
    if args.seed is not None:
        random.seed(args.seed)

    endpoint = args.url.rstrip("/") + "/api/telemetry"
    state = {bay: random.random() < 0.3 for bay in BAYS}
    print(f"Luna Argus simulator: {len(BAYS)} virtual sensors")
    print(f"Sending readings to: {endpoint}")
    print("Press Ctrl+C to stop.")

    try:
        for bay in BAYS:
            send(endpoint, bay, read_distance(state[bay]))

        while True:
            bay = random.choice(BAYS)
            if random.random() < 0.5:
                state[bay] = random.random() < arrival_bias(datetime.now().hour)
            send(endpoint, bay, read_distance(state[bay]))
            print(
                f"{datetime.now():%H:%M:%S}  {bay:<3} "
                f"{'OCCUPIED' if state[bay] else 'FREE'}"
            )
            time.sleep(random.uniform(0.8, 2.5) / args.speed)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")
    except OSError as exc:
        print("Backend unreachable. Check the website URL and try again:", exc)


if __name__ == "__main__":
    main()
