import sys
import os
import io
from contextlib import redirect_stdout, redirect_stderr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_engine import SearchEngine
from connect_db import get_connection

class StructuredSearchEngine(SearchEngine):
    def search_structured(self, user_input):
        self._prepare_state()
        
        parsed = self.parse_query(user_input)
        self._last_parsed = parsed

        if not self.validate_query(parsed):
            return {
                'success': False,
                'error': 'Query validation failed',
                'parsed': parsed.to_dict() if hasattr(parsed, 'to_dict') else parsed
            }

        db = get_connection()
        if not db:
            return {'success': False, 'error': 'Database connection failed'}

        try:
            with db:
                self.log_search(db, parsed)
                query, params = self._build_query(parsed)
                self._update_query_info(query, params, parsed)

                results = self._execute_query(db, query, params)

                if not results:
                    return self._handle_no_results(db, parsed, params)

                paths, velocity_flags = self._reconstruct_paths_structured(results)
                self._last_paths = paths
                self._last_velocity_flags = velocity_flags

                return self._format_response(parsed, results, paths, velocity_flags)
        except Exception as e:
            print(f"DEBUG: Error in search_structured: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if db:
                db.close()

    def _prepare_state(self):
        """Initializes internal state for a new search."""
        self._last_parsed = None
        self._last_results = []
        self._last_paths = []
        self._last_velocity_flags = []
        self._last_query_info = {}
        self._warnings = []

    def _update_query_info(self, query, params, parsed):
        """Updates query info for debugging and logging."""
        # Handle both SearchQuery object and legacy dict
        if hasattr(parsed, 'to_dict'):
            p_dict = parsed.to_dict()
        else:
            p_dict = parsed

        self._last_query_info = {
            'query': query,
            'params': params,
            'color': p_dict.get('color'),
            'type': p_dict.get('type'),
            'type_list': p_dict.get('type_list'),
            'location': p_dict.get('location'),
            'vehicle_id': p_dict.get('vehicle_id'),
            'time_constraint': str(p_dict.get('time_constraint')) if p_dict.get('time_constraint') else None
        }

    def _handle_no_results(self, db, parsed, params):
        """Handles the case where no results are found, including fallback search."""
        if hasattr(parsed, 'to_dict'):
            p_dict = parsed.to_dict()
        else:
            p_dict = parsed

        color_str = f"{p_dict.get('color')} " if p_dict.get('color') else ""
        type_str = p_dict.get('group_name') or p_dict.get('type') or \
                   (p_dict.get('type_list')[0] if p_dict.get('type_list') else "vehicles")
        
        display_type = type_str if type_str.lower().endswith('s') else f"{type_str}s"
        loc_str = f" at {p_dict.get('location')}" if p_dict.get('location') else ""
        
        # Try fallback search (ignore date/time constraints)
        results = self._execute_fallback_query(db, parsed, params)

        if not results:
            count_info = self._check_object_existence(db, parsed)
            if count_info['exists']:
                self._warnings.append(f"We found {count_info['count']} {color_str}{display_type} in the system, but none{loc_str}. Try searching without the location.")
            else:
                self._warnings.append(f"No {color_str}{display_type} found in the entire surveillance system.")

            return {
                'success': True,
                'parsed': p_dict,
                'query_info': self._last_query_info,
                'warnings': self._warnings,
                'object_count': count_info,
                'results': [],
                'result_count': 0,
                'paths': []
            }
        else:
            self._warnings.append(f'No {color_str}{display_type} found{loc_str} for today. Showing results from all dates.')
            paths, velocity_flags = self._reconstruct_paths_structured(results)
            return self._format_response(parsed, results, paths, velocity_flags)

    def _format_response(self, parsed, results, paths, velocity_flags):
        """Formats the final search response."""
        if hasattr(parsed, 'to_dict'):
            p_dict = parsed.to_dict()
        else:
            p_dict = parsed

        return {
            'success': True,
            'parsed': p_dict,
            'query_info': self._last_query_info,
            'warnings': self._warnings,
            'results': results,
            'result_count': len(results),
            'paths': paths,
            'velocity_flags': velocity_flags
        }

    def _build_query(self, parsed):
        p_dict = parsed.to_dict() if hasattr(parsed, 'to_dict') else parsed
        query = """
            SELECT l.object_id, l.sighting_time, c.location_name, c.latitude, c.longitude, l.object_colour, l.object_type
            FROM surveillance_logs l
            JOIN cameras c ON l.camera_id = c.camera_id
            WHERE 1=1
        """
        params = []

        if p_dict.get('color'):
            query += " AND l.object_colour = %s"
            params.append(p_dict['color'])

        if p_dict.get('vehicle_id'):
            query += " AND l.object_id = %s"
            params.append(p_dict['vehicle_id'])

        if p_dict.get('type_list'):
            placeholders = ', '.join(['%s'] * len(p_dict['type_list']))
            query += f" AND l.object_type IN ({placeholders})"
            params.extend(p_dict['type_list'])
        elif p_dict.get('type'):
            query += " AND l.object_type = %s"
            params.append(p_dict['type'])

        if p_dict.get('location'):
            query += " AND c.location_name = %s"
            params.append(p_dict['location'])

        if p_dict.get('time_constraint'):
            query += " AND l.sighting_time BETWEEN %s AND %s"
            params.append(p_dict['time_constraint'][0])
            params.append(p_dict['time_constraint'][1])

        query += " ORDER BY l.sighting_time ASC"
        return query, params

    def _execute_query(self, db, query, params):
        cursor = None
        try:
            cursor = db.cursor()
            cursor.execute(query, tuple(params))
            return cursor.fetchall()
        except Exception as e:
            print(f"DEBUG: Error in _execute_query: {e}")
            raise e
        finally:
            if cursor:
                cursor.close()

    def _execute_fallback_query(self, db, parsed, original_params):
        p_dict = parsed.to_dict() if hasattr(parsed, 'to_dict') else parsed
        query = """
            SELECT l.object_id, l.sighting_time, c.location_name, c.latitude, c.longitude, l.object_colour, l.object_type
            FROM surveillance_logs l
            JOIN cameras c ON l.camera_id = c.camera_id
            WHERE 1=1
        """
        fallback_params = []

        if p_dict.get('color'):
            query += " AND l.object_colour = %s"
            fallback_params.append(p_dict['color'])

        if p_dict.get('vehicle_id'):
            query += " AND l.object_id = %s"
            fallback_params.append(p_dict['vehicle_id'])

        if p_dict.get('type_list'):
            placeholders = ', '.join(['%s'] * len(p_dict['type_list']))
            query += f" AND l.object_type IN ({placeholders})"
            fallback_params.extend(p_dict['type_list'])
        elif p_dict.get('type'):
            query += " AND l.object_type = %s"
            fallback_params.append(p_dict['type'])

        if p_dict.get('location'):
            query += " AND c.location_name = %s"
            fallback_params.append(p_dict['location'])

        if p_dict.get('time_constraint'):
            query += " AND TIME(l.sighting_time) BETWEEN TIME(%s) AND TIME(%s)"
            fallback_params.append(p_dict['time_constraint'][0])
            fallback_params.append(p_dict['time_constraint'][1])

        query += " ORDER BY l.sighting_time ASC"

        cursor = None
        try:
            cursor = db.cursor()
            cursor.execute(query, tuple(fallback_params))
            return cursor.fetchall()
        except Exception as e:
            print(f"DEBUG: Error in _execute_fallback_query: {e}")
            raise e
        finally:
            if cursor:
                cursor.close()

    def _check_object_existence(self, db, parsed):
        p_dict = parsed.to_dict() if hasattr(parsed, 'to_dict') else parsed
        result = {'exists': False, 'count': 0}
        cursor = None
        try:
            cursor = db.cursor()
            if p_dict.get('vehicle_id'):
                object_query = "SELECT COUNT(*) FROM surveillance_logs l WHERE l.object_id = %s"
                cursor.execute(object_query, (p_dict['vehicle_id'],))
            elif p_dict.get('type_list'):
                placeholders = ', '.join(['%s'] * len(p_dict['type_list']))
                if p_dict.get('color'):
                    object_query = f"SELECT COUNT(*) FROM surveillance_logs l WHERE l.object_colour = %s AND l.object_type IN ({placeholders})"
                    cursor.execute(object_query, (p_dict['color'], *p_dict['type_list']))
                else:
                    object_query = f"SELECT COUNT(*) FROM surveillance_logs l WHERE l.object_type IN ({placeholders})"
                    cursor.execute(object_query, tuple(p_dict['type_list']))
            elif p_dict.get('type'):
                if p_dict.get('color'):
                    object_query = "SELECT COUNT(*) FROM surveillance_logs l WHERE l.object_colour = %s AND l.object_type = %s"
                    cursor.execute(object_query, (p_dict['color'], p_dict['type']))
                else:
                    object_query = "SELECT COUNT(*) FROM surveillance_logs l WHERE l.object_type = %s"
                    cursor.execute(object_query, (p_dict['type'],))
            else:
                return result

            row = cursor.fetchone()
            if row:
                count = row[0]
                result = {'exists': count > 0, 'count': count}
            return result
        except Exception as e:
            print(f"DEBUG: Error in _check_object_existence: {e}")
            raise e
        finally:
            if cursor:
                cursor.close()

    def _reconstruct_paths_structured(self, results):
        objects_paths = {}
        for row in results:
            obj_id = row[0]
            obj_data = {
                'time': row[1],
                'location': row[2],
                'lat': float(row[3]),
                'lon': float(row[4]),
                'color': row[5],
                'type': row[6]
            }
            if obj_id not in objects_paths:
                objects_paths[obj_id] = []
            objects_paths[obj_id].append(obj_data)

        paths = []
        velocity_flags = []

        for obj_id, path in objects_paths.items():
            path_info = {
                'object_id': obj_id,
                'color': path[0]['color'],
                'type': path[0]['type'],
                'journey': [],
                'stages': []
            }

            for i in range(1, len(path)):
                p1 = (path[i-1]['lat'], path[i-1]['lon'], path[i-1]['time'])
                p2 = (path[i]['lat'], path[i]['lon'], path[i]['time'])

                velocity = self.calculate_velocity(p1, p2)
                stage = {
                    'from': path[i-1]['location'],
                    'to': path[i]['location'],
                    'velocity_kmh': velocity,
                    'flagged': velocity > self.max_logical_speed_kmh
                }
                path_info['stages'].append(stage)

                if stage['flagged']:
                    if obj_id not in velocity_flags:
                        velocity_flags.append(obj_id)

            path_info['journey'] = ' -> '.join([s['from'] for s in path_info['stages']]) + ' -> ' + path[-1]['location']
            paths.append(path_info)

        return paths, velocity_flags
