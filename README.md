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
2. Double-click to run, or run from command prompt: `FSAR-windows.exe`

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

