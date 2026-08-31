CREATE TABLE IF NOT EXISTS route_sessions (
    id SERIAL PRIMARY KEY,
    driver_id VARCHAR(32) NOT NULL,
    session_date DATE NOT NULL DEFAULT CURRENT_DATE,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    total_packages_assigned INT DEFAULT 0,
    total_delivered INT DEFAULT 0,
    total_exceptions INT DEFAULT 0,
    total_distance_miles NUMERIC(6, 2) DEFAULT 0.0,
    total_idle_minutes NUMERIC(6, 2) DEFAULT 0.0,
    average_dwell_minutes NUMERIC(5, 2) DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS stop_metrics (
    id SERIAL PRIMARY KEY,
    package_id VARCHAR(64) NOT NULL,
    driver_id VARCHAR(32) NOT NULL,
    arrived_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    dwell_duration_seconds INT,
    delivery_status VARCHAR(32) NOT NULL,
    distance_from_target_meters NUMERIC(6, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_driver_performance (
    driver_id VARCHAR(32) NOT NULL,
    report_date DATE NOT NULL DEFAULT CURRENT_DATE,
    completion_rate NUMERIC(5, 2),
    avg_speed_mph NUMERIC(4, 1),
    max_speed_mph NUMERIC(4, 1),
    total_stops INT,
    on_time_stops INT,
    fadr_percentage NUMERIC(5, 2),
    PRIMARY KEY (driver_id, report_date)
);

CREATE INDEX IF NOT EXISTS idx_route_sessions_driver_date ON route_sessions(driver_id, session_date);
CREATE INDEX IF NOT EXISTS idx_stop_metrics_driver ON stop_metrics(driver_id);
