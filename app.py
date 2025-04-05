from flask import Flask, jsonify, render_template 
from flask_cors import CORS
import psutil
import platform
import os
import subprocess
import smtplib
from email.mime.text import MIMEText

# Windows-specific library for fetching laptop info
try:
    import wmi
    w = wmi.WMI()
except ImportError:
    w = None  # If not on Windows, wmi won't work

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "your_email@gmail.com" 
EMAIL_PASSWORD = "your_app_password"  # Use an app password https://www.youtube.com/watch?v=MkLX85XU5rU&ab_channel=HarishBhathee
ALERT_THRESHOLD = {"cpu": 80, "disk": 90, "battery": 20}  # Set your threshold values

def send_alert(subject, message):
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS 
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, msg.as_string())
    except Exception as e:
        print(f"Failed to send email alert: {e}")

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

# Function to get system info
def get_system_info():
    system_info = {
        "os_name": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "architecture": platform.architecture()[0],
        "hostname": platform.node(),
        "username": os.getlogin(),
    }
    
    if platform.system() == "Windows":
        return get_windows_laptop_info(system_info)
    elif platform.system() == "Darwin":  # macOS
        return get_mac_laptop_info(system_info)
    elif platform.system() == "Linux":
        return get_linux_laptop_info(system_info)
    else:
        return system_info

# Windows laptop info
def get_windows_laptop_info(system_info):
    if not w:
        return {"error": "WMI not available on this system"}

    try:
        computer = w.Win32_ComputerSystem()[0]
        battery = w.Win32_Battery()[0] if w.Win32_Battery() else None
        laptop_info = {
            "manufacturer": computer.Manufacturer,
            "model": computer.Model,
            "battery_status": battery.BatteryStatus if battery else "No Battery",
            "battery_charge": battery.EstimatedChargeRemaining if battery else "N/A",
        }
    except Exception as e:
        laptop_info = {"error": f"WMI Error: {e}"}

    system_info["laptop_info"] = laptop_info
    return system_info

# macOS laptop info
def get_mac_laptop_info(system_info):
    try:
        model_info = subprocess.check_output("system_profiler SPHardwareDataType", shell=True, stderr=subprocess.DEVNULL).decode()
        manufacturer = "Apple"
        model = "Unknown"
        for line in model_info.splitlines():
            if "Model Identifier" in line:
                model = " ".join(line.strip().split(":")[1:]).strip()

        battery_info = subprocess.check_output("pmset -g batt", shell=True, stderr=subprocess.DEVNULL).decode().split("\n")[1]
        battery_status = "Charging" if "charging" in battery_info else "Not Charging"
        battery_charge = int(battery_info.split("\t")[1].split("%")[0])

        laptop_info = {
            "manufacturer": manufacturer,
            "model": model,
            "battery_status": battery_status,
            "battery_charge": battery_charge,
        }
    except Exception as e:
        laptop_info = {"error": f"macOS command failed: {e}"}

    system_info["laptop_info"] = laptop_info
    return system_info

# Linux laptop info
def get_linux_laptop_info(system_info):
    try:
        manufacturer = "Unknown"
        model = "Unknown"
        if subprocess.call("which dmidecode", shell=True, stdout=subprocess.DEVNULL) == 0:
            model_info = subprocess.check_output("dmidecode -t system", shell=True, stderr=subprocess.DEVNULL).decode()
            for line in model_info.splitlines():
                if "Manufacturer" in line:
                    manufacturer = line.split(":")[1].strip()
                if "Product Name" in line:
                    model = line.split(":")[1].strip()
        else:
            raise Exception("dmidecode not installed")
        battery_path = "/sys/class/power_supply/BAT0"
        if os.path.exists(battery_path):
            with open(os.path.join(battery_path, "capacity"), 'r') as f:
                battery_charge = f.read().strip()
            with open(os.path.join(battery_path, "status"), 'r') as f:
                battery_status = f.read().strip()
        else:
            battery_status = "No Battery"
            battery_charge = "N/A"

        laptop_info = {
            "manufacturer": manufacturer,
            "model": model,
            "battery_status": battery_status,
            "battery_charge": battery_charge,
        }
    except Exception as e:
        laptop_info = {"error": f"Linux command failed: {e}"}

    system_info["laptop_info"] = laptop_info
    return system_info

@app.route('/api/stats')
def get_stats():
    system_info = get_system_info()
    stats = {
        "cpu_usage": psutil.cpu_percent(interval=1),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "running_processes": len(psutil.pids())
    }
    
    alerts = []
    if stats["cpu_usage"] > ALERT_THRESHOLD["cpu"]:
        alerts.append("High CPU Usage Alert!")
    if stats["disk_usage"] > ALERT_THRESHOLD["disk"]:
        alerts.append("High Disk Usage Alert!")
    if "laptop_info" in system_info and "battery_charge" in system_info["laptop_info"]:
        try:
            battery_level = int(system_info["laptop_info"]["battery_charge"])
            if battery_level < ALERT_THRESHOLD["battery"]:
                alerts.append("Low Battery Alert!")
        except ValueError:
            pass

    if alerts:
        send_alert("System Alert", "\n".join(alerts))

    return jsonify({"system_info": system_info, "resource_stats": stats})

if __name__ == '__main__':
    app.run(debug=True)
