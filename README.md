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

1. **Install Homebrew**: If you don't have Homebrew, open the Terminal (you can find it in Applications -> Utilities) and paste the following command, then press Enter:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   Follow the on-screen instructions.

2. **Install Python**: Once Homebrew is installed, run the following command in the Terminal:
   ```bash
   brew install python
   ```

3. **Verify Installation**: Close and reopen the Terminal, then type `python3 --version`. If it shows a version number, you're ready to go.

#### Linux 🐧

Most Linux distributions come with Python pre-installed. You can verify this by opening a Terminal and typing `python3 --version`. If it's not installed or you need a newer version, use your distribution's package manager.

**For Debian/Ubuntu-based systems:**
```bash
sudo apt update
sudo apt install python3 python3-pip
```

**For Fedora/CentOS/RHEL-based systems:**
```bash
sudo dnf install python3 python3-pip
```

### 2. Game Dependencies Installation

After installing Python, you need to install the necessary libraries for the game. We've included installation scripts to make this easy.

#### Windows Users

1. **Double-click** the `install_dependencies.bat` file in the game folder
2. The script will automatically install Pygame and NumPy
3. Press any key when installation is complete

Alternatively, you can run it from Command Prompt:
```cmd
install_dependencies.bat
```

#### macOS and Linux Users

1. **Open Terminal** in the game folder
2. **Make the script executable** (first time only):
   ```bash
   chmod +x install_dependencies.sh
   ```
3. **Run the installation script**:
   ```bash
   ./install_dependencies.sh
   ```

#### Manual Installation (All Platforms)

If you prefer to install dependencies manually, run:
```bash
pip install pygame numpy
```
or on macOS/Linux:
```bash
pip3 install pygame numpy
```

## How to Play

### Single-Player (Offline) Mode

To play by yourself, simply run the `main.py` file without any arguments. This mode uses the same host logic but without a second player.

```bash
python main.py
```

### Online Co-op

To play with a friend, one person must act as the host and the other as the client.

#### Hosting a Game 💻

The host runs the server, which simulates the game world and handles the game state. The host's computer needs to be accessible to the client.

1. Open a Terminal or Command Prompt in the directory containing `main.py`.
2. Run the host command, specifying a port number (e.g., 5000).
   ```bash
   python main.py --host 5000
   ```
3. Find your IP address and share it with your friend. If you're on a LAN, this will be a local IP (e.g., 192.168.1.100). If you're on the internet, you'll need your public IP and may need to set up port forwarding on your router for the chosen port (5000).

#### Joining a Game 🎮

The client connects to the host's server and sends their input. The game state is streamed from the host to the client.

1. Open a Terminal or Command Prompt in the directory with `main.py`.
2. Run the join command, using the host's IP address and the specified port.
   ```bash
   python main.py --join <HOST_IP>:<PORT>
   ```

For example, if the host's IP is 127.0.0.1 (for local testing) and the port is 5000:
```bash
python main.py --join 127.0.0.1:5000
```

## Controls

The game supports both keyboard/mouse and gamepad controls.

| Action | Keyboard/Mouse | Gamepad |
|--------|----------------|---------|
| Move | WASD | Left Stick |
| Aim | Mouse | Right Stick |
| Fire | Left Mouse Button | RT / A Button |
| Restart | R (Host only) | Not available |
| Buy Upgrade | 1, 2, 3, 4 (Host only) | Not available |
| Skip Shop | B (Host only) | Not available |

## Technical Notes

- **Network Protocol**: The game uses a simple, custom netcode that sends JSON messages over TCP. This is intended for learning and demonstration purposes. It is not secure and should not be exposed to the public internet without proper hardening.

- **Host-Authoritative Model**: The host's machine is the source of truth for all game physics and state. The client sends input commands to the host, which then simulates the game and sends back a snapshot of the world. This prevents cheating and simplifies synchronization.

- **Port Forwarding**: To play over the internet, the host must configure their router to forward the chosen port to their computer's local IP address. This allows the client's connection request to reach the host's machine.
