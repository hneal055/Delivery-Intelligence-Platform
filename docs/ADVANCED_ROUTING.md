# Advanced Route Intelligence

Enterprise-grade route optimization with multi-constraint support for fleet management.

## Features

### 1. **Time Window Constraints**
- Hard constraints (must deliver within window)
- Soft constraints (preferred delivery window)
- Automatic time window validation
- Violation tracking and reporting

### 2. **Vehicle Capacity Planning**
- Weight, volume, and package count limits
- Real-time capacity tracking
- Automatic feasibility checking
- Utilization analytics

### 3. **Multi-Depot Routing**
- Optimize across multiple distribution centers
- Automatic depot-to-stop assignment
- Territory-based routing
- Cross-depot analytics

### 4. **Break Scheduling**
- Regulatory compliance (breaks every N hours)
- Automatic break insertion in routes
- Max shift hours enforcement
- Break location tracking

### 5. **Dynamic Re-Optimization**
- Real-time route adjustments
- Traffic delay handling
- New job insertion
- Driver breakdown recovery

---

## API Endpoints

### Create Depot

Create a new distribution center location.

**Request:**
```http
POST /advanced-route/depots
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Downtown Distribution Center",
  "lat": 40.7128,
  "lon": -74.0060,
  "address": "123 Main St, New York, NY",
  "operating_hours_start": "06:00:00",
  "operating_hours_end": "22:00:00",
  "max_vehicles": 50
}
```

**Response:**
```json
{
  "id": "depot_123",
  "name": "Downtown Distribution Center",
  "lat": 40.7128,
  "lon": -74.0060,
  "address": "123 Main St, New York, NY",
  "operating_hours_start": "06:00:00",
  "operating_hours_end": "22:00:00",
  "max_vehicles": 50,
  "is_active": true
}
```

---

### List Depots

Get all active distribution centers.

**Request:**
```http
GET /advanced-route/depots?active_only=true
Authorization: Bearer <token>
```

---

### Create Vehicle Profile

Define vehicle capacity and capabilities.

**Request:**
```http
POST /advanced-route/vehicles/profile
Authorization: Bearer <token>
Content-Type: application/json

{
  "vehicle_id": "VAN-001",
  "max_weight_kg": 1500.0,
  "max_volume_m3": 15.0,
  "max_packages": 120,
  "vehicle_type": "van",
  "fuel_type": "electric"
}
```

---

### Optimize Single Route

Optimize route for one driver with full constraint satisfaction.

**Request:**
```http
POST /advanced-route/optimize-single
Authorization: Bearer <token>
Content-Type: application/json

{
  "driver_id": "driver123",
  "depot_id": "depot_456",
  "package_ids": ["pkg1", "pkg2", "pkg3"],
  "constraints": {
    "enforce_time_windows": true,
    "enforce_capacity": true,
    "enforce_breaks": true,
    "max_route_duration_hours": 10.0,
    "optimization_objective": "minimize_distance"
  },
  "start_time": "2026-02-26T08:00:00Z"
}
```

---

### Multi-Depot Optimization

Optimize routes across multiple depots and drivers simultaneously.

**Request:**
```http
POST /advanced-route/optimize-multi-depot
Authorization: Bearer <token>
Content-Type: application/json

{
  "depots": [ ... ],
  "stops": [ ... ],
  "available_drivers": [ ... ],
  "constraints": {
    "enforce_time_windows": true,
    "enforce_capacity": true,
    "enforce_breaks": true,
    "max_route_duration_hours": 8.0
  }
}
```

---

### Add Time Window Constraint

Restrict delivery to a specific time window.

**Request:**
```http
POST /advanced-route/time-windows
Authorization: Bearer <token>
Content-Type: application/json

{
  "package_id": "pkg123",
  "window_start": "2026-02-26T09:00:00Z",
  "window_end": "2026-02-26T12:00:00Z",
  "is_hard_constraint": true
}
```

---

### Get Route History

Retrieve optimization history for a driver.

**Request:**
```http
GET /advanced-route/route-history/{driver_id}?limit=10
Authorization: Bearer <token>
```

---

### Capacity Utilization Analytics

Get fleet capacity utilization statistics.

**Request:**
```http
GET /advanced-route/analytics/capacity-utilization?days=7
Authorization: Bearer <token>
```

**Response:**
```json
{
  "period_days": 7,
  "average_utilization_percent": 72.5,
  "min_utilization_percent": 45.0,
  "max_utilization_percent": 95.0,
  "total_routes_optimized": 42
}
```

---

### Time Window Compliance Analytics

Monitor SLA compliance.

**Request:**
```http
GET /advanced-route/analytics/time-window-compliance?days=7
Authorization: Bearer <token>
```

**Response:**
```json
{
  "period_days": 7,
  "total_violations": 3,
  "total_routes": 42,
  "compliance_rate_percent": 92.86
}
```

---

## Usage Examples

### Example 1: Basic Route Optimization

```python
import requests

TOKEN = "your_auth_token"
API_URL = "http://localhost:8000"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# Create depot
depot_response = requests.post(
    f"{API_URL}/advanced-route/depots",
    headers=HEADERS,
    json={
        "name": "Main Warehouse",
        "lat": 40.7128,
        "lon": -74.0060,
        "address": "123 Warehouse Blvd"
    }
)
depot_id = depot_response.json()["id"]

# Add time windows
for package_id in ["pkg1", "pkg2"]:
    requests.post(
        f"{API_URL}/advanced-route/time-windows",
        headers=HEADERS,
        json={
            "package_id": package_id,
            "window_start": "2026-02-26T10:00:00Z",
            "window_end": "2026-02-26T14:00:00Z",
            "is_hard_constraint": True
        }
    )

# Optimize route
route_response = requests.post(
    f"{API_URL}/advanced-route/optimize-single",
    headers=HEADERS,
    json={
        "driver_id": "driver123",
        "depot_id": depot_id,
        "package_ids": ["pkg1", "pkg2"],
        "constraints": {
            "enforce_time_windows": True,
            "enforce_capacity": True
        }
    }
)

print(f"Optimized: {route_response.json()}")
```

### Example 2: Multi-Depot Fleet Optimization

```python
import requests

TOKEN = "your_auth_token"
API_URL = "http://localhost:8000"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

response = requests.post(
    f"{API_URL}/advanced-route/optimize-multi-depot",
    headers=HEADERS,
    json={
        "depots": [
            {"id": "depot1", "name": "North", "lat": 40.7, "lon": -74.0},
            {"id": "depot2", "name": "South", "lat": 40.6, "lon": -73.9}
        ],
        "stops": [...],
        "available_drivers": [...],
        "constraints": {
            "enforce_time_windows": True,
            "max_route_duration_hours": 8.0
        }
    }
)

routes = response.json()
print(f"Created {len(routes)} optimized routes")
```

---

## Database Schema

### New Tables
- **depots** - Distribution center locations
- **vehicle_profiles** - Vehicle capacity specs
- **route_history** - Optimization audit trail
- **driver_break_logs** - Break compliance
- **time_window_constraints** - Delivery windows

---

## Performance

- **Stops per route**: Optimal < 50 stops
- **Multi-depot**: Linear scaling
- **Time windows**: ~5% overhead
- **Capacity checks**: O(n) complexity

---

## Optimization Objectives

- `minimize_distance` - Shortest distance (default)
- `minimize_time` - Fastest delivery
- `balance_load` - Even distribution

---

## Changelog

### v1.0 (2026-02-26)
- Initial release with time windows
- Vehicle capacity planning
- Multi-depot optimization
- Break scheduling
- Route analytics

