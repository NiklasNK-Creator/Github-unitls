@echo off
setlocal
set SCRIPT_DIR=%~dp0
set PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    echo Python environment not found. Run the package setup first.
    exit /b 1
)

"%PYTHON_EXE%" "%SCRIPT_DIR%cli.py" %*
exit /b %errorlevel%
