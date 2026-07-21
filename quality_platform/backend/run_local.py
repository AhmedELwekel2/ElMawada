"""Local development launcher for the backend."""
import sys
import os

# Add the project root and quality_bot to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
backend_dir = os.path.dirname(os.path.abspath(__file__))
bot_dir = os.path.join(project_root, 'quality_bot')

for p in [project_root, backend_dir, bot_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)