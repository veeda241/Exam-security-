import urllib.request
import json
import sys

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "https://exam-security.onrender.com"

def test_deployment():
    try:
        print(f"Testing Deployment @ {BASE_URL}...")
        
        # 1. API Info
        print(f"\n1. API Info ({BASE_URL}/api)...")
        try:
            with urllib.request.urlopen(f"{BASE_URL}/api", timeout=15) as res:
                data = json.loads(res.read())
                print(f"   Success! Name: {data.get('name')} | Version: {data.get('version')}")
        except Exception as e:
            print(f"   ❌ API Info Error: {e}")

        # 2. Dashboard Stats
        print(f"\n2. Dashboard Stats ({BASE_URL}/api/analysis/dashboard)...")
        try:
            with urllib.request.urlopen(f"{BASE_URL}/api/analysis/dashboard", timeout=25) as res:
                data = json.loads(res.read())
                print(f"   Success! {len(data)} student summaries retrieved.")
                if data:
                    s = data[0]
                    print(f"      Sample: {s.get('name')} | Status: {s.get('status')} | URL: {s.get('last_visited_url')}")
        except Exception as e:
            print(f"   ❌ Dashboard Error: {e}")
            if hasattr(e, 'read'):
                print(f"      Response: {e.read().decode()}")

        # 3. Sessions
        print(f"\n3. Sessions List ({BASE_URL}/api/sessions/)...")
        try:
            with urllib.request.urlopen(f"{BASE_URL}/api/sessions/", timeout=15) as res:
                data = json.loads(res.read())
                print(f"   Success! {len(data)} sessions found.")
        except Exception as e:
            print(f"   ❌ Sessions Error: {e}")

    except Exception as e:
        print(f"\n❌ Overall Test Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_deployment()
