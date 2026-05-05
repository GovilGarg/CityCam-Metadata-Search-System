from connect_db import get_connection

def search_by_object(object_id):
    """
    Search the database for all logs matching a specific Object ID.
    Fulfills Stage 3 (Search) and Stage 4 (Path Reconstruction).
    """
    print(f"\n--- Searching for Object: {object_id} ---")
    
    with get_connection() as db:
        if not db:
            print("Failed to connect to database.")
            return

        with db.cursor() as cursor:
            query = """
                SELECT l.sighting_time, l.object_type, l.object_colour, c.location_name 
                FROM surveillance_logs l
                JOIN cameras c ON l.camera_id = c.camera_id
                WHERE l.object_id = %s
                ORDER BY l.sighting_time ASC 
            """
            cursor.execute(query, (object_id,))
            results = cursor.fetchall()

            if not results:
                print(f"No sightings found for {object_id}.")
                return

            print(f"Found {len(results)} sightings:")
            
            # Stage 4 Logic: Build a journey string
            journey_path = []
            
            for row in results:
                # row: (0:sighting_time, 1:object_type, 2:object_colour, 3:location_name)
                print(f"[{row[0]}] A {row[2]} {row[1]} was spotted at {row[3]}")
                journey_path.append(row[3])

            # Print the Reconstruction (Stage 4)
            if len(journey_path) > 1:
                print("\n--- RECONSTRUCTED JOURNEY ---")
                print(" -> ".join(journey_path))

def search_by_attributes(color=None, obj_type=None, start_time=None, end_time=None, limit=5):
    """
    Search by specific vehicle attributes like color, type, or a specific time range.
    """
    print(f"\n--- Searching by Attributes ---")
    
    query = """
        SELECT l.object_id, l.sighting_time, l.object_colour, l.object_type, c.location_name
        FROM surveillance_logs l
        JOIN cameras c ON l.camera_id = c.camera_id
        WHERE 1=1
    """
    
    conditions = []
    params = []

    if color:
        conditions.append("l.object_colour = %s")
        params.append(color)
        print(f"Condition: Color = '{color}'")
        
    if obj_type:
        conditions.append("l.object_type = %s")
        params.append(obj_type)
        print(f"Condition: Type = '{obj_type}'")
        
    if start_time:
        conditions.append("l.sighting_time >= %s")
        params.append(start_time)
        print(f"Condition: From {start_time}")
        
    if end_time:
        conditions.append("l.sighting_time <= %s")
        params.append(end_time)
        print(f"Condition: Until {end_time}")

    if conditions:
        query += " AND " + " AND ".join(conditions)
        
    query += " ORDER BY l.sighting_time DESC LIMIT %s"
    params.append(limit)

    with get_connection() as db:
        with db.cursor() as cursor:
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()

            if not results:
                print("No matches found.")
                return

            print(f"Top {len(results)} recent matches:")
            for row in results:
                # row: (object_id, sighting_time, color, type, location_name)
                print(f"ID: {row[0]:<10} | [{row[1]}] | {row[2]} {row[3]} at {row[4]}")

if __name__ == "__main__":
    # Let's test the Search Engine!
    
    # Needs a real Object ID from simulation to test properly. 
    # We will fetch a random one first just to demonstrate.
    with get_connection() as db:
        with db.cursor() as cursor:
            cursor.execute("SELECT object_id FROM surveillance_logs LIMIT 1")
            sample_id = cursor.fetchone()
            
    if sample_id:
        search_by_object(sample_id[0])
        
    search_by_attributes(color="Red", limit=3)
    search_by_attributes(obj_type="SUV", limit=3)

