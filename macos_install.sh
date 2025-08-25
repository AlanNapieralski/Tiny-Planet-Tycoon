
#!/bin/bash
echo "============================================="
echo "Installing and building My Pygame Game"
echo "============================================="

# ------------------------------
# 1. Check Python installation
# ------------------------------
if ! command -v python3 &> /dev/null
then
    echo "Python3 is not installed. Downloading Python 3.12 installer..."
    # Download official Python installer for macOS
    curl -O https://www.python.org/ftp/python/3.12.1/python-3.12.1-macos11.pkg
    echo "Installing Python..."
    sudo installer -pkg python-3.12.1-macos11.pkg -target /
    rm python-3.12.1-macos11.pkg

    # Verify installation
    if ! command -v python3 &> /dev/null
    then
        echo "Python installation failed. Please install manually."
        exit 1
    else
        echo "Python installed successfully!"
    fi
else
    echo "Python found!"
fi

# ------------------------------
# 2. Create virtual environment
# ------------------------------
echo "Creating virtual environment..."
python3 -m venv venv

# Activate venv
source venv/bin/activate

# ------------------------------
# 3. Upgrade pip
# ------------------------------
echo "Upgrading pip..."
python3 -m pip install --upgrade pip

# ------------------------------
# 4. Install dependencies
# ------------------------------
echo "Installing required packages..."
pip install pygame pyinstaller

# ------------------------------
# 5. Build executable with PyInstaller
# ------------------------------
echo "Building executable..."
# Use colon (:) on macOS for --add-data
pyinstaller --onefile --add-data "sound:sound" main.py

# ------------------------------
# 6. Finish
# ------------------------------
echo "============================================="
echo "Build complete!"
echo "Your executable is in the dist folder."
echo "To play the game, run: dist/main"
echo "============================================="

# Deactivate virtual environment
deactivate
