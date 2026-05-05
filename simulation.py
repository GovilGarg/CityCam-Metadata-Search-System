import random 
from datetime import datetime , timedelta
from connect_db import get_connection
from camera_setup import setup_infrastruct

# Data (records) that will be inserted at once 

CHUNK_SIZE = 600


# Metadata need for data generation

object_colour =["Red", "Silver", "Green","Blue","Pink","Orange","Yellow","White","Black",
                "Grey","Purple","Sky Blue","Cyan","Brown","Dark Green", "Maroon", "Pearl White",
                "Metallic Grey", "Bronze", "Copper","Royal Blue","Beige"]


object_type =["Sedan", "SUV", "Luxury Sedan", "Compact SUV", "Luxury Cars", "Sports Cars",
               "Motorcycle", "Scooter", "Auto" ,"Rickshaw", "Electric Rickshaw", "Scooty",
               "Mini Truck", "Heavy Truck", "Tanker", "Bus", "Luxury Coach","Firefighter Truck", 
               "Van", "Tempo", "Tractor", "Ambulance", "Police Jeep", "Pickup"]


# LOGIC for Data Generation (generation of random sightings data)

def get_sightings(avail_camera):
    #generates object id in form of VEH-0000
    vehicle_id = f"VEH-{random.randint(1000,9999)}"
    selected_camera = random.choice(avail_camera)
    # Generate realistic time across the last 24 hours with full resolution
    time = datetime.now() - timedelta(seconds=random.randint(0, 86400))
    
    return(
        selected_camera,
        vehicle_id,
        random.choice(object_type),
        random.choice(object_colour),
        time
    )

def run_scenario(specific_scenario=None):
    with get_connection() as db :
        with db.cursor() as cursor:
            cursor.execute("SELECT camera_id, location_name From cameras")
            
            # Create a map of location names to camera IDs
            camera_data = cursor.fetchall()
            camera_list = [row[0] for row in camera_data]
            location_to_cameras = {}
            for cam_id, loc_name in camera_data:
                if loc_name not in location_to_cameras:
                    location_to_cameras[loc_name] = []
                location_to_cameras[loc_name].append(cam_id)

            if not camera_list:
                print("ERROR!!! Camera not found!")
                return
            

            print(f" Generating {CHUNK_SIZE} random sightings ...")

            # We use "_" as we don't need current index no., we just need loop running
            # Generating data and then sorting it chronologically before insertion
            sightings_data = [get_sightings(camera_list) for _ in range(CHUNK_SIZE)]
            
            # Inject specific scenario data if requested
            if specific_scenario == "red_cars_at_saket":
                print("--- Injecting Specific Scenario: Red Cars at Saket ---")
                saket_cameras = location_to_cameras.get("Saket", [])
                if saket_cameras:
                    for _ in range(10): # Add 10 red cars at Saket
                        cam = random.choice(saket_cameras)
                        vid = f"VEH-SAK-{random.randint(1000,9999)}"
                        vtype = random.choice(["Sedan", "SUV", "Luxury Sedan"])
                        vcol = "Red"
                        vtime = datetime.now() - timedelta(minutes=random.randint(1, 120))
                        sightings_data.append((cam, vid, vtype, vcol, vtime))

            # Sorting by sighting_time (which is at index 4 of each tuple)
            # This ensures log_id (AUTO_INCREMENT) follows the time sequence
            sightings_data.sort(key=lambda x: x[4])

            query = """INSERT INTO surveillance_logs(camera_id,object_id,object_type,object_colour,sighting_time)
                        VALUES (%s,%s,%s,%s,%s)"""
            
            cursor.executemany(query,sightings_data)
            db.commit()

            print(f"SUCCESS------{CHUNK_SIZE} sightings data inserted in DB")

            # Add this right after the db.commit() in run_scenario()
            cursor.execute("SELECT COUNT(*) FROM surveillance_logs")
            count = cursor.fetchone()[0]
            print(f"DATABASE VERIFICATION: Total logs in DB now: {count}")

            # Verify the JOIN works
            print("\n--- Testing the JOIN (Last 3 records) ---")
            cursor.execute("""
                SELECT l.object_id, l.object_type, c.camera_id 
                FROM surveillance_logs AS l 
                JOIN cameras AS c ON l.camera_id = c.camera_id 
                ORDER BY l.sighting_time DESC 
                LIMIT 3
            """)
            for row in cursor.fetchall():
                print(row)

if __name__=="__main__":
    import sys
    scenario = sys.argv[1] if len(sys.argv) > 1 else "red_cars_at_saket"
    run_scenario(scenario)