#!/bin/bash
cd /home/abee/project/codetrace/backend
# Use setsid to detach from the terminal
setsid /home/abee/project/codetrace/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 </dev/null >/tmp/uvicorn.log 2>&1 &
disown
echo "uvicorn started with pid $!"
