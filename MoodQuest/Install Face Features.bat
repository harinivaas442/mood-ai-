@echo off
cd /d "%~dp0"
echo Installing the face model and extras. This can take several minutes and a few GB...
python -m pip install transformers torch pillow scikit-learn opencv-python streamlit-sortables Authlib
echo.
echo Optional face dots (may not work on every Python version):
python -m pip install mediapipe
echo.
echo Done. Now double-click "Start Mood Quest.bat".
pause
