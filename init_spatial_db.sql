CREATE EXTENSION IF NOT EXISTS postgis;
DROP TABLE IF EXISTS dispatches CASCADE;
DROP TABLE IF EXISTS drivers CASCADE;

CREATE TABLE drivers (
    driver_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dispatches (
    dispatch_id VARCHAR(50) PRIMARY KEY,
    driver_id VARCHAR(50) REFERENCES drivers(driver_id),
    destination_name VARCHAR(150) NOT NULL,
    status VARCHAR(50) NOT NULL,
    speed VARCHAR(20) DEFAULT '0 mph',
    route_geom GEOMETRY(LineString, 4326),
    current_location GEOMETRY(Point, 4326),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dispatches_location ON dispatches USING GIST (current_location);
CREATE INDEX idx_dispatches_route ON dispatches USING GIST (route_geom);

INSERT INTO drivers (driver_id, name, status) VALUES 
('DRV-201', 'Marcus Vance', 'On Route'),
('DRV-202', 'Sarah Jenkins', 'Ready'),
('DRV-203', 'David Ross', 'Off Duty'),
('DRV-204', 'Elena Rostova', 'On Route');

INSERT INTO dispatches (dispatch_id, driver_id, destination_name, status, speed, current_location, route_geom) VALUES 
('DISP-1092', 'DRV-201', 'North Loop Terminal', 'In Transit', '34 mph', ST_SetSRID(ST_MakePoint(-87.6298, 41.8781), 4326), ST_GeomFromText('LINESTRING(-87.85 41.75, -87.75 41.80, -87.68 41.85, -87.6298 41.8781)', 4326)),
('DISP-1093', 'DRV-202', 'Westside Hub C', 'Dispatched', '0 mph', ST_SetSRID(ST_MakePoint(-87.6500, 41.8850), 4326), ST_GeomFromText('LINESTRING(-87.90 41.90, -87.65 41.8850)', 4326)),
('DISP-1094', 'DRV-203', 'Downtown Center', 'Delivered', '0 mph', ST_SetSRID(ST_MakePoint(-87.6244, 41.8756), 4326), ST_GeomFromText('LINESTRING(-87.80 41.70, -87.6244 41.8756)', 4326)),
('DISP-1095', 'DRV-204', 'O''Hare Cargo Bay 4', 'En Route', '58 mph', ST_SetSRID(ST_MakePoint(-87.9073, 41.9742), 4326), ST_GeomFromText('LINESTRING(-87.95 42.00, -87.9073 41.9742)', 4326));
