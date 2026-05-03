"""
Database management for BikeCommute Analytics
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from config import DATABASE_FILE

class BikeCommuteDB:
    def __init__(self, db_file=DATABASE_FILE):
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create rides table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drive_file_id TEXT UNIQUE NOT NULL,
                date TEXT NOT NULL,
                duration INTEGER NOT NULL,
                distance REAL NOT NULL,
                avg_hr INTEGER,
                max_hr INTEGER,
                avg_speed REAL NOT NULL,
                calories INTEGER,
                temp REAL,
                wind_speed REAL,
                wind_direction REAL,
                wind_component REAL,
                route_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Create trackpoints table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trackpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ride_id INTEGER NOT NULL,
                time TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                hr INTEGER,
                FOREIGN KEY (ride_id) REFERENCES rides (id)
            )
            """
        )

        conn.commit()
        conn.close()

    def insert_ride(
        self,
        drive_file_id,
        date,
        duration,
        distance,
        avg_hr,
        max_hr,
        avg_speed,
        calories,
        temp,
        wind_speed,
        wind_direction,
        wind_component,
        route_type,
    ):
        """Insert a new ride record and return ride_id"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO rides (
                    drive_file_id, date, duration, distance, avg_hr, max_hr,
                    avg_speed, calories, temp, wind_speed, wind_direction, wind_component, route_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    drive_file_id,
                    date,
                    duration,
                    distance,
                    avg_hr,
                    max_hr,
                    avg_speed,
                    calories,
                    temp,
                    wind_speed,
                    wind_direction,
                    wind_component,
                    route_type,
                ),
            )
            conn.commit()
            ride_id = cursor.lastrowid
            return ride_id
        except sqlite3.IntegrityError:
            return None  # File already processed
        finally:
            conn.close()

    def get_all_rides(self):
        """Get all rides ordered by date"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rides ORDER BY date DESC")
        rides = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rides

    def get_rides_by_route(self, route_type):
        """Get rides for a specific route (work/home)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM rides WHERE route_type = ? ORDER BY date DESC",
            (route_type,),
        )
        rides = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rides

    def get_best_time(self, route_type):
        """Get best (shortest) time for a route"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM rides WHERE route_type = ? ORDER BY duration ASC LIMIT 1",
            (route_type,),
        )
        ride = cursor.fetchone()
        conn.close()
        return dict(ride) if ride else None

    def get_last_ride(self):
        """Get the most recent ride"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rides ORDER BY date DESC LIMIT 1")
        ride = cursor.fetchone()
        conn.close()
        return dict(ride) if ride else None

    def get_current_streak(self, route_type):
        """Get current consecutive ride streak for a route"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM rides WHERE route_type = ? ORDER BY date DESC",
            (route_type,),
        )
        result = cursor.fetchone()
        conn.close()
        return result["count"] if result else 0

    def ride_exists(self, drive_file_id):
        """Check if a ride has already been processed"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM rides WHERE drive_file_id = ?", (drive_file_id,))
        result = cursor.fetchone()
        conn.close()
        return result["count"] > 0

    def insert_trackpoints(self, ride_id, trackpoints):
        """Insert trackpoints for a ride"""
        conn = self.get_connection()
        cursor = conn.cursor()

        for tp in trackpoints:
            cursor.execute(
                """
                INSERT INTO trackpoints (ride_id, time, lat, lon, hr)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ride_id, tp.get("time"), tp.get("lat"), tp.get("lon"), tp.get("hr"))
            )

        conn.commit()
        conn.close()

    def get_trackpoints(self, ride_id):
        """Get all trackpoints for a ride"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM trackpoints WHERE ride_id = ? ORDER BY time ASC",
            (ride_id,)
        )
        trackpoints = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return trackpoints

    def get_ride_by_id(self, ride_id):
        """Get a specific ride by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rides WHERE id = ?", (ride_id,))
        ride = cursor.fetchone()
        conn.close()
        return dict(ride) if ride else None
