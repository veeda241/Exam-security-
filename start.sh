#!/bin/bash
# Start script for Render deployment
export PYTHONPATH=server
exec uvicorn server.main:app --host 0.0.0.0 --port $PORT
