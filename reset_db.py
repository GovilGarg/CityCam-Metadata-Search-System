from connect_db import get_connection

def reset_database():
    print("--- RESETTING DATABASE ---")
    with get_connection() as db:
        if not db:
            print("Failed to connect to the database.")
            return

        with db.cursor() as cursor:
            # Drop tables in reverse dependency order
            print("Dropping search_audit_logs table...")
            cursor.execute("DROP TABLE IF EXISTS search_audit_logs")
            
            print("Dropping surveillance_logs table...")
            cursor.execute("DROP TABLE IF EXISTS surveillance_logs")
            
            print("Dropping cameras table...")
            cursor.execute("DROP TABLE IF EXISTS cameras")
            
            # Now create the tables properly so they are ready
            print("Creating cameras table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cameras(
                    camera_id VARCHAR(20) PRIMARY KEY,
                    location_name VARCHAR(100),
                    latitude DECIMAL (9,6),
                    longitude DECIMAL (9,6)
                )
            """)
            
            print("Creating surveillance_logs table (with user's new schema)...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS surveillance_logs(
                    log_id INT AUTO_INCREMENT PRIMARY KEY,
                    object_id VARCHAR(40),
                    object_type VARCHAR(50),
                    object_colour VARCHAR(20),
                    camera_id VARCHAR(20),
                    CONSTRAINT fk_camera FOREIGN KEY (camera_id) REFERENCES cameras(camera_id),
                    sighting_time DATETIME,
                    -- Optimized Time Attribute: Generated column for fast time-of-day searching
                    sighting_time_only TIME GENERATED ALWAYS AS (TIME(sighting_time)) VIRTUAL,
                    INDEX idx_time (sighting_time),
                    INDEX idx_time_only (sighting_time_only),
                    INDEX idx_objects (object_id, object_type, object_colour),
                    INDEX idx_colour_type (object_colour, object_type),
                    INDEX idx_camera (camera_id)
                )
            """)
            
            print("Creating search_audit_logs table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_audit_logs(
                    audit_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(50) DEFAULT 'system',
                    parsed_query TEXT,
                    search_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            db.commit()
            print("--- DATABASE RESET COMPLETE ---")
            print("Both tables are now empty with the correct structures.")

if __name__ == "__main__":
    reset_database()
