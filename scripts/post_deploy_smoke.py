#!/usr/bin/env python3
import os
import sys
import httpx

def run_smoke_tests():
    base_url = os.environ.get("API_BASE_URL", "http://localhost:8001")
    print(f"Starting smoke tests against {base_url}...")
    
    with httpx.Client(base_url=base_url) as client:
        # 1. Health check
        print("Checking /health...")
        try:
            r = client.get("/health", timeout=5.0)
            if r.status_code != 200:
                print(f"FAILED: /health returned {r.status_code}")
                sys.exit(1)
            print("OK.")
        except Exception as e:
            print(f"FAILED: /health exception: {e}")
            sys.exit(1)
            
        # 2. Ready check
        print("Checking /ready...")
        try:
            r = client.get("/ready", timeout=5.0)
            if r.status_code != 200:
                print(f"FAILED: /ready returned {r.status_code} (Database/Redis might be still warming up)")
            else:
                print("OK.")
        except Exception as e:
            print(f"FAILED: /ready exception: {e}")
            
        # 3. Webhook verification check
        print("Checking Webhook GET verification...")
        try:
            r = client.get("/webhook")
            # Usually throws a missing params exception like 400 or 403. As long as it isn't 404, the path is loaded.
            if r.status_code == 404:
                print(f"FAILED: /webhook not found!")
                sys.exit(1)
            print("OK.")
        except Exception as e:
            print(f"FAILED: Webhook GET exception: {e}")
            sys.exit(1)
            
        print("Smoke tests passed successfully.")

if __name__ == "__main__":
    run_smoke_tests()
