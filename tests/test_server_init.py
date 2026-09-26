"""
Test Server and Router Initialization
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.app import app

print(f"FastAPI app loaded successfully!")
print(f"Total registered routes: {len(app.routes)}")
route_paths = [r.path for r in app.routes if hasattr(r, 'path')]
print(f"Sample routes: {route_paths[:10]}")
