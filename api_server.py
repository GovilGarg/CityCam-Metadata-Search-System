print("Starting API Server script...")
import http.server
import json
import sys
import os
import urllib.parse
print("Importing StructuredSearchEngine...")
from structured_search import StructuredSearchEngine
print("Imports successful.")

# Add parent directory to path to import local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SearchAPIHandler(http.server.BaseHTTPRequestHandler):
    search_engine = StructuredSearchEngine()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'healthy'}).encode())
        elif self.path == '/api/ollama':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            is_active = self.search_engine.intelligence.is_active()
            self.wfile.write(json.dumps({'ollama_active': is_active}).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        print(f"POST request to {self.path}")
        if self.path == '/api/search':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                query = data.get('query', '')
                
                if not query:
                    self._send_json({'success': False, 'error': 'No query provided'}, 400)
                    return

                result = self.search_engine.search_structured(query)
                self._send_json(result)

            except Exception as e:
                self._send_json({'success': False, 'error': str(e)}, 500)
        elif self.path == '/api/ollama/toggle':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                active = data.get('active', True)
                self.search_engine.intelligence.set_active(active)
                self._send_json({'ollama_active': self.search_engine.intelligence.is_active()})
            except Exception as e:
                self._send_json({'success': False, 'error': str(e)}, 500)
        else:
            self.send_error(404)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

def run_server(port=5000):
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, SearchAPIHandler)
    print(f"API Server running on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
