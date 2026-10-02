CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    hash TEXT,
    auth_provider TEXT DEFAULT 'local',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    name TEXT,
    avatar_url TEXT,
    location TEXT,
    vehicle_type TEXT DEFAULT 'car',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    work_date TEXT NOT NULL,
    city TEXT NOT NULL,
    distance_km REAL DEFAULT 0,
    fuel_cost REAL DEFAULT 0,
    fuel_price REAL DEFAULT 0,
    rent_cost REAL DEFAULT 0,
    other_expenses REAL DEFAULT 0,
    work_hours REAL DEFAULT 0,
    income REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, name_key)
);

CREATE INDEX IF NOT EXISTS idx_trips_user_date ON trips(user_id, work_date);
CREATE INDEX IF NOT EXISTS idx_trips_user_city ON trips(user_id, city);