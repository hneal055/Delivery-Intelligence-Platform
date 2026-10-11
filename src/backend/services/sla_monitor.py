import time
import logging
from typing import Dict, List

logger = logging.getLogger("delivery_platform.sla_monitor")

class SLAMonitorService:
    def __init__(self, max_idle_seconds: int = 300):
        self.max_idle_seconds = max_idle_seconds
        # Tracks last movement timestamp per driver: { driver_id: {"last_active": timestamp, "lat": lat, "lng": lng} }
        self.driver_activity: Dict[str, Dict] = {}

    def evaluate_telemetry(self, driver_id: str, lat: float, lng: float, speed: float) -> List[str]:
        current_time = time.time()
        incidents = []

        if driver_id not in self.driver_activity:
            self.driver_activity[driver_id] = {"last_active": current_time, "lat": lat, "lng": lng}
            return incidents

        last_data = self.driver_activity[driver_id]
        
        # Check if vehicle is virtually stationary (speed < 1.0 km/h or negligible GPS movement)
        distance_moved = ((lat - last_data["lat"])**2 + (lng - last_data["lng"])**2)**0.5
        
        if speed < 1.0 and distance_moved < 0.0001:
            idle_duration = current_time - last_data["last_active"]
            if idle_duration > self.max_idle_seconds:
                incidents.append(f"SLA Warning: Driver {driver_id} has been stationary for {int(idle_duration)} seconds.")
        else:
            # Reset activity timer on movement
            self.driver_activity[driver_id] = {"last_active": current_time, "lat": lat, "lng": lng}

        return incidents

sla_monitor = SLAMonitorService()
