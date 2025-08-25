# Tiny Planet: Siege

Tiny Planet: Siege is an action-packed, online co-op twin-stick shooter where you and a friend defend your tiny planet's core from relentless waves of enemies. Featuring boss fights, power-ups, and a persistent upgrade shop, this game is built with Python and Pygame. It's designed to be a fun, accessible project that also serves as a demonstration of networking in game development.

The game can be enjoyed in single-player offline mode or in 2-player online co-op over a LAN or the internet.

## Features

- **Online 2-Player Co-op**: Team up with a friend to defend the planet's core. The game uses a host-authoritative server model.
- **Single-Player Mode**: Fully playable offline for a solo experience.
- **Intense Gameplay**: Face escalating waves of enemies, culminating in challenging boss fights every five waves.
- **Power-ups and Upgrades**: Collect coins from defeated foes to purchase powerful upgrades in the shop between waves. Find power-ups like health packs, shields, and overdrive for a temporary boost.
- **Dynamic Visuals**: Features a lighting and particle system for exciting visual feedback.
- **Controller Support**: Play with a gamepad for a classic twin-stick shooter feel.
- **Procedural Audio**: Optional sound effects generated with NumPy for a richer auditory experience.

## Installation Guide

To play "Tiny Planet: Siege," you'll first need to install Python, and then the game's dependencies. Follow the instructions for your operating system below.

### 1. Python Installation

#### Windows 📝

1. **Download Python**: Go to the official Python website at [python.org/downloads](https://python.org/downloads).
2. **Run the Installer**: Click the "Download Python" button for the latest version. Once downloaded, run the installer.
3. **Important Step**: On the first screen of the installer, make sure to check the box that says "Add Python to PATH". This is crucial for the installation scripts to work.
4. **Complete Installation**: Click "Install Now" and follow the on-screen prompts to complete the installation.
5. **Verify Installation**: Open the Command Prompt (search for "cmd" in the Start Menu) and type `python --version`. If it shows a version number, you're all set!

#### macOS 🍎

Modern versions of macOS come with Python pre-installed. However, it's recommended to install a newer version using Homebrew.

1. **Install Homebrew**: If you don't have Homebrew, open the Terminal (Applications -> Utilities) and paste:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. **Install Python**:
   ```bash
   brew install python
   ```
3. **Verify Installation**:
   ```bash
   python3 --version
   ```

---

## Dependencies Installation

Before running the game, you need to install Python and the required Python libraries. To simplify this process, we’ve included installation scripts for each platform.

### Windows Users 📝

1. **Open Terminal or Command Prompt** in the game folder.
2. **Run the installation script**:
```cmd
windows_install.bat
```
- This script will automatically:
  - Install Python (if not already installed)
  - Create a virtual environment
  - Install Pygame, NumPy, and PyInstaller
  - Build the `.exe` executable in the `dist` folder
3. Press any key when the installation completes.

### macOS Users 🍎

1. **Open Terminal** in the game folder.
2. **Make the script executable** (first time only):
```bash
chmod +x macos_install.sh
```
3. **Run the installation script**:
```bash
./macos_install.sh
```
4. Ensure the resulting executable has execute permissions:
```bash
chmod +x dist/main
```

### Manual Installation (All Platforms)

```bash
# Windows
pip install pygame numpy pyinstaller

# macOS
pip3 install pygame numpy pyinstaller
```

---

## How to Play

### Single-Player (Offline) Mode

Run the executable or `main.py` without arguments:

```bash
# Windows
dist\main.exe

# macOS
./dist/main
```

### Online Co-op

#### Hosting a Game 💻
```bash
python main.py --host 5000
```
Share your IP with your friend (LAN or internet; configure port forwarding for public access).

#### Joining a Game 🎮
```bash
python main.py --join <HOST_IP>:<PORT>
```
Example:
```bash
python main.py --join 127.0.0.1:5000
```

---

## Controls

| Action | Keyboard/Mouse | Gamepad |
|--------|----------------|---------|
| Move | WASD | Left Stick |
| Aim | Mouse | Right Stick |
| Fire | Left Mouse Button | RT / A Button |
| Restart | R (Host only) | Not available |
| Buy Upgrade | 1,2,3,4 (Host only) | Not available |
| Skip Shop | B (Host only) | Not available |

---

## Technical Notes

- **Network Protocol**: JSON messages over TCP; not secure for public internet.
- **Host-Authoritative Model**: Host simulates game physics and sends updates to the client.
- **Port Forwarding**: Needed for internet play; forward chosen port to host machine.

---

## Distribution Scripts Summary

| Platform | Script | Description |
|----------|--------|-------------|
| Windows | `windows_install.bat` | Installs Python, dependencies, builds `.exe` |
| macOS | `macos_install.sh` | Installs Python, dependencies, builds `.app`/executable |

> Ensure scripts have **execute permissions** on macOS:
```bash
chmod +x macos_install.sh
chmod +x dist/main
```
