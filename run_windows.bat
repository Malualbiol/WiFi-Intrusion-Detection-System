@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
.venv\Scripts\python.exe wids.py generate
if errorlevel 1 goto error
.venv\Scripts\python.exe wids.py train
if errorlevel 1 goto error
.venv\Scripts\python.exe wids.py demo
if errorlevel 1 goto error
echo.
echo FINISHED. Open results\confusion_matrix.png and results\metrics.json
pause
exit /b 0
:error
echo Something failed. Check Python installation and error messages above.
pause
exit /b 1
