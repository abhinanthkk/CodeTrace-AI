#!/bin/bash
# Run the CodeTrace AI backend
cd /home/abee/project/codetrace/backend
exec /home/abee/project/codetrace/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
