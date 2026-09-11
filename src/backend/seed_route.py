"""
seed_route.py - Reset and Seed Route Data for Delivery Intelligence Platform
Clears delivered statuses/proofs and initializes 6 active pending packages.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
MANIFEST_FILE = os.path.join(DATA_DIR, "manifest.json")
PROOFS_FILE = os.path.join(DATA_DIR, "proofs.json")

INITIAL_STOPS = [
    {
        "package_id": "pkg-001",
        "recipient_name": "Marcus Vance",
        "address": "233 S Wacker Dr, Chicago, IL 60606",
        "suite": "Ste 3400",
        "latitude": 41.878876,
        "longitude": -87.635915,
        "status": "pending",
        "priority": "standard",
        "time_window": "09:00 - 11:00",
        "package_type": "Document Envelope",
        "notes": "Deliver to 34th-floor security desk. Signature required."
    },
    {
        "package_id": "pkg-002",
        "recipient_name": "Elena Rostova",
        "address": "111 N State St, Chicago, IL 60602",
        "suite": "Floor 7",
        "latitude": 41.883733,
        "longitude": -87.627918,
        "status": "pending",
        "priority": "express",
        "time_window": "09:30 - 11:30",
        "package_type": "Fragile Box",
        "notes": "Retail receiving entrance off Washington St."
    },
    {
        "package_id": "pkg-003",
        "recipient_name": "Derrick Sterling",
        "address": "875 N Michigan Ave, Chicago, IL 60611",
        "suite": "Apt 42B",
        "latitude": 41.898818,
        "longitude": -87.624128,
        "status": "pending",
        "priority": "standard",
        "time_window": "10:00 - 12:30",
        "package_type": "Parcel Box",
        "notes": "Leave with front desk concierge."
    },
    {
        "package_id": "pkg-004",
        "recipient_name": "Alicia Mendez",
        "address": "600 E Grand Ave, Chicago, IL 60611",
        "suite": "Dock B",
        "latitude": 41.891712,
        "longitude": -87.608558,
        "status": "pending",
        "priority": "standard",
        "time_window": "11:00 - 13:00",
        "package_type": "Crate (Medium)",
        "notes": "Navy Pier delivery dock. Back up bay 4."
    },
    {
        "package_id": "pkg-005",
        "recipient_name": "Kofi Mensah",
        "address": "301 S Columbus Dr, Chicago, IL 60604",
        "suite": "South Entrance",
        "latitude": 41.880564,
        "longitude": -87.621887,
        "status": "pending",
        "priority": "express",
        "time_window": "11:30 - 13:30",
        "package_type": "Temperature Controlled",
        "notes": "Handle with care. High priority bio-sample."
    },
    {
        "package_id": "pkg-006",
        "recipient_name": "Rachel Zhao",
        "address": "1200 S DuSable Lake Shore Dr, Chicago, IL 60605",
        "suite": "Staff Entry",
        "latitude": 41.866261,
        "longitude": -87.616980,
        "status": "pending",
        "priority": "standard",
        "time_window": "13:00 - 15:00",
        "package_type": "Insulated Pouch",
        "notes": "Museum campus delivery entrance. Call on arrival."
    }
]


def seed_data():
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(INITIAL_STOPS, f, indent=2)
    print(f"[+] Manifest seeded: {len(INITIAL_STOPS)} pending stops -> {MANIFEST_FILE}")

    with open(PROOFS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)
    print(f"[+] Proofs cleared: 0 completed records -> {PROOFS_FILE}")

    print("\nRoute reset complete. System ready for live testing.")


if __name__ == "__main__":
    seed_data()