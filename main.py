import sys
import os
import importlib.util

backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load backend/main.py cleanly without circular root conflict
spec = importlib.util.spec_from_file_location("backend_main", os.path.join(backend_dir, "main.py"))
backend_main = importlib.util.module_from_spec(spec)
sys.modules["backend_main"] = backend_main
spec.loader.exec_module(backend_main)

app = backend_main.app
