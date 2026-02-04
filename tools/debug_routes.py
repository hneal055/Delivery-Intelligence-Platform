from src.backend.api.main import app
import json

print("Registered Routes:")
for route in app.routes:
    print(f"{route.path} {route.methods}")
