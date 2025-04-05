#System Health Monitor – Flask Web App

A cross-platform Flask app to monitor system health and send email alerts when CPU, disk, or battery levels exceed custom thresholds.

#Features

- Real-time system monitoring:
  - CPU usage
  - Memory usage
  - Disk usage
  - Battery status
  - OS, hardware, and user info
- 📧 Email alerts when thresholds are breached
- 🌐 REST API at `/api/stats` returning system info in JSON
- 🖥️ Works on Windows, macOS, and Linux
 #Install Dependencies
pip install -r requirements.txt
 #Platform Notes
Windows: Make sure to install wmi
