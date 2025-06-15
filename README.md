# Q&A Overlay System v1.1

A robust clipboard monitoring system with customizable overlay display for quick access to Q&A information.

## ✨ New in v1.1

- **🎨 Configuration GUI**: Customize colors, fonts, position, and more
- **🎯 Live Configuration Updates**: Changes apply instantly
- **✨ Animations**: Smooth fade in/out effects
- **⏱️ Auto-Hide**: Configurable timeout for overlay
- **📍 9 Position Options**: Place overlay anywhere on screen

## 📋 Features

- Real-time clipboard monitoring
- Transparent overlay display
- Fuzzy search matching
- Robust error handling
- Process monitoring with auto-restart
- Customizable appearance and behavior

## 🚀 Quick Start

### Prerequisites

```bash
# Install required packages
sudo apt-get install python3 python3-pip xclip
pip3 install PyQt5
```

### Installation

1. Clone or download all files to a directory
2. Make scripts executable:
   ```bash
   chmod +x start_qa_system.sh stop_qa_system.sh
   ```

### Usage

**Start the system**:
```bash
./start_qa_system.sh
```

**Start with configuration GUI**:
```bash
./start_qa_system.sh -c
```

**Configuration GUI only**:
```bash
./start_qa_system.sh -C
```

**Stop the system**:
```bash
./stop_qa_system.sh
```

## 📁 Files

- `qa_overlay.py` - Overlay display with configuration support
- `qa_finder.py` - Clipboard monitor and Q&A matcher
- `qa_config_gui.py` - Configuration interface
- `answare.json` - Q&A database
- `qa_config.json` - Configuration settings (auto-created)
- `start_qa_system.sh` - Start script with monitoring
- `stop_qa_system.sh` - Stop script

## 🎨 Configuration

### GUI Options

Access the configuration GUI to customize:

- **Position**: 9 screen positions
- **Size**: Width and height
- **Transparency**: 50-100%
- **Font**: Family, size, bold
- **Colors**: Text, outline, background
- **Auto-hide**: 0-120 seconds
- **Animations**: Enable/disable

### Manual Configuration

Edit `qa_config.json` directly:

```json
{
  "overlay": {
    "position": "right-middle",
    "width": 600,
    "transparency": 95
  },
  "text": {
    "font_size": 12,
    "text_color": "#FFFFFF"
  }
}
```

## 💡 How It Works

1. **Clipboard Monitoring**: `qa_finder.py` watches the clipboard
2. **Pattern Matching**: Searches `answare.json` for matching questions
3. **Socket Communication**: Sends results to overlay via localhost:12345
4. **Overlay Display**: Shows Q&A in customizable transparent window
5. **Auto Management**: Process monitoring ensures reliability

## 🛠️ Troubleshooting

### Common Issues

**Port already in use**:
```bash
# Find and kill process using port 12345
sudo lsof -i :12345
kill -9 <PID>
```

**Display not found**:
```bash
# Set display variable
export DISPLAY=:0
```

**Permission denied**:
```bash
# Make scripts executable
chmod +x *.sh *.py
```

### Logs

Check logs in the `logs/` directory for detailed information.

## 📊 Q&A Database Format

`answare.json` structure:

```json
[
  {
    "question": "Question text",
    "answer": "Single answer"
  },
  {
    "question": "Question text",
    "answers": ["Answer 1", "Answer 2"]
  }
]
```

## 🔧 Advanced Usage

### Custom Start Options

```bash
# Check system without starting
./start_qa_system.sh --help

# View live logs
tail -f logs/qa_system_*.log
```

### Process Management

The system includes:
- Automatic restart on failure (max 5 attempts)
- Health checks every 10 seconds
- Graceful shutdown handling
- PID file management

## 📄 License

This project is provided as-is for educational and personal use.

## 🤝 Contributing

Feel free to submit issues, fork, and create pull requests.