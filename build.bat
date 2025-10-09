@echo off
REM Get the directory of this script
set SCRIPT_DIR=%~dp0

REM Change to the script's directory to ensure paths are correct
cd /d %SCRIPT_DIR%

REM Echo current directory for debugging
echo Current directory: %cd%

REM Check if main.spec exists
if not exist main.spec (
    echo ERROR: main.spec not found in %cd%!
    exit /b 1
)

echo Found main.spec. Running PyInstaller...

REM Run PyInstaller using python -m to avoid PATH issues
python -m PyInstaller main.spec

if %errorlevel% neq 0 (
    echo.
    echo ERROR: PyInstaller failed with error code %errorlevel%.
    exit /b %errorlevel%
)

echo.
echo Build completed successfully.
exit /b 0
