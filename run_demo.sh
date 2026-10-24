#!/bin/bash
# Simple launcher for the Dam Break prototype
cd "$(dirname "$0")"
echo "Starting Dam Break Inundation Modelling Prototype..."
echo "Open http://localhost:8501 in your browser"
streamlit run app/app.py --server.headless true
