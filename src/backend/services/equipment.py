import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# In-memory inventory store (seeded with Chicago Depot assets)
EQUIPMENT_INVENTORY: Dict[str, Dict[str, Any]] = {
    "EQ-SCN-101": {
        "id": "EQ-SCN-101",
        "barcode": "SCN-TC57-101",
        "name": "Zebra TC57 Handheld Scanner",
        "type": "SCANNER",
        "serial_number": "ZB-99381-A",
        "status": "CHECKED_OUT",
        "assigned_driver_id": "D001",
        "battery_level": 94,
        "last_inspected": "2026-08-28T10:00:00Z",
        "checked_out_at": "2026-08-31T07:15:00Z",
    },
    "EQ-SCN-102": {
        "id": "EQ-SCN-102",
        "barcode": "SCN-TC57-102",
        "name": "Zebra TC57 Handheld Scanner",
        "type": "SCANNER",
        "serial_number": "ZB-99382-B",
        "status": "AVAILABLE",
        "assigned_driver_id": None,
        "battery_level": 100,
        "last_inspected": "2026-08-30T14:30:00Z",
        "checked_out_at": None,
    },
    "EQ-VAN-501": {
        "id": "EQ-VAN-501",
        "barcode": "VAN-SPRINTER-501",
        "name": "Mercedes Sprinter 2500 (Van #5)",
        "type": "VEHICLE",
        "serial_number": "VIN-4JGDA5EB8PA102938",
        "status": "CHECKED_OUT",
        "assigned_driver_id": "D001",
        "odometer_miles": 41280,
        "fuel_percent": 88,
        "last_inspected": "2026-08-29T08:00:00Z",
        "checked_out_at": "2026-08-31T07:10:00Z",
    },
    "EQ-VAN-502": {
        "id": "EQ-VAN-502",
        "barcode": "VAN-SPRINTER-502",
        "name": "Ford Transit Cargo 350 (Van #6)",
        "type": "VEHICLE",
        "serial_number": "VIN-1FTYR2Y84MKA49281",
        "status": "AVAILABLE",
        "assigned_driver_id": None,
        "odometer_miles": 28450,
        "fuel_percent": 95,
        "last_inspected": "2026-08-30T16:00:00Z",
        "checked_out_at": None,
    },
    "EQ-POS-301": {
        "id": "EQ-POS-301",
        "barcode": "POS-SQUARE-301",
        "name": "Square Terminal Card Reader",
        "type": "POS_TERMINAL",
        "serial_number": "SQ-88192-K",
        "status": "AVAILABLE",
        "assigned_driver_id": None,
        "battery_level": 100,
        "last_inspected": "2026-08-31T06:00:00Z",
        "checked_out_at": None,
    },
}

# Transaction audit log
EQUIPMENT_LOGS: List[Dict[str, Any]] = []

def get_all_equipment() -> List[Dict[str, Any]]:
    return list(EQUIPMENT_INVENTORY.values())

def get_equipment_by_barcode_or_id(code: str) -> Optional[Dict[str, Any]]:
    code = code.strip().upper()
    for item in EQUIPMENT_INVENTORY.values():
        if item["id"].upper() == code or item["barcode"].upper() == code:
            return item
    return None

def check_out_equipment(code: str, driver_id: str) -> Dict[str, Any]:
    item = get_equipment_by_barcode_or_id(code)
    if not item:
        return {"status": "error", "message": f"Asset with identifier {code} not found."}

    if item["status"] == "CHECKED_OUT" and item["assigned_driver_id"] != driver_id:
        return {
            "status": "error",
            "message": f"Asset {item['id']} is currently checked out to driver {item['assigned_driver_id']}.",
        }

    now_iso = datetime.now(timezone.utc).isoformat()
    item["status"] = "CHECKED_OUT"
    item["assigned_driver_id"] = driver_id
    item["checked_out_at"] = now_iso

    log_entry = {
        "event": "CHECK_OUT",
        "asset_id": item["id"],
        "asset_name": item["name"],
        "driver_id": driver_id,
        "timestamp": now_iso,
    }
    EQUIPMENT_LOGS.insert(0, log_entry)
    logger.info(f"[Equipment] Checked out {item['id']} to {driver_id}")
    return {"status": "success", "action": "CHECK_OUT", "item": item}

def check_in_equipment(
    code: str,
    driver_id: str,
    battery_level: Optional[int] = None,
    odometer_miles: Optional[int] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    item = get_equipment_by_barcode_or_id(code)
    if not item:
        return {"status": "error", "message": f"Asset with identifier {code} not found."}

    now_iso = datetime.now(timezone.utc).isoformat()
    item["status"] = "AVAILABLE"
    item["assigned_driver_id"] = None
    item["checked_out_at"] = None

    if battery_level is not None:
        item["battery_level"] = battery_level
    if odometer_miles is not None:
        item["odometer_miles"] = odometer_miles

    log_entry = {
        "event": "CHECK_IN",
        "asset_id": item["id"],
        "asset_name": item["name"],
        "driver_id": driver_id,
        "battery_level": battery_level,
        "odometer_miles": odometer_miles,
        "notes": notes,
        "timestamp": now_iso,
    }
    EQUIPMENT_LOGS.insert(0, log_entry)
    logger.info(f"[Equipment] Checked in {item['id']} from {driver_id}")
    return {"status": "success", "action": "CHECK_IN", "item": item}
