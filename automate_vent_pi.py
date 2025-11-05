import sys
import time
import requests
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from collections import deque
import RPi.GPIO as GPIO
import dht11

# Setup logging
def setup_logging():
    """Setup logging with file rotation and console output"""
    # Create logger
    logger = logging.getLogger('vent_automation')
    logger.setLevel(logging.INFO)
    
    # Prevent adding multiple handlers if function is called multiple times
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation (10MB max, keep 5 files)
    file_handler = RotatingFileHandler(
        '/home/pi/vent_automation.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

# sys.path.append('vent-monitor-webapp')
# from utils.integration import WebAppDataLogger

class DHT11Sensor:
    """DHT11 temperature and humidity sensor reader using dht11 package"""
    
    def __init__(self, gpio_pin: int = 4):
        self.gpio_pin = gpio_pin
        self._temperature = None
        self._humidity = None
        self._last_reading = None
        self._read_interval = 2.0  # DHT11 minimum read interval is 1 second, use 2 for safety
        
        # Create DHT11 instance (GPIO initialization is handled by the dht11 package)
        self.dht11_instance = dht11.DHT11(pin=self.gpio_pin)
        
        logger.info(f"DHT11: Initialized on GPIO pin {self.gpio_pin}")
    
    def read(self) -> bool:
        """
        Read temperature and humidity from DHT11
        Returns True if successful, False otherwise
        """
        now = time.time()
        
        # Respect minimum read interval
        if self._last_reading and (now - self._last_reading) < self._read_interval:
            return self._temperature is not None
        
        # Try reading up to 3 times
        for attempt in range(3):
            try:
                result = self.dht11_instance.read()
                
                if result.is_valid():
                    # Validate readings are reasonable
                    if 0 <= result.humidity <= 100 and -40 <= result.temperature <= 80:
                        self._temperature = result.temperature  # Already in Celsius
                        self._humidity = result.humidity
                        self._last_reading = now
                        return True
                    else:
                        logger.warning(f"DHT11: Invalid readings - temp: {result.temperature}°C, humidity: {result.humidity}%")
                else:
                    logger.warning(f"DHT11: Read error code: {result.error_code}")
                
            except Exception as e:
                logger.error(f"DHT11: Exception during read: {e}")
            
            time.sleep(0.5)  # Delay between attempts
        
        logger.error("DHT11: Failed to get valid reading after 3 attempts")
        return False
    
    @property
    def temperature_c(self) -> Optional[float]:
        """Get temperature in Celsius"""
        return self._temperature
    
    @property
    def temperature_f(self) -> Optional[float]:
        """Get temperature in Fahrenheit"""
        if self._temperature is not None:
            return self._temperature * 9.0 / 5.0 + 32.0
        return None
    
    @property
    def humidity(self) -> Optional[float]:
        """Get humidity percentage"""
        return self._humidity
    
    @property
    def is_data_available(self) -> bool:
        """Check if valid data is available"""
        return self._temperature is not None and self._humidity is not None

class PurpleAirSensor:
    def __init__(self, base_url: str = "http://192.168.4.4"):
        """
        Initialize PurpleAir sensor reader
        
        Args:
            base_url: Base URL of the PurpleAir sensor
        """
        self.base_url = base_url.rstrip('/')
        self._data: Dict[str, Any] = {}
        self._last_update: Optional[datetime] = None
    
    def update(self, timeout: int = 10) -> bool:
        """
        Fetch latest data from the sensor
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/json?live=true"
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            self._data = response.json()
            self._last_update = datetime.now()
            return True
            
        except requests.RequestException as e:
            logger.error(f"PurpleAir: Error fetching data: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"PurpleAir: Error parsing JSON: {e}")
            return False
    
    def is_data_available(self) -> bool:
        """Check if data has been fetched"""
        return bool(self._data)
    
    @property
    def last_update(self) -> Optional[datetime]:
        """Get timestamp of last successful update"""
        return self._last_update
    
    # Device Information
    @property
    def sensor_id(self) -> str:
        return self._data.get("SensorId", "")
    
    @property
    def device_datetime(self) -> str:
        return self._data.get("DateTime", "")
    
    @property
    def geo_location(self) -> str:
        return self._data.get("Geo", "")
    
    @property
    def device_id(self) -> int:
        return self._data.get("Id", 0)
    
    @property
    def latitude(self) -> float:
        return self._data.get("lat", 0.0)
    
    @property
    def longitude(self) -> float:
        return self._data.get("lon", 0.0)
    
    @property
    def place(self) -> str:
        return self._data.get("place", "")
    
    @property
    def version(self) -> str:
        return self._data.get("version", "")
    
    @property
    def hardware_version(self) -> str:
        return self._data.get("hardwareversion", "")
    
    @property
    def hardware_discovered(self) -> str:
        return self._data.get("hardwarediscovered", "")
    
    # System Status
    @property
    def memory(self) -> int:
        return self._data.get("Mem", 0)
    
    @property
    def memory_fragmentation(self) -> int:
        return self._data.get("memfrag", 0)
    
    @property
    def memory_free_block(self) -> int:
        return self._data.get("memfb", 0)
    
    @property
    def memory_cs(self) -> int:
        return self._data.get("memcs", 0)
    
    @property
    def uptime(self) -> int:
        return self._data.get("uptime", 0)
    
    @property
    def adc_voltage(self) -> float:
        return self._data.get("Adc", 0.0)
    
    @property
    def logging_rate(self) -> int:
        return self._data.get("loggingrate", 0)
    
    @property
    def period(self) -> int:
        return self._data.get("period", 0)
    
    # Network Status
    @property
    def rssi(self) -> int:
        return self._data.get("rssi", 0)
    
    @property
    def wifi_state(self) -> str:
        return self._data.get("wlstate", "")
    
    @property
    def ssid(self) -> str:
        return self._data.get("ssid", "")
    
    @property
    def http_success(self) -> int:
        return self._data.get("httpsuccess", 0)
    
    @property
    def http_sends(self) -> int:
        return self._data.get("httpsends", 0)
    
    @property
    def pa_latency(self) -> int:
        return self._data.get("pa_latency", 0)
    
    # Environmental Data
    @property
    def temperature_f(self) -> float:
        return self._data.get("current_temp_f", 0.0)
    
    @property
    def humidity(self) -> float:
        return self._data.get("current_humidity", 0.0)
    
    @property
    def dewpoint_f(self) -> float:
        return self._data.get("current_dewpoint_f", 0.0)
    
    @property
    def pressure(self) -> float:
        return self._data.get("pressure", 0.0)
    
    @property
    def temperature_f_680(self) -> float:
        return self._data.get("current_temp_f_680", 0.0)
    
    @property
    def humidity_680(self) -> float:
        return self._data.get("current_humidity_680", 0.0)
    
    @property
    def dewpoint_f_680(self) -> float:
        return self._data.get("current_dewpoint_f_680", 0.0)
    
    @property
    def pressure_680(self) -> float:
        return self._data.get("pressure_680", 0.0)
    
    @property
    def gas_680(self) -> float:
        return self._data.get("gas_680", 0.0)
    
    # PM Data - Channel A
    @property
    def pm25_aqi(self) -> int:
        return self._data.get("pm2.5_aqi", 0)
    
    @property
    def pm25_aqic(self) -> str:
        return self._data.get("p25aqic", "")
    
    @property
    def pm1_0_cf_1(self) -> float:
        return self._data.get("pm1_0_cf_1", 0.0)
    
    @property
    def pm2_5_cf_1(self) -> float:
        return self._data.get("pm2_5_cf_1", 0.0)
    
    @property
    def pm10_0_cf_1(self) -> float:
        return self._data.get("pm10_0_cf_1", 0.0)
    
    @property
    def pm1_0_atm(self) -> float:
        return self._data.get("pm1_0_atm", 0.0)
    
    @property
    def pm2_5_atm(self) -> float:
        return self._data.get("pm2_5_atm", 0.0)
    
    @property
    def pm10_0_atm(self) -> float:
        return self._data.get("pm10_0_atm", 0.0)
    
    # Particle Count Data - Channel A
    @property
    def particles_0_3_um(self) -> float:
        return self._data.get("p_0_3_um", 0.0)
    
    @property
    def particles_0_5_um(self) -> float:
        return self._data.get("p_0_5_um", 0.0)
    
    @property
    def particles_1_0_um(self) -> float:
        return self._data.get("p_1_0_um", 0.0)
    
    @property
    def particles_2_5_um(self) -> float:
        return self._data.get("p_2_5_um", 0.0)
    
    @property
    def particles_5_0_um(self) -> float:
        return self._data.get("p_5_0_um", 0.0)
    
    @property
    def particles_10_0_um(self) -> float:
        return self._data.get("p_10_0_um", 0.0)
    
    # PM Data - Channel B
    @property
    def pm25_aqi_b(self) -> int:
        return self._data.get("pm2.5_aqi_b", 0)
    
    @property
    def pm25_aqic_b(self) -> str:
        return self._data.get("p25aqic_b", "")
    
    @property
    def pm1_0_cf_1_b(self) -> float:
        return self._data.get("pm1_0_cf_1_b", 0.0)
    
    @property
    def pm2_5_cf_1_b(self) -> float:
        return self._data.get("pm2_5_cf_1_b", 0.0)
    
    @property
    def pm10_0_cf_1_b(self) -> float:
        return self._data.get("pm10_0_cf_1_b", 0.0)
    
    @property
    def pm1_0_atm_b(self) -> float:
        return self._data.get("pm1_0_atm_b", 0.0)
    
    @property
    def pm2_5_atm_b(self) -> float:
        return self._data.get("pm2_5_atm_b", 0.0)
    
    @property
    def pm10_0_atm_b(self) -> float:
        return self._data.get("pm10_0_atm_b", 0.0)
    
    # Particle Count Data - Channel B
    @property
    def particles_0_3_um_b(self) -> float:
        return self._data.get("p_0_3_um_b", 0.0)
    
    @property
    def particles_0_5_um_b(self) -> float:
        return self._data.get("p_0_5_um_b", 0.0)
    
    @property
    def particles_1_0_um_b(self) -> float:
        return self._data.get("p_1_0_um_b", 0.0)
    
    @property
    def particles_2_5_um_b(self) -> float:
        return self._data.get("p_2_5_um_b", 0.0)
    
    @property
    def particles_5_0_um_b(self) -> float:
        return self._data.get("p_5_0_um_b", 0.0)
    
    @property
    def particles_10_0_um_b(self) -> float:
        return self._data.get("p_10_0_um_b", 0.0)
    
    # Status Flags
    @property
    def status_0(self) -> int:
        return self._data.get("status_0", 0)
    
    @property
    def status_1(self) -> int:
        return self._data.get("status_1", 0)
    
    @property
    def status_2(self) -> int:
        return self._data.get("status_2", 0)
    
    @property
    def status_3(self) -> int:
        return self._data.get("status_3", 0)
    
    @property
    def status_4(self) -> int:
        return self._data.get("status_4", 0)
    
    def get_raw_data(self) -> Dict[str, Any]:
        """Get the raw JSON data"""
        return self._data.copy()
    
    def __str__(self) -> str:
        return f"PurpleAir Sensor {self.sensor_id} - Temp: {self.temperature_f}°F, Humidity: {self.humidity}%, PM2.5 AQI: {self.pm25_aqi}"

class GPIOController:
    def __init__(self):
        """Initialize GPIO using RPi.GPIO"""
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        self.pins = {}  # Track pin states
        logger.info("GPIO Controller: Initialized using RPi.GPIO")
    
    def setup_pin(self, pin, mode='output'):
        """
        Setup GPIO pin mode
        pin: GPIO pin number
        mode: 'output' or 'input'
        """
        if mode.lower() == 'output':
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)  # Initialize to LOW
            self.pins[pin] = 0
        elif mode.lower() == 'input':
            GPIO.setup(pin, GPIO.IN)
            self.pins[pin] = GPIO.input(pin)
        else:
            raise ValueError("Mode must be 'output' or 'input'")
        
        logger.info(f"GPIO {pin} setup as {mode}")
    
    def turn_on(self, pin):
        """Turn on GPIO pin (set to HIGH/1)"""
        GPIO.output(pin, GPIO.HIGH)
        self.pins[pin] = 1
        logger.info(f"GPIO {pin} turned ON")
    
    def turn_off(self, pin):
        """Turn off GPIO pin (set to LOW/0)"""
        GPIO.output(pin, GPIO.LOW)
        self.pins[pin] = 0
        logger.info(f"GPIO {pin} turned OFF")
    
    def toggle(self, pin):
        """Toggle GPIO pin state"""
        current_state = self.pins.get(pin, 0)
        new_state = 1 - current_state
        if new_state:
            GPIO.output(pin, GPIO.HIGH)
        else:
            GPIO.output(pin, GPIO.LOW)
        self.pins[pin] = new_state
        logger.info(f"GPIO {pin} toggled to {'ON' if new_state else 'OFF'}")
        return new_state
    
    def read_pin(self, pin):
        """Read current state of GPIO pin"""
        if pin in self.pins:
            # For output pins, return our tracked state
            # For input pins, read actual state
            try:
                actual_state = GPIO.input(pin)
                self.pins[pin] = actual_state
                return actual_state
            except:
                return self.pins.get(pin, 0)
        return 0
    
    def cleanup(self):
        """Clean up GPIO resources"""
        GPIO.cleanup()
        logger.info("GPIO Controller: Cleanup complete")

class DehumidifyVentController:
    def __init__(self, gpio_controller: GPIOController, vent_pin: int, dehum_pin: int):
        """
        Initialize Dehumidifier and Vent Controller
        
        Args:
            gpio_controller: Instance of GPIOController
            vent_pin: GPIO pin number for vent control
            dehum_pin: GPIO pin number for dehumidifier control
        """
        self.gpio = gpio_controller
        self.vent_pin = vent_pin
        self.dehum_pin = dehum_pin
        
        # Setup pins
        self.gpio.setup_pin(self.vent_pin, 'output')
        self.gpio.setup_pin(self.dehum_pin, 'output')
    
    def activate_vent(self):
        """Activate the vent"""
        logger.info("Activating vent")
        self.gpio.turn_on(self.vent_pin)
    
    def deactivate_vent(self):
        """Deactivate the vent"""
        logger.info("Deactivating vent")
        self.gpio.turn_off(self.vent_pin)
    
    def activate_dehumidifier(self):
        """Activate the dehumidifier"""
        logger.info("Activating dehumidifier")
        self.gpio.turn_on(self.dehum_pin)
    
    def deactivate_dehumidifier(self):
        """Deactivate the dehumidifier"""
        logger.info("Deactivating dehumidifier")
        self.gpio.turn_off(self.dehum_pin)
        
    def get_vent_state(self) -> bool:
        """Get current vent state"""
        return bool(self.gpio.read_pin(self.vent_pin))
    
    def get_dehumidifier_state(self) -> bool:
        """Get current dehumidifier state"""
        return bool(self.gpio.read_pin(self.dehum_pin))
        
class VentDehumidifyStateMachine:
    """
    State machine that periodically reads the PurpleAir sensor, smooths readings,
    and controls the vent and dehumidifier according to the desired logic.
    Call update() repeatedly (e.g. from a loop or scheduler).
    """

    def __init__(
        self,
        controller: DehumidifyVentController,
        aqi: PurpleAirSensor,
        indoor_sensor: DHT11Sensor,
        aqi_threshold: int = 50,
        ideal_humidity: float = 35.0,
        ideal_temperature_f: float = 72.0,
        max_outdoor_humidity: float = 85.0,
        vent_with_dehum_humidity_threshold: float = 60.0,
        min_outdoor_temp_f: float = 0.0,
        max_outdoor_temp_f: float = 90.0,
        smoothing_samples: int = 5,
        min_change_interval_s: int = 60,
        limited_on_s: int = 10 * 60,   # 10 minutes
        limited_off_s: int = 50 * 60,  # 50 minutes
        quick_vent_s: int = 5 * 60,    # 5 minutes for hot outdoor air
    ):
        self.controller = controller
        self.aqi = aqi
        self.indoor_sensor = indoor_sensor

        self.AQI_THRESHOLD = aqi_threshold
        self.IDEAL_HUMIDITY = ideal_humidity
        self.IDEAL_TEMPERATURE_F = ideal_temperature_f
        self.MAX_OUTDOOR_HUMIDITY = max_outdoor_humidity
        self.MIN_OUTDOOR_TEMPERATURE_F = min_outdoor_temp_f
        self.MAX_OUTDOOR_TEMPERATURE_F = max_outdoor_temp_f
        self.VENT_WITH_DEHUM_HUMIDITY_THRESH = vent_with_dehum_humidity_threshold

        self.smoothing_samples = smoothing_samples
        self.min_change_interval_s = min_change_interval_s

        self.limited_on_s = limited_on_s
        self.limited_off_s = limited_off_s
        self.limited_cycle_len = self.limited_on_s + self.limited_off_s
        
        self.quick_vent_s = quick_vent_s

        # smoothing buffers
        self._temp_hist = deque(maxlen=self.smoothing_samples)
        self._hum_hist = deque(maxlen=self.smoothing_samples)
        self._aqi_hist = deque(maxlen=self.smoothing_samples)
        
        # indoor sensor smoothing buffers
        self._indoor_temp_hist = deque(maxlen=self.smoothing_samples)
        self._indoor_hum_hist = deque(maxlen=self.smoothing_samples)

        # state tracking
        self._last_vent_change: Optional[datetime] = None
        self._last_dehum_change: Optional[datetime] = None
        self._limited_cycle_start: Optional[datetime] = None
        self._limited_mode = False
        self._quick_vent_start: Optional[datetime] = None
        self._quick_vent_mode = False

    def _now(self) -> datetime:
        return datetime.now()

    def _avg(self, d: deque) -> float:
        if not d:
            return 0.0
        return sum(d) / len(d)

    def update(self, indoor_humidity: Optional[float] = None, indoor_temperature: Optional[float] = None) -> None:
        """
        Perform one state-machine update:
        - read and smooth sensor values
        - decide desired vent/dehum states
        - apply debouncing and limited venting cycle
        - command the controller
        """

        # Fetch latest outdoor data
        if not self.aqi.update():
            logger.error("VentSM: Failed to update AQI sensor data")
            return

        outdoor_aqi = float(self.aqi.pm25_aqi)
        outdoor_humidity = float(self.aqi.humidity)
        outdoor_temp = float(self.aqi.temperature_f)

        # Update smoothing buffers for outdoor data
        self._aqi_hist.append(outdoor_aqi)
        self._hum_hist.append(outdoor_humidity)
        self._temp_hist.append(outdoor_temp)

        avg_aqi = self._avg(self._aqi_hist)
        avg_outdoor_hum = self._avg(self._hum_hist)
        avg_outdoor_temp = self._avg(self._temp_hist)

        # Read indoor sensor data
        indoor_sensor_success = self.indoor_sensor.read()
        
        if indoor_sensor_success and self.indoor_sensor.is_data_available:
            # Use DHT11 sensor data
            dht_temp_f = self.indoor_sensor.temperature_f
            dht_humidity = self.indoor_sensor.humidity
            
            # Update indoor smoothing buffers
            self._indoor_temp_hist.append(dht_temp_f)
            self._indoor_hum_hist.append(dht_humidity)
            
            # Use smoothed indoor values
            indoor_temperature = self._avg(self._indoor_temp_hist)
            indoor_humidity = self._avg(self._indoor_hum_hist)
            
            logger.info(f"VentSM: DHT11 - temp: {dht_temp_f:.1f}°F, humidity: {dht_humidity:.1f}%")
        else:
            # Fall back to last known values if available, otherwise use provided values or defaults
            if len(self._indoor_temp_hist) > 0 and len(self._indoor_hum_hist) > 0:
                # Use last smoothed values from previous successful readings
                indoor_temperature = self._avg(self._indoor_temp_hist)
                indoor_humidity = self._avg(self._indoor_hum_hist)
                logger.info(f"VentSM: Using last known DHT11 values - temp: {indoor_temperature:.1f}°F, humidity: {indoor_humidity:.1f}%")
            else:
                # Fall back to provided values or defaults if no previous readings available
                if indoor_humidity is None:
                    indoor_humidity = 40.0  # Default fallback
                if indoor_temperature is None:
                    indoor_temperature = 70.0  # Default fallback
                logger.warning("VentSM: Using fallback indoor values (DHT11 read failed, no previous readings)")

        logger.info(f"VentSM: avg AQI={avg_aqi:.1f}, out hum={avg_outdoor_hum:.1f}%, out temp={avg_outdoor_temp:.1f}°F | indoor hum={indoor_humidity:.1f}%, indoor temp={indoor_temperature:.1f}°F")

        # Evaluate conditions
        temp_in_range = (self.MIN_OUTDOOR_TEMPERATURE_F <= avg_outdoor_temp <= self.MAX_OUTDOOR_TEMPERATURE_F)
        temp_would_bring_closer = abs(avg_outdoor_temp - self.IDEAL_TEMPERATURE_F) < abs(indoor_temperature - self.IDEAL_TEMPERATURE_F)
        outdoor_cooler_than_ideal = avg_outdoor_temp < self.IDEAL_TEMPERATURE_F
        outdoor_too_cold = avg_outdoor_temp < (self.IDEAL_TEMPERATURE_F - 15)
        indoor_warmer_than_ideal = indoor_temperature > self.IDEAL_TEMPERATURE_F
        outdoor_hotter_than_ideal = avg_outdoor_temp > self.IDEAL_TEMPERATURE_F

        # Baseline decisions
        desired_vent = False
        desired_dehum = False

        # AQI safety check: always keep vent closed when outside AQI is poor
        if avg_aqi > self.AQI_THRESHOLD:
            desired_vent = False
            logger.info("VentSM: AQI above threshold -> vent forced CLOSED")
        else:
            # Only consider venting if temperature in allowed range
            if not temp_in_range:
                desired_vent = False
                logger.info("VentSM: Outdoor temp outside allowed range -> vent CLOSED")
            # Only consider venting if humidity is below max
            elif avg_outdoor_hum > self.MAX_OUTDOOR_HUMIDITY: # could be raining, don't vent!
                desired_vent = False
                logger.info("VentSM: Outdoor humidity above max -> vent CLOSED")
            else:
                # Clear any existing cycling modes when conditions change
                if temp_would_bring_closer:
                    self._limited_mode = False
                    self._limited_cycle_start = None
                    self._quick_vent_mode = False
                    self._quick_vent_start = None

                if temp_would_bring_closer:
                    # Outdoor temp would help reach ideal -> allow venting
                    desired_vent = True
                    logger.info("VentSM: Outdoor temp would bring us closer -> vent OPEN")
                elif (outdoor_hotter_than_ideal or outdoor_too_cold) and temp_in_range:
                    # Hot outdoor air OR outdoor air much cooler than ideal -> quick vent cycle for air exchange
                    self._quick_vent_mode = True
                    if self._quick_vent_start is None:
                        self._quick_vent_start = self._now()
                        logger.info("VentSM: Entering quick vent mode for hot/cold outdoor air")
                    
                    elapsed = (self._now() - self._quick_vent_start).total_seconds()
                    quick_cycle_len = 60 * 60  # 60 minutes total cycle
                    phase = elapsed % quick_cycle_len
                    
                    if phase < self.quick_vent_s:
                        desired_vent = True
                        logger.info("VentSM: Quick vent -> ON phase")
                        logger.debug(f"VentSM: Quick vent ON phase progress: {phase / self.quick_vent_s * 100:.1f}%")
                    else:
                        desired_vent = False
                        logger.info("VentSM: Quick vent -> OFF phase")
                        off_phase_elapsed = phase - self.quick_vent_s
                        off_phase_duration = quick_cycle_len - self.quick_vent_s  # 55 minutes
                        logger.debug(f"VentSM: Quick vent OFF phase progress: {off_phase_elapsed / off_phase_duration * 100:.1f}%")
                else: # temp in reasonable range but doesn't help reach ideal
                    # Temperature neutral -> limited venting
                    self._limited_mode = True
                    if self._limited_cycle_start is None:
                        self._limited_cycle_start = self._now()
                        logger.info("VentSM: Entering limited venting mode; starting cycle")
                    
                    elapsed = (self._now() - self._limited_cycle_start).total_seconds()
                    phase = elapsed % self.limited_cycle_len
                    if phase < self.limited_on_s:
                        desired_vent = True
                        logger.info("VentSM: Limited cycle -> ON phase")
                        logger.debug(f"VentSM: Limited cycle phase time: {phase:.1f}s")
                        logger.debug(f"VentSM: Limited cycle ON phase progress: {phase / self.limited_on_s * 100:.1f}%")
                    else:
                        desired_vent = False
                        logger.info("VentSM: Limited cycle -> OFF phase")
                        logger.debug(f"VentSM: Limited cycle phase time: {phase:.1f}s")
                        off_phase_elapsed = phase - self.limited_on_s
                        logger.debug(f"VentSM: Limited cycle OFF phase progress: {off_phase_elapsed / self.limited_off_s * 100:.1f}%")

        # Venting condition has been determined, now determine dehumidification state
        if indoor_humidity > self.IDEAL_HUMIDITY and indoor_humidity > 50: # don't even consider dehum if humidity isn't above 50%
            if (outdoor_cooler_than_ideal):
                # It's colder & more humid outside 
                if desired_vent: # We are venting in cooler more humid air
                    if temp_would_bring_closer and indoor_warmer_than_ideal: # It's warmer than ideal inside already
                        desired_dehum = False
                        logger.info("VentSM: High humidity but prefer venting (outdoor cooler or indoor warm) -> vent ON, dehumidifier OFF")
                    else:
                        # It won't hurt to dehumidify as the warmer dehumidified air will heat up indoor temperature
                        desired_dehum = True
                        logger.info("VentSM: High humidity and venting cooler humid air -> vent ON with dehumidifier ON")
            elif (indoor_warmer_than_ideal):
                # It's warmer & less humid outside
                if desired_vent: # We are venting in warmer drier air
                    desired_dehum = False
                    logger.info("VentSM: High humidity but prefer venting (outdoor warmer and drier) -> vent ON, dehumidifier OFF")
                elif indoor_humidity > 60:
                    desired_dehum = True
                    logger.info("VentSM: High humidity and not venting -> vent CLOSED with dehumidifier ON")
                else:
                    desired_dehum = False
                    logger.info("VentSM: High humidity but prioritize not heating above ideal indoor temperature -> vent OFF, dehumidifier OFF")
        else:
            logger.info("VentSM: Indoor humidity within ideal range -> dehumidifier OFF")
            desired_dehum = False

        # Debounce / rate limit state changes
        now = self._now()
        current_vent_state = self.controller.get_vent_state()
        current_dehum_state = self.controller.get_dehumidifier_state()

        # Vent control (closing for AQI exceed should be immediate)
        if avg_aqi > self.AQI_THRESHOLD and current_vent_state:
            self.controller.deactivate_vent()
            self._last_vent_change = now
        elif desired_vent != current_vent_state:
            if self._last_vent_change is None or (now - self._last_vent_change).total_seconds() >= self.min_change_interval_s:
                if desired_vent:
                    self.controller.activate_vent()
                else:
                    self.controller.deactivate_vent()
                self._last_vent_change = now
            else:
                logger.debug("VentSM: Vent change suppressed by debounce timer")

        # Dehumidifier control
        if desired_dehum != current_dehum_state:
            if self._last_dehum_change is None or (now - self._last_dehum_change).total_seconds() >= self.min_change_interval_s:
                if desired_dehum:
                    self.controller.activate_dehumidifier()
                else:
                    self.controller.deactivate_dehumidifier()
                self._last_dehum_change = now
            else:
                logger.debug("VentSM: Dehumidifier change suppressed by debounce timer")
    
# Example usage
if __name__ == "__main__":
    logger.info("Starting Vent Automation System")
    
    sensor = PurpleAirSensor()
    if sensor.update():
        logger.info(f"Initial PurpleAir reading - AQI: {sensor.pm25_aqi}, Temperature: {sensor.temperature_f}°F")
    else:
        logger.error("Failed to get initial PurpleAir reading")
    
    try:
        # Create GPIO controller instance
        gpio = GPIOController()
        
        # Create DHT11 sensor (using GPIO4 with dht11 package)
        dht11_sensor = DHT11Sensor(gpio_pin=4)
        
        # Test DHT11 sensor
        if dht11_sensor.read():
            logger.info(f"Initial DHT11 reading - Temperature: {dht11_sensor.temperature_f:.1f}°F, Humidity: {dht11_sensor.humidity:.1f}%")
        else:
            logger.warning("DHT11 - Failed to get initial reading")
        
        # Create Dehumidifier and Vent Controller
        controller = DehumidifyVentController(gpio, vent_pin=5, dehum_pin=22)
        
        # Create and run state machine with DHT11 sensor
        state_machine = VentDehumidifyStateMachine(controller, sensor, dht11_sensor)
        
        logger.info("Vent automation system initialized successfully, starting main loop")
        
        while True:
            state_machine.update()
            time.sleep(30)  # Update every 30 seconds
    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down gracefully")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        # Always cleanup
        if 'gpio' in locals():
            gpio.cleanup()
        logger.info("Vent automation system shutdown complete")