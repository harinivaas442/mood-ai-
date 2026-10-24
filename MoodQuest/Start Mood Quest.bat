@echo off
cd /d "%~dp0"
echo Installing the basics (first time only)...
python -m pip install streamlit pandas --quiet
echo Starting AI Mood Quest+ ... your browser will open. Keep this window open.
python -m streamlit run app.py
pause
