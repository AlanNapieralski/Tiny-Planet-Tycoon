
@echo off
echo =============================================
echo Installing and building My Pygame Game
echo =============================================

REM ------------------------------
REM 1. Check Python installation
REM ------------------------------
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python is not installed. Please install Python 3.9 or higher.
    pause
    exit /b
) ELSE (
    echo Python found!
)

REM ------------------------------
REM 2. Create virtual environment
REM ------------------------------
echo Creating virtual environment...
python -m venv venv

REM Activate venv
call venv\Scripts\activate

REM ------------------------------
REM 3. Upgrade pip
REM ------------------------------
echo Upgrading pip...
python -m pip install --upgrade pip

REM ------------------------------
REM 4. Install dependencies
REM ------------------------------
echo Installing required packages...
pip install pygame pyinstaller

REM ------------------------------
REM 5. Build executable with PyInstaller
REM ------------------------------
echo Building executable...
REM --onefile: single .exe
REM --windowed: no console window
REM --icon: your game icon (ico file)
REM --add-data: include sounds and images
pyinstaller --onefile --windowed --icon=game_icon.ico --add-data "sounds;sounds" --add-data "images;images" main.py

REM ------------------------------
REM 6. Finish
REM ------------------------------
echo =============================================
echo Build complete!
echo Your executable is in the "dist" folder.
echo To play the game, run: dist\main.exe
echo =============================================

REM Deactivate virtual environment
deactivate

pause
