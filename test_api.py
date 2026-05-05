import urllib.request
import json

def test_search():
    url = "http://localhost:5000/api/search"
    payload = json.dumps({"query": "red cars at saket"}).encode('utf-8')
    
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Status: {response.status}")
            data = json.loads(response.read().decode('utf-8'))
            print(f"Success: {data.get('success')}")
            if data.get('success'):
                print(f"Results found: {data.get('result_count')}")
                print(f"Parsed Type List: {data.get('parsed', {}).get('type_list')}")
                if data.get('results'):
                    print("First result:", data.get('results')[0])
            else:
                print(f"Error: {data.get('error')}")
                print(f"Warnings: {data.get('warnings')}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == '__main__':
    test_search()
