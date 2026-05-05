from connect_db import get_connection

def diagnose():
    print("--- DIAGNOSING DATABASE ---")
    with get_connection() as db:
        if not db:
            print("Failed to connect to the database.")
            return

        with db.cursor() as cursor:
            # Check for NULL in location_name
            try:
                cursor.execute("SELECT COUNT(*) FROM cameras WHERE location_name IS NULL")
                null_locations = cursor.fetchone()[0]
                print(f"\nNumber of cameras with NULL location_name: {null_locations}")
                
                if null_locations > 0:
                    cursor.execute("SELECT * FROM cameras WHERE location_name IS NULL LIMIT 5")
                    print("Sample cameras with NULL location_name:")
                    for row in cursor.fetchall():
                        print(row)
            except Exception as e:
                print(f"Error checking location_name: {e}")
                
            # Check table structures
            print("\n--- cameras table structure ---")
            try:
                cursor.execute("DESCRIBE cameras")
                for row in cursor.fetchall():
                    print(row)
            except Exception as e:
                print(e)
                
            print("\n--- surveillance_logs table structure ---")
            try:
                cursor.execute("DESCRIBE surveillance_logs")
                for row in cursor.fetchall():
                    print(row)
            except Exception as e:
                print(f"Table might not exist: {e}")

if __name__ == "__main__":
    diagnose()
