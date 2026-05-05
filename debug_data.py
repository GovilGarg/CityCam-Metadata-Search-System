from connect_db import get_connection

def check_data():
    db = get_connection()
    if not db:
        print("Failed to connect to DB")
        return
    
    try:
        with db.cursor() as cursor:
            # Check for Saket location
            cursor.execute("SELECT camera_id FROM cameras WHERE location_name = 'Saket'")
            cameras = cursor.fetchall()
            print(f"Cameras at Saket: {cameras}")
            
            # Check for Red Cars at Saket
            query = """
                SELECT l.object_id, l.object_colour, l.object_type, c.location_name
                FROM surveillance_logs l
                JOIN cameras c ON l.camera_id = c.camera_id
                WHERE l.object_colour = 'Red' AND l.object_type = 'Car' AND c.location_name = 'Saket'
            """
            cursor.execute(query)
            results = cursor.fetchall()
            print(f"Red Cars at Saket: {len(results)} found")
            if results:
                print(results[:5])
                
            # Check for any Red objects at Saket
            query_any = """
                SELECT l.object_colour, l.object_type, c.location_name
                FROM surveillance_logs l
                JOIN cameras c ON l.camera_id = c.camera_id
                WHERE l.object_colour = 'Red' AND c.location_name = 'Saket'
            """
            cursor.execute(query_any)
            any_results = cursor.fetchall()
            print(f"Any Red objects at Saket: {len(any_results)} found")
            for res in any_results:
                print(f" - {res}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    check_data()
