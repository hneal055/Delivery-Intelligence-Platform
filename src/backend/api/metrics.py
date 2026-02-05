from prometheus_client import Gauge

# Metric to track active drivers
ACTIVE_DRIVERS = Gauge("connected_drivers_total", "Number of drivers providing telemetry in the last 60 seconds")

# In-memory store for last heartbeat: {driver_id: timestamp}
driver_heartbeats = {}
