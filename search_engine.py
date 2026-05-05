from connect_db import get_connection
import re
from datetime import datetime, timedelta
import math
import json
import difflib
import requests

# Catalog for entity mapping
ENTITY_CATALOG = {
    "STOP_WORDS": {"i", "saw", "a", "an", "the", "in", "at", "around", "near", "looking", "for", "between", "from", "to"},
    "COLORS": {
        "red", "blue", "black", "white", "silver", "grey", "green", "yellow", 
        "beige", "bronze", "brown", "copper", "cyan", "dark green", "maroon", 
        "metallic grey", "orange", "pearl white", "pink", "purple", "royal blue", "sky blue"
    },
    "TYPES": {
        "car", "suv", "truck", "bike", "motorcycle", "van", "bus", "ambulance", "auto",
        "compact suv", "electric rickshaw", "firefighter truck", "heavy truck", "luxury cars",
        "luxury coach", "luxury sedan", "mini truck", "pickup", "police jeep", "rickshaw",
        "scooter", "scooty", "sedan", "sports cars", "tanker", "tempo", "tractor"
    },
    "VEHICLE_GROUPS": {
        "four wheelers": {
            "car", "suv", "sedan", "compact suv", "luxury sedan", "sports cars", 
            "luxury cars", "police jeep", "van", "mini truck", "heavy truck", 
            "tanker", "firefighter truck", "ambulance", "pickup"
        },
        "two wheelers": {
            "bike", "motorcycle", "scooter", "scooty"
        },
        "three wheelers": {
            "auto", "rickshaw", "electric rickshaw"
        }
    },
    "LOCATIONS": [
        "Connaught Place", "Chandni Chowk", "India Gate", "Lajpat Nagar", 
        "Karol Bagh", "Hauz Khas", "Saket", "Vasant Kunj", "Dwarka", 
        "Rohini", "Pitampura", "Janakpuri", "Rajouri Garden", "Nehru Place", 
        "Okhla", "Greater Kailash", "Dhaula Kuan", "Aerocity", 
        "Chanakyapuri", "Paharganj", "Lal Qila"
    ]
}
ENTITY_CATALOG["LOCATIONS_MAP"] = {loc.lower(): loc for loc in ENTITY_CATALOG["LOCATIONS"]}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    # Floating point precision correction
    a = min(1.0, max(0.0, a))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class SearchQuery:
    """Represents a parsed search query with all its entities and constraints."""
    def __init__(self, color=None, vehicle_type=None, location=None, vehicle_id=None, 
                 time_constraint=None, date_mentioned=False, type_list=None, group_name=None):
        self.color = color
        self.type = vehicle_type
        self.location = location
        self.vehicle_id = vehicle_id
        self.time_constraint = time_constraint
        self.date_mentioned = date_mentioned
        self.type_list = type_list
        self.group_name = group_name

    def to_dict(self):
        return {
            "color": self.color,
            "type": self.type,
            "location": self.location,
            "vehicle_id": self.vehicle_id,
            "time_constraint": self.time_constraint,
            "date_mentioned": self.date_mentioned,
            "type_list": self.type_list,
            "group_name": self.group_name
        }

    def __repr__(self):
        return f"SearchQuery({self.to_dict()})"

class OllamaIntelligenceLayer:
    """Handles advanced local NLP using Ollama for privacy-focused metadata querying."""
    def __init__(self, model="gpt-oss:120b-cloud", host="http://localhost:11434"):
        self.model = model
        self.host = host
        self.api_url = f"{host}/api/generate"
        self._force_disabled = False
        self.available = self._check_availability()

    def _check_availability(self):
        # Force disabled for local testing to avoid hangs in the intelligence layer
        print("[Intelligence] Local Ollama Layer explicitly disabled for stability.")
        return False
        try:
            response = requests.get(self.host, timeout=1)
            if response.status_code == 200:
                print(f"[Intelligence] Local Ollama Layer ({self.model}) active.")
                return True
        except:
            pass
        print("[Intelligence] Local Ollama not detected. Falling back to Regex.")
        return False

    def is_active(self):
        return self.available and not self._force_disabled

    def set_active(self, active):
        self._force_disabled = not active
        print(f"[Intelligence] Ollama layer {'disabled' if self._force_disabled else 'enabled'}.")

    def parse_with_ollama(self, user_input):
        if not self.available:
            return None
        
        print(f"[Step 0] Requesting Local Intelligence from Ollama ({self.model})...")
        
        # System prompt to guide the LLM to return JSON
        prompt = f"""
        Task: Extract entities from a surveillance query.
        Input: "{user_input}"
        
        Instructions:
        Return ONLY a JSON object with these keys:
        - "color": (string or null) - use one of: {list(ENTITY_CATALOG["COLORS"])}
        - "type": (string or null) - use one of: {list(ENTITY_CATALOG["TYPES"])} or one of the groups below.
        - "location": (string or null) - use one of: {ENTITY_CATALOG["LOCATIONS"]}
        - "vehicle_id": (string or null) - extract numeric or alphanumeric vehicle/object ID if mentioned.
        - "time_range": (list [start_hour, end_hour] or null, 24h format)
        - "date": (string YYYY-MM-DD or null)

        Available Vehicle Groups (use as 'type'): {list(ENTITY_CATALOG["VEHICLE_GROUPS"].keys())}

        Example: "Find the red vehicle that passed through the main gate after 3 PM"
        Output: {{"color": "Red", "type": "Car", "location": "Main Gate", "time_range": [15, 23], "date": null, "vehicle_id": null}}
        
        Example: "all four wheelers"
        Output: {{"color": null, "type": "four wheelers", "location": null, "time_range": null, "date": null, "vehicle_id": null}}
        
        Example: "search for vehicle 1025"
        Output: {{"color": null, "type": null, "location": null, "time_range": null, "date": null, "vehicle_id": "1025"}}

        Return strictly valid JSON.
        """
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
            response = requests.post(self.api_url, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return json.loads(result.get("response", "{}"))
        except Exception as e:
            print(f"[Intelligence] Ollama parsing failed: {e}")
        return None

class SearchEngine:
    def __init__(self, ollama_model="gpt-oss:120b-cloud"):
        self.max_logical_speed_kmh = 200 # Max theoretical speed of a vehicle in the city
        self.intelligence = OllamaIntelligenceLayer(model=ollama_model)
        
        # Initialize metadata from ENTITY_CATALOG
        self.catalog = ENTITY_CATALOG.copy()
        
        # Try to refresh from DB
        self.refresh_metadata()

    def refresh_metadata(self):
        """Fetches latest metadata from the database to keep search entities dynamic."""
        print("[Step 0] Refreshing Metadata from Database...")
        conn = get_connection()
        if not conn:
            print("--> DB Connection failed, using fallback metadata.")
            return

        try:
            cursor = conn.cursor()
            
            # Fetch Colors
            cursor.execute("SELECT DISTINCT color FROM vehicle_logs WHERE color IS NOT NULL")
            db_colors = {row[0].lower() for row in cursor.fetchall() if row[0]}
            if db_colors: self.catalog["COLORS"].update(db_colors)

            # Fetch Types
            cursor.execute("SELECT DISTINCT vehicle_type FROM vehicle_logs WHERE vehicle_type IS NOT NULL")
            db_types = {row[0].lower() for row in cursor.fetchall() if row[0]}
            if db_types: self.catalog["TYPES"].update(db_types)

            # Fetch Locations
            cursor.execute("SELECT DISTINCT location_name FROM camera_setup")
            db_locs = [row[0] for row in cursor.fetchall() if row[0]]
            if db_locs:
                self.catalog["LOCATIONS"] = db_locs
                self.catalog["LOCATIONS_MAP"] = {loc.lower(): loc for loc in db_locs}

            print(f"--> Metadata Refreshed: {len(self.catalog['COLORS'])} colors, {len(self.catalog['TYPES'])} types, {len(self.catalog['LOCATIONS'])} locations.")
        except Exception as e:
            print(f"--> Metadata Refresh Error: {e}")
        finally:
            conn.close()

    def get_fuzzy_match(self, token, targets, cutoff=0.6):
        """Helper for fuzzy matching with a configurable cutoff. Returns (match, score)."""
        if not token or not targets:
            return None, 0
        matches = difflib.get_close_matches(token.lower(), [t.lower() for t in targets], n=1, cutoff=cutoff)
        if matches:
            match = matches[0]
            score = difflib.SequenceMatcher(None, token.lower(), match.lower()).ratio()
            return match, score
        return None, 0

    def _parse_time_regex(self, user_input_lower):
        """Extracts time and date constraints using regex patterns."""
        # Improved Time Parser: Handles "between HH:MM am/pm and HH:MM am/pm" or "from HH:MM to HH:MM"
        time_range_match = re.search(r'(?:between|from)\s+(\d{1,2}(?::\d{2})?)\s*(am|pm)?\s*(and|to|-)\s+(\d{1,2}(?::\d{2})?)\s*(am|pm)', user_input_lower)
        
        # Check for specific dates like "March 25", "2026-03-25", or "7-4-2026"
        date_match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})', user_input_lower)
        numeric_date_match = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', user_input_lower)
        
        target_date = datetime.now()
        date_mentioned = False
        
        if date_match:
            month_name = date_match.group(1).capitalize()
            day = int(date_match.group(2))
            try:
                target_date = datetime.strptime(f"{month_name} {day} {target_date.year}", "%B %d %Y")
                date_mentioned = True
            except:
                pass
        elif numeric_date_match:
            day = int(numeric_date_match.group(1))
            month = int(numeric_date_match.group(2))
            year = int(numeric_date_match.group(3))
            try:
                target_date = datetime(year, month, day)
                date_mentioned = True
            except:
                pass

        time_constraint = None
        if time_range_match:
            def get_time_parts(t, m):
                parts = t.split(':')
                h = int(parts[0])
                mi = int(parts[1]) if len(parts) > 1 else 0
                if not m: 
                    return min(23, h), mi
                if m == 'pm' and h < 12: h += 12
                if m == 'am' and h == 12: h = 0
                return min(23, h), mi

            t1, m1, connector, t2, m2 = time_range_match.groups()
            if not m1: m1 = m2
            
            h1, mi1 = get_time_parts(t1, m1)
            h2, mi2 = get_time_parts(t2, m2)
            
            target_start = target_date.replace(hour=h1, minute=mi1, second=0, microsecond=0)
            target_end = target_date.replace(hour=h2, minute=mi2, second=59, microsecond=0)
            time_constraint = (target_start, target_end)
        else:
            # Check for "last X hours" or "last X minutes"
            relative_time_match = re.search(r'last\s+(\d+)\s*(hours?|mins?|minutes?)', user_input_lower)
            if relative_time_match:
                amount = int(relative_time_match.group(1))
                unit = relative_time_match.group(2)
                end = datetime.now()
                if 'hour' in unit:
                    start = end - timedelta(hours=amount)
                else:
                    start = end - timedelta(minutes=amount)
                time_constraint = (start, end)
                date_mentioned = True 
            else:
                # Support "HH:MM am/pm" or just "HH am/pm"
                single_time_match = re.search(r'(\d{1,2}(?::\d{2})?)\s*(am|pm)', user_input_lower)
                if single_time_match:
                    t, meridian = single_time_match.groups()
                    parts = t.split(':')
                    hour = int(parts[0])
                    minute = int(parts[1]) if len(parts) > 1 else 0
                    
                    if meridian == 'pm' and hour < 12:
                        hour += 12
                    elif meridian == 'am' and hour == 12:
                        hour = 0
                    
                    target_start = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    target_end = target_date.replace(hour=hour, minute=minute, second=59, microsecond=0)
                    time_constraint = (target_start, target_end)
        
        if time_constraint or date_mentioned:
            return {
                'constraint': time_constraint,
                'date_mentioned': date_mentioned
            }
        return None

    def normalize_entity(self, value, category):
        """Helper to format entity names correctly (e.g., 'suv' -> 'SUV', 'car' -> 'Car')."""
        if not value:
            return None
        
        val_lower = value.lower().strip()
        acronyms = {'suv'}
        
        # 1. Exact match from catalog
        if category == 'color':
            if val_lower in self.catalog["COLORS"]: return val_lower.title()
            match, score = self.get_fuzzy_match(val_lower, self.catalog["COLORS"], cutoff=0.6)
            return match.title() if match else val_lower.title()
        
        elif category == 'type':
            if val_lower in self.catalog["TYPES"]:
                return val_lower.upper() if val_lower in acronyms else val_lower.title()
            match, score = self.get_fuzzy_match(val_lower, self.catalog["TYPES"], cutoff=0.6)
            if match:
                return match.upper() if match in acronyms else match.title()
            return val_lower.upper() if val_lower in acronyms else val_lower.title()
            
        elif category == 'location':
            if val_lower in self.catalog["LOCATIONS_MAP"]: return self.catalog["LOCATIONS_MAP"][val_lower]
            # Try fuzzy matching against LOCATIONS
            match, score = self.get_fuzzy_match(val_lower, self.catalog["LOCATIONS"], cutoff=0.6)
            return self.catalog["LOCATIONS_MAP"].get(match.lower(), match) if match else value.title()
            
        return value.title()

    def parse_query(self, user_input):
        user_input_lower = user_input.lower()
        has_all = "all" in user_input_lower
        
        # Try local Ollama Intelligence first (Step 0)
        llm_data = self.intelligence.parse_with_ollama(user_input)
        
        if llm_data:
            print(f"--> Local Intelligence Result: {llm_data}")
            query_obj = self._create_query_from_llm(llm_data, has_all)
            # Use regex logic as fallback for time/date
            time_res = self._parse_time_regex(user_input_lower)
            if time_res:
                query_obj.time_constraint = time_res['constraint']
                query_obj.date_mentioned = time_res['date_mentioned']
            return query_obj

        # Fallback to Step 1 (Regex)
        print(f"\n[Step 1] Parsing Query (Regex Fallback): '{user_input}'")
        query_obj = SearchQuery()
        query_obj.vehicle_id = self._extract_vehicle_id(user_input_lower)
        
        tokens, potential_matches = self._get_potential_matches(user_input_lower)
        used_tokens = set()

        # Pass 1: Exact Matches
        self._match_exact_entities(potential_matches, query_obj, used_tokens, has_all)
        
        # Pass 2: Fuzzy Matches
        self._match_fuzzy_entities(potential_matches, query_obj, used_tokens, has_all)
        
        # Extract time/date
        time_res = self._parse_time_regex(user_input_lower)
        if time_res:
            query_obj.time_constraint = time_res['constraint']
            query_obj.date_mentioned = time_res['date_mentioned']
                
        print(f"--> Mapped Entities: {query_obj}")
        return query_obj

    def _create_query_from_llm(self, llm_data, has_all):
        """Creates a SearchQuery object from LLM output."""
        query_obj = SearchQuery(
            color=self.normalize_entity(llm_data.get("color"), 'color'),
            vehicle_type=llm_data.get("type"),
            location=self.normalize_entity(llm_data.get("location"), 'location'),
            vehicle_id=llm_data.get("vehicle_id")
        )
        
        type_val = query_obj.type.lower() if query_obj.type else ""
        if type_val in self.catalog["VEHICLE_GROUPS"]:
            query_obj.type_list = [t.title() for t in self.catalog["VEHICLE_GROUPS"][type_val]]
            query_obj.group_name = type_val.title()
            query_obj.type = None
        elif type_val:
            normalized_type = self.normalize_entity(type_val, 'type')
            if has_all:
                for group_name, members in self.catalog["VEHICLE_GROUPS"].items():
                    if type_val in members or normalized_type.lower() in members:
                        query_obj.type_list = [t.title() for t in members]
                        query_obj.group_name = group_name.title()
                        query_obj.type = None
                        return query_obj
            query_obj.type = normalized_type
        return query_obj

    def _extract_vehicle_id(self, user_input_lower):
        """Extracts vehicle ID using regex."""
        id_match = re.search(r'(?:vehicle|object|id|sighting)\s*(?:id|#)?\s*([a-z0-9-]+)', user_input_lower)
        if id_match:
            return id_match.group(1)
        standalone_id = re.search(r'\b([a-z]{3}-\d{4}|\d{4,})\b', user_input_lower)
        return standalone_id.group(1) if standalone_id else None

    def _get_potential_matches(self, user_input_lower):
        """Generates single and double word tokens for matching."""
        tokens = re.findall(r'\b\w+\b', user_input_lower)
        potential_matches = []
        for i in range(len(tokens)):
            potential_matches.append(tokens[i])
            if i < len(tokens) - 1:
                potential_matches.append(f"{tokens[i]} {tokens[i+1]}")
        potential_matches.sort(key=len, reverse=True)
        return tokens, potential_matches

    def _match_exact_entities(self, potential_matches, query_obj, used_tokens, has_all):
        """Performs exact matching for colors, types, locations, and groups."""
        for token in potential_matches:
            if token in self.catalog["STOP_WORDS"] or any(t in used_tokens for t in token.split()):
                continue
            
            if token in self.catalog["VEHICLE_GROUPS"]:
                query_obj.type_list = [t.title() for t in self.catalog["VEHICLE_GROUPS"][token]]
                query_obj.group_name = token.title()
                for t in token.split(): used_tokens.add(t)
            elif token in self.catalog["LOCATIONS_MAP"]:
                query_obj.location = self.catalog["LOCATIONS_MAP"][token]
                for t in token.split(): used_tokens.add(t)
            elif token in self.catalog["COLORS"]:
                query_obj.color = token.title()
                for t in token.split(): used_tokens.add(t)
            elif token in self.catalog["TYPES"]:
                if has_all:
                    for group_name, members in self.catalog["VEHICLE_GROUPS"].items():
                        if token in members:
                            query_obj.type_list = [t.title() for t in members]
                            query_obj.group_name = group_name.title()
                            query_obj.type = None
                            break
                    else:
                        query_obj.type = self.normalize_entity(token, 'type')
                else:
                    query_obj.type = self.normalize_entity(token, 'type')
                for t in token.split(): used_tokens.add(t)

    def _match_fuzzy_entities(self, potential_matches, query_obj, used_tokens, has_all):
        """Performs fuzzy matching for remaining tokens."""
        for token in potential_matches:
            if token in self.catalog["STOP_WORDS"] or any(t in used_tokens for t in token.split()):
                continue
            
            search_token = token
            is_multi = ' ' in token
            if not is_multi and search_token.endswith('s') and \
               search_token not in self.catalog["TYPES"] and \
               search_token not in self.catalog["COLORS"]:
                search_token = search_token[:-1]

            threshold = 0.8 if is_multi else 0.6
            best_match, best_score, best_cat = None, 0, None
            
            if not query_obj.color:
                m, s = self.get_fuzzy_match(search_token, self.catalog["COLORS"], cutoff=threshold)
                if s > best_score: best_match, best_score, best_cat = m, s, 'color'
            
            if not (query_obj.type or query_obj.type_list):
                m, s = self.get_fuzzy_match(search_token, self.catalog["TYPES"], cutoff=threshold)
                if s > best_score: best_match, best_score, best_cat = m, s, 'type'
            
            if not query_obj.location:
                m, s = self.get_fuzzy_match(search_token, self.catalog["LOCATIONS"], cutoff=threshold)
                if s > best_score: best_match, best_score, best_cat = m, s, 'location'
            
            if best_match and best_score >= threshold:
                if best_cat == 'color':
                    query_obj.color = best_match.title()
                elif best_cat == 'type':
                    match_lower = best_match.lower()
                    if has_all:
                        for group_name, members in self.catalog["VEHICLE_GROUPS"].items():
                            if match_lower in members:
                                query_obj.type_list = [t.title() for t in members]
                                query_obj.group_name = group_name.title()
                                query_obj.type = None
                                break
                        else:
                            query_obj.type = self.normalize_entity(match_lower, 'type')
                    else:
                        query_obj.type = self.normalize_entity(match_lower, 'type')
                elif best_cat == 'location':
                    query_obj.location = self.catalog["LOCATIONS_MAP"].get(best_match.lower(), best_match)
                for t in token.split(): used_tokens.add(t)
    
    def validate_query(self, query_obj):
        print("[Step 2] Validating Query Data...")
        # Handle both dict and SearchQuery object for backward compatibility during transition
        time_constraint = query_obj.time_constraint if hasattr(query_obj, 'time_constraint') else query_obj.get("time_constraint")
        
        if time_constraint:
            target_start, target_end = time_constraint
            if target_start > datetime.now():
                print("--> Validation Failed: Cannot search for records in the future!")
                return False
        return True

    def calculate_velocity(self, p1, p2):
        # Coordinates: lat, lon, datetime
        dist = haversine(p1[0], p1[1], p2[0], p2[1])
        time_diff_hours = (p2[2] - p1[2]).total_seconds() / 3600.0
        
        if time_diff_hours <= 0:
            return float('inf')
        return dist / time_diff_hours

    def log_search(self, db, query_obj):
        print("[Step 3] Auditing search query to persistence memory...")
        cursor = None
        try:
            cursor = db.cursor()
            # If it's a SearchQuery object, convert to dict for logging
            serializable_data = query_obj.to_dict() if hasattr(query_obj, 'to_dict') else query_obj.copy()
            
            if serializable_data.get("time_constraint"):
                t_start, t_end = serializable_data["time_constraint"]
                serializable_data["time_constraint"] = f"{t_start.isoformat()} to {t_end.isoformat()}"
            
            # Insert tracking log
            cursor.execute(
                "INSERT INTO search_audit_logs (parsed_query) VALUES (%s)",
                (json.dumps(serializable_data),)
            )
            db.commit()
        except Exception as e:
            print(f"Warning: Could not log search audit. Ensure 'search_audit_logs' table exists. ({e})")
        finally:
            if cursor:
                cursor.close()

    def search(self, user_input):
        query_obj = self.parse_query(user_input)
        
        if not self.validate_query(query_obj):
            return
            
        db = get_connection()
        if not db:
            print("ERROR: Could not establish a database connection.")
            return

        try:
            with db:
                self.log_search(db, query_obj)
                query, params = self._build_search_query(query_obj)
                
                # Execution Plan Check
                self._explain_query(db, query, params)

                print("\nExecuting main query...")
                results = self._execute_sql(db, query, params)

                if not results:
                    results = self._handle_search_fallbacks(db, query_obj, params)
                
                if results:
                    print(f"Found {len(results)} matches.")
                    self.reconstruct_paths(results)
                else:
                    self._report_no_results(db, query_obj)

        except Exception as e:
            print(f"ERROR during search execution: {e}")
        finally:
            if db:
                db.close()

    def _build_search_query(self, query_obj):
        """Constructs the SQL query and parameters."""
        print("\n[Step 4] Query Construction (Parameterized)...")
        query = """
            SELECT l.object_id, l.sighting_time, c.location_name, c.latitude, c.longitude, l.object_colour, l.object_type
            FROM surveillance_logs l
            JOIN cameras c ON l.camera_id = c.camera_id
            WHERE 1=1
        """
        params = []
        
        if query_obj.color:
            query += " AND l.object_colour = %s"
            params.append(query_obj.color)
        
        if query_obj.vehicle_id:
            query += " AND l.object_id = %s"
            params.append(query_obj.vehicle_id)
        
        if query_obj.type_list:
            placeholders = ', '.join(['%s'] * len(query_obj.type_list))
            query += f" AND l.object_type IN ({placeholders})"
            params.extend(query_obj.type_list)
        elif query_obj.type:
            query += " AND l.object_type = %s"
            params.append(query_obj.type)
        
        if query_obj.location:
            query += " AND c.location_name = %s"
            params.append(query_obj.location)
        
        if query_obj.time_constraint:
            query += " AND l.sighting_time BETWEEN %s AND %s"
            params.append(query_obj.time_constraint[0])
            params.append(query_obj.time_constraint[1])
            
        query += " ORDER BY l.sighting_time ASC"
        return query, params

    def _explain_query(self, db, query, params):
        """Prints the execution plan for the query."""
        print("\n[Step 5] Fetching Optimized Retrieval Data (EXPLAIN block):")
        explain_query = "EXPLAIN " + query
        try:
            with db.cursor(dictionary=True) as cursor:
                cursor.execute(explain_query, tuple(params))
                plan = cursor.fetchall()
                print("   Used Indexes Keys:")
                for index, step in enumerate(plan):
                    print(f"    -> Table {step['table']}: {step['key'] if step['key'] else 'Whole Table Scan WARNING!'}")
        except:
            print("   (Explain plan not available for this database/query)")

    def _execute_sql(self, db, query, params):
        """Executes the SQL query and returns results."""
        with db.cursor() as cursor:
            cursor.execute(query, tuple(params))
            return cursor.fetchall()

    def _handle_search_fallbacks(self, db, query_obj, params):
        """Handles fallbacks when no results are found."""
        if query_obj.time_constraint and not query_obj.date_mentioned:
            print("\n[Notice] No matches found for today. Searching all dates for this time range...")
            # Create a temporary query for fallback
            # Note: This is a simplified fallback; in a real app, we'd rebuild the query properly
            # but here we're maintaining the original logic
            query, _ = self._build_search_query(query_obj)
            fallback_query = query.replace("l.sighting_time BETWEEN %s AND %s", 
                                         "l.sighting_time_only BETWEEN TIME(%s) AND TIME(%s)")
            return self._execute_sql(db, fallback_query, params)
        return []

    def _report_no_results(self, db, query_obj):
        """Reports that no results were found and gives hints."""
        print("\n[Notice] No matches for this specific query. Checking general existence...")
        
        cursor = db.cursor()
        if query_obj.type_list:
            placeholders = ', '.join(['%s'] * len(query_obj.type_list))
            object_query = f"SELECT COUNT(*) FROM surveillance_logs l WHERE l.object_colour = %s AND l.object_type IN ({placeholders})"
            cursor.execute(object_query, (query_obj.color, *query_obj.type_list))
        else:
            object_query = "SELECT COUNT(*) FROM surveillance_logs l WHERE l.object_colour = %s AND l.object_type = %s"
            cursor.execute(object_query, (query_obj.color, query_obj.type))
        
        count = cursor.fetchone()[0]
        type_label = query_obj.group_name or query_obj.type or "vehicle"
        if count > 0:
            print(f"--> Found {count} sightings of {query_obj.color} {type_label} at other times/dates.")
            print("--> Try searching without time constraints or for a different date.")
        else:
            print(f"--> No sightings of {query_obj.color} {type_label} found in the entire database.")
        cursor.close()
            
    def reconstruct_paths(self, results):
        # Group by objects
        objects_paths = {}
        for row in results:
            obj_id = row[0]
            obj_data = {
                "time": row[1],
                "location": row[2],
                "lat": row[3],
                "lon": row[4],
                "color": row[5],
                "type": row[6]
            }
            if obj_id not in objects_paths:
                objects_paths[obj_id] = []
            objects_paths[obj_id].append(obj_data)
            
        # Check velocities
        flagged_objects = []
        for obj_id, path in objects_paths.items():
            print(f"\nEvaluating Object ID: {obj_id} ({path[0]['color']} {path[0]['type']})")
            
            journey_string = [path[0]['location']]
            
            for i in range(1, len(path)):
                p1 = (path[i-1]['lat'], path[i-1]['lon'], path[i-1]['time'])
                p2 = (path[i]['lat'], path[i]['lon'], path[i]['time'])
                
                velocity = self.calculate_velocity(p1, p2)
                journey_string.append(path[i]['location'])
                
                marker = ""
                if velocity > self.max_logical_speed_kmh:
                    marker = f" [FLAG: {velocity:.2f} km/h - PHYSICALLY IMPOSSIBLE]"
                    if obj_id not in flagged_objects:
                        flagged_objects.append(obj_id)
                else:
                    marker = f" (Speed: {velocity:.2f} km/h)"
                    
                print(f"  Stage {i}: {path[i-1]['location']} -> {path[i]['location']}{marker}")
                
            print(f"  Proven Path: {' -> '.join(journey_string)}")
            
        if flagged_objects:
            print(f"\n[Step 7] Threat Assessment & Alerting:")
            print(f"  WARNING: {len(flagged_objects)} object(s) flagged for velocity cheating!")
        else:
            print("\n[Step 7] Threat Assessment & Alerting:")
            print("  No suspicious velocity patterns detected in this dataset.")

if __name__ == "__main__":
    srch = SearchEngine()
    
    import sys
    
    if len(sys.argv) > 1:
        # If arguments are passed, run them
        query = " ".join(sys.argv[1:])
        srch.search(query)
    else:
        # Interactive mode
        print("\n=== ADVANCED SURVEILLANCE SEARCH ENGINE ===")
        print("Type 'exit' to quit. Try searching like 'red car in Rohini at 4 pm'.")
        
        while True:
            try:
                user_input = input("\nEnter Search Query: ").strip()
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("Exiting search engine...")
                    break
                if not user_input:
                    continue
                srch.search(user_input)
            except KeyboardInterrupt:
                print("\nExiting search engine...")
                break
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
