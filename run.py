import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.environ['PYTHONPATH'] = project_root

import uvicorn

if __name__ == "__main__":
    uvicorn.run("backend.api.main:app", reload=False, port=8001)