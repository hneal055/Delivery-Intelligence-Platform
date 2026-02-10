from prometheus_client import Gauge, Counter

# Metric to track active drivers
ACTIVE_DRIVERS = Gauge("connected_drivers_total", "Number of drivers providing telemetry in the last 60 seconds")
DELIVERIES_COMPLETED = Counter("deliveries_completed_total", "Total number of successful deliveries")

# In-memory store for last heartbeat: {driver_id: timestamp}
driver_heartbeats = {}
