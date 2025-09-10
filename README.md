# FSAR - **Real-time file monitoring** - Watch for changes in any directory

An application that displays a directory tree and lights up files/folders with different colors when they change.

## Features

- **Real-time file monitoring** - Watch for changes in any directory
- **Visual tree display** - See your directory structure in a tree format
- **Color-coded activity** - Files light up with different colors based on activity type and recency:
  - 🟢 **Bright Green** - Newly created files (last 2 seconds)
  - 🟢 **Green** - Recently created files (last 5-10 seconds)
  - 🔴 **Bright Red** - Recently modified files (last 2 seconds)
  - 🟠 **Red/Orange** - Modified files (last 5-30 seconds)
  - ~~🗑️ **Strikethrough Red**~~ - Recently deleted files (shown for 30 seconds)
  - ⚪ **White** - No recent changes
- **File type indicators**:
  - 🆕 - Newly created files
  - 📄 - Regular files
  - 🗑️ - Recently deleted files
  - 📁 - Directories
  - **[NEW]** tag - Newly created files and directories (shown after filename)
  - **[EDITED]** tag - Recently modified files (shown after filename)

## Installation

### Download Pre-built Binaries

Head to [releases](https://github.com/foglomon/FSAR/releases/latest) and download the executable for your OS:

#### Windows

1. Download `FSAR-windows.exe`
2. **Important**: If Windows shows a warning or blocks the file, see [Windows Troubleshooting](#windows-troubleshooting) below
3. Double-click to run, or run from command prompt: `FSAR-windows.exe`

#### Linux

1. Download `FSAR-linux`
2. Make it executable: `chmod +x FSAR-linux`
3. Run: `./FSAR-linux`
4. (Optional) Move to PATH: `sudo cp FSAR-linux /usr/local/bin/fsar`

#### macOS

1. Download `FSAR-macos`
2. Make it executable: `chmod +x FSAR-macos`
3. First run: `./FSAR-macos` (macOS may show security warning)
4. If blocked, go to **System Preferences > Security & Privacy > General** and click **"Allow Anyway"**
5. Run again: `./FSAR-macos`
6. (Optional) Move to PATH: `sudo cp FSAR-macos /usr/local/bin/fsar`

(Note: Moving to PATH allows you to run **FSAR** from any terminal location.)

## Usage

Simply run the program and it will ask you questions to configure the monitoring:

```
Example interaction:


🚀 File System Activity Monitor
Watch files and directories light up as they change!

📁 Enter directory path to monitor (or '.' for current directory): .
🔔 Enable audio chime notifications? (y/n) [n]: y

✅ Configuration:
📂 Directory: C:\Users\YourName\Projects
🔔 Chime: Enabled

Starting monitor...
```

## Building

```bash
git clone https://github.com/foglomon/FSAR.git
cd FSAR
pip install -r requirements.txt
```

## Requirements

- Python 3.7+
- watchdog (for file system monitoring)
- rich (for terminal UI)

Perfect for:

- Watching build processes
- Monitoring log files
- Debugging file operations
- Understanding which files your applications touch

## Windows Troubleshooting

### "Windows cannot access the specified device, path or file" Error

This error commonly occurs with PyInstaller-compiled executables on Windows. Here are solutions:

#### 1. Windows Defender / Antivirus

- **Right-click** the executable → **Properties** → **Unblock** (if checkbox exists)
- Add the executable to your antivirus **whitelist/exclusions**
- Temporarily disable **Real-time protection** in Windows Defender to test

#### 2. Run as Administrator

- **Right-click** the executable → **Run as administrator**

#### 3. Alternative Download Methods

- Try downloading with a different browser
- Download to a different location (avoid Desktop/Downloads)
- Use `Ctrl+Shift+S` in browser to "Save As" instead of direct download

#### 4. PowerShell Execution Policy (for audio chimes)

If chime notifications don't work:

```powershell
# Run PowerShell as Administrator and execute:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 5. SmartScreen Filter

If Windows SmartScreen blocks execution:

- Click **"More info"** → **"Run anyway"**
- Or go to **Windows Security** → **App & browser control** → **Reputation-based protection** → Temporarily disable

#### 6. File Location

- Move the executable to a folder like `C:\Tools\` instead of Desktop/Downloads
- Avoid paths with spaces or special characters

### Still Having Issues?

1. Try running from **Command Prompt** or **PowerShell** to see error details
2. Check Windows Event Viewer for security-related blocks
3. Create an issue on GitHub with your specific error message
