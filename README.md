# 🌬️ Smart Home Vent Automation System

An intelligent Raspberry Pi-based system that automatically controls ventilation and dehumidification based on real-time indoor/outdoor environmental conditions and air quality data.

## 🏡 Background

I work from home out of my basement. Upon testing for radon, it was discovered that radon levels were much higher than recommended. In addition to radon mitigation fans, I installed a ventilating dehumidifier with an external air intake with the idea that increasing positive air pressure would reduce the radon drawn from the ground. This worked to reduce radon to safe levels. This came with the additional benefit of dehumidifying the basement when needed and providing fresh quality air to my home office keeping me refreshed while working.

However, I soon realized that poor air quality (due to wildfire smoke, etc.) severely impacts comfort even though the unit contains a MERV 8 filter. Turns out pumping smoke filled air into your house is not a good idea! There were other QOL issues that caused me to be constantly adjusting the vent duty cycle, disabling dehumidification, etc. (dehumidification increases my office temperature to uncomfortable levels on warm days).

I developed this automation script and accompanying hardware to run my ventilation and dehumidification how I prefer!

## 🎯 What Does It Do?

This system continuously monitors:

- **Outdoor conditions**: Air quality (AQI), temperature, and humidity via PurpleAir sensor
- **Indoor conditions**: Temperature and humidity via DHT11 sensor

Then intelligently controls:

- **Ventilation fan**: Opens/closes based on temperature differentials and air quality
- **Dehumidifier**: Activates when indoor humidity is too high

## ✨ Key Features

- 🛡️ **AQI Protection**: Automatically closes vents when outdoor air quality is poor
- 🌡️ **Smart Temperature Control**: Only vents when outdoor air helps reach ideal temperature
- 💧 **Humidity Management**: Prevents over-humidification and mold growth
- 🔄 **Cycling Modes**:
  - Limited venting (10 min on / 50 min off) for air exchange
  - Quick venting (5 min on / 55 min off) for extreme temperatures
- 📊 **Data Smoothing**: Moving averages prevent erratic behavior
- ⏱️ **Debouncing**: Prevents rapid on/off cycling
- 📝 **Comprehensive Logging**: Rotating log files with detailed system status
- 🏠 **Home Assistant Integration**: MQTT discovery for easy monitoring

## 🛠️ Hardware Requirements

### Core Components

- **Raspberry Pi** (Zero 2W)
- **MicroSD Card**
- **PurpleAir Sensor** (FLEX - for outdoor air quality monitoring)
- **DHT11 Temperature/Humidity Sensor** (for indoor monitoring)

### Control Hardware

- **2x Relay HAT** (for controlling vent fan and dehumidifier)
- **Ventilating Dehumidifier** (AprilAire 8192)
- **Powered Damper** (Suncourt ZoneMaster 6-Inch)

### Wiring Components

- **Jumper wires** (female-to-female and male-to-female)
- **Breadboard** or **perfboard** (optional, for cleaner connections)
- **Power supply** for Raspberry Pi (5V 3A recommended)

## 🔌 Wiring Diagram

```txt
DHT11 Sensor:
├── VCC → Pi Pin 2 (5V)
├── GND → Pi Pin 6 (Ground)
└── Data → Pi Pin 7 (GPIO 4)

Relay Module 1 (Vent):
├── VCC → Pi Pin 4 (5V)
├── GND → Pi Pin 9 (Ground)
└── IN → Pi Pin 29 (GPIO 5)

Relay Module 2 (Dehumidifier):
├── VCC → Pi Pin 4 (5V)
├── GND → Pi Pin 14 (Ground)
└── IN → Pi Pin 15 (GPIO 22)
```

TBD: Schematic to interface with Aprilaire coming soon!

## 📦 Software Installation

### 1. Prepare Raspberry Pi

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
sudo apt install python3-pip python3-venv git -y
```

### 2. Clone and Setup Project

```bash
# Clone the repository
cd /home/pi
git clone https://github.com/yourusername/vent-automation.git
cd vent-automation

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install RPi.GPIO requests dht11
```

### 3. Configure Settings

Edit the script to match your setup:

```python
# In automate_vent_pi.py, modify these settings:
sensor = PurpleAirSensor("http://192.168.1.100")  # Your PurpleAir IP
dht11_sensor = DHT11Sensor(gpio_pin=4)            # DHT11 GPIO pin
controller = DehumidifyVentController(gpio, vent_pin=5, dehum_pin=22)  # Relay pins

# Adjust thresholds as needed:
state_machine = VentDehumidifyStateMachine(
    controller, sensor, dht11_sensor,
    aqi_threshold=50,           # Close vents above this AQI
    ideal_humidity=35.0,        # Target humidity %
    ideal_temperature_f=72.0,   # Target temperature °F
    max_outdoor_humidity=85.0,  # Don't vent if outdoor humidity above this
    min_outdoor_temp_f=32.0,    # Minimum vent outdoor temperature
    max_outdoor_temp_f=95.0     # Maximum vent outdoor temperature
)
```

## 🚀 Running the System

### Manual Start (for testing)

```bash
cd /home/pi/vent-automation
source venv/bin/activate
python automate_vent_pi.py
```

### Automatic Start on Boot (Recommended)

Create a systemd service:

```bash
sudo nano /etc/systemd/system/vent-automation.service
```

Add this content:

```ini
[Unit]
Description=Vent Automation Controller
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi
Environment=PATH=/home/pi/.venv/bin
ExecStart=/home/pi/.venv/bin/python /home/pi/automate_vent_pi.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable vent-automation.service
sudo systemctl start vent-automation.service

# Check status
sudo systemctl status vent-automation.service

# View logs
sudo journalctl -u vent-automation.service -f
```

## 📊 Monitoring and Logs

### Log Files

The system creates rotating log files at `/home/pi/vent_automation.log`:

- **Max size**: 10MB per file
- **Retention**: 5 backup files (50MB total)
- **Format**: Timestamped entries with detailed status information

### View Logs

```bash
# Real-time log monitoring
tail -f /home/pi/vent_automation.log

# Search for errors
grep "ERROR" /home/pi/vent_automation.log

# View recent activity
tail -100 /home/pi/vent_automation.log
```

### System Management

```bash
# Start/stop/restart service
sudo systemctl start vent-automation.service
sudo systemctl stop vent-automation.service
sudo systemctl restart vent-automation.service

# Check if running
sudo systemctl is-active vent-automation.service
```

## 🏠 Home Assistant Integration (Future)

The system supports MQTT discovery for seamless Home Assistant integration:

1. **Install MQTT broker** (Mosquitto recommended)
2. **Add MQTT integration** to your `configuration.yaml`:

   ```yaml
   mqtt:
     broker: localhost
     discovery: true
   ```

3. **Entities automatically appear** in Home Assistant:
   - Indoor/outdoor temperature and humidity sensors
   - AQI sensor
   - Vent and dehumidifier status
   - System operating mode
   - Last update timestamp

## ⚙️ How It Works

### Decision Logic

The system uses a sophisticated state machine with multiple operating modes:

1. **Safety First**: Always closes vents if outdoor AQI exceeds threshold
2. **Temperature Priority**: Vents freely when outdoor air helps reach ideal temperature
3. **Limited Cycling**: 10min on/50min off cycle for neutral temperature conditions
4. **Quick Cycling**: 5min on/55min off for extreme temperatures (air exchange only)
5. **Humidity Control**: Activates dehumidifier based on indoor conditions and vent status

### Smart Features

- **Data Smoothing**: Uses 5-sample moving averages to prevent noise-induced decisions
- **Debouncing**: 60-second minimum between state changes prevents rapid cycling
- **Fallback Logic**: Uses last known sensor values if DHT11 fails temporarily
- **Comprehensive Logging**: Every decision is logged with reasoning

## 🔧 Troubleshooting

### Common Issues

**DHT11 sensor not reading:**

- Check wiring connections
- Verify GPIO pin number in code
- DHT11 sensors can be unreliable - consider upgrading to DHT22

**PurpleAir sensor not responding:**

- Verify IP address is correct
- Check network connectivity
- Ensure PurpleAir is on same network

**Relays not switching:**

- Test with multimeter
- Verify relay module voltage requirements
- Check GPIO pin assignments

**Service won't start:**
```bash
# Check service status and logs
sudo systemctl status vent-automation.service
sudo journalctl -u vent-automation.service --no-pager
```

### Debug Mode

Enable debug logging by changing the log level:

```python
logger.setLevel(logging.DEBUG)
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for:

- Bug fixes
- Feature improvements
- Documentation updates
- Hardware compatibility additions

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Safety Notice

This system controls electrical devices. Please ensure:

- Proper electrical safety practices
- Appropriate fusing/circuit protection
- Professional installation for high-voltage connections
- Regular system monitoring and maintenance

---

**Happy Automating!** 🎉

*Built with ❤️ for the smart home community*
