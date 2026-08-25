CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS labor_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS labors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    worker_id INTEGER NOT NULL,
    labor_type_id INTEGER NOT NULL,
    hours REAL NOT NULL,
    price_per_hour REAL NOT NULL,
    total_price REAL NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0,
    FOREIGN KEY (worker_id) REFERENCES workers (id),
    FOREIGN KEY (labor_type_id) REFERENCES labor_types (id)
);

CREATE TABLE IF NOT EXISTS production (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    kilos REAL NOT NULL,
    price_per_kilo REAL NOT NULL,
    total_income REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS expense_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    expense_type_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0,
    FOREIGN KEY (expense_type_id) REFERENCES expense_types (id)
);

-- Dades extretes automaticament de Vegga (programador de reg)
CREATE TABLE IF NOT EXISTS vegga_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id INTEGER NOT NULL,
    snapshot_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    device_date TEXT,
    connected INTEGER,
    alarm INTEGER,
    out_service INTEGER,
    system_stop_malfunction INTEGER,
    conditional_stop_malfunction INTEGER,
    general_malfunction INTEGER,
    flow_malfunction INTEGER,
    counter_malfunction INTEGER,
    fertilizer_malfunction INTEGER,
    filter_malfunction INTEGER,
    ph_malfunction INTEGER,
    ce_malfunction INTEGER,
    definitive_stop_malfunction INTEGER,
    tension_vcc REAL,
    battery_load INTEGER,
    last_reception TEXT
);

CREATE TABLE IF NOT EXISTS vegga_water_meters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id INTEGER NOT NULL,
    meter_id TEXT NOT NULL,
    snapshot_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_volume REAL,
    x_flow REAL,
    leak_flow REAL
);

CREATE TABLE IF NOT EXISTS vegga_filter_events (
    unit_id INTEGER NOT NULL,
    vegga_id TEXT NOT NULL,
    event_date TEXT,
    number INTEGER,
    duration_value REAL,
    imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (unit_id, vegga_id)
);

CREATE TABLE IF NOT EXISTS vegga_sectors (
    unit_id INTEGER NOT NULL,
    sector_id INTEGER NOT NULL,
    name TEXT,
    output INTEGER,
    sector_op INTEGER,
    program_list TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (unit_id, sector_id)
);

CREATE TABLE IF NOT EXISTS vegga_programs (
    unit_id INTEGER NOT NULL,
    program_id INTEGER NOT NULL,
    name TEXT,
    sector1 INTEGER,
    start_minutes INTEGER,
    duration_seconds INTEGER,
    fertilizer1 INTEGER,
    monday INTEGER, tuesday INTEGER, wednesday INTEGER, thursday INTEGER,
    friday INTEGER, saturday INTEGER, sunday INTEGER,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (unit_id, program_id)
);

CREATE TABLE IF NOT EXISTS vegga_analog_sensors (
    unit_id INTEGER NOT NULL,
    sensor_id TEXT NOT NULL,
    snapshot_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    name TEXT,
    x_value REAL,
    min_graphics REAL,
    max_graphics REAL,
    PRIMARY KEY (unit_id, sensor_id, snapshot_at)
);

CREATE TABLE IF NOT EXISTS vegga_digital_sensors (
    unit_id INTEGER NOT NULL,
    sensor_id TEXT NOT NULL,
    snapshot_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    name TEXT,
    x_state INTEGER,
    PRIMARY KEY (unit_id, sensor_id, snapshot_at)
);
