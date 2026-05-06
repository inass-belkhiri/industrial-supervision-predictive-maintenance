# flow_sensor.py
# Reads flow rate from a YF-S201 Hall effect flow sensor connected to a GPIO pin.
# The sensor outputs a square wave pulse train.
# Frequency (Hz) = 7.5 * Flow Rate (L/min)

import time
import logging
import threading

try:
    import gpiozero
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    logging.warning("gpiozero not installed. Flow sensor will use default value.")

import config

log = logging.getLogger(__name__)

class FlowSensor:
    def __init__(self, pin, k_factor=7.5):
        self.pin = pin
        self.k_factor = k_factor
        self.pulse_count = 0
        self.lock = threading.Lock()
        self.sensor = None
        self.last_read_time = time.time()
        self._init_sensor()

    def _init_sensor(self):
        if not HAS_GPIO:
            log.warning("gpiozero not available, flow sensor disabled")
            return
        try:
            # Using DigitalInputDevice for pulse counting
            # bounce_time helps filter out noise
            self.sensor = gpiozero.DigitalInputDevice(self.pin, bounce_time=0.01)
            self.sensor.when_activated = self._pulse
            log.info(f"Flow sensor initialized on GPIO {self.pin}")
        except Exception as e:
            log.error(f"Failed to initialize flow sensor on GPIO {self.pin}: {e}")
            self.sensor = None

    def _pulse(self):
        with self.lock:
            self.pulse_count += 1

    def read_lpm(self) -> float:
        """
        Returns flow rate in Liters per minute.
        Resets the pulse counter after each read.
        """
        if not self.sensor:
            return config.FLOW_DEFAULT_LPM

        now = time.time()
        elapsed = now - self.last_read_time
        self.last_read_time = now

        with self.lock:
            pulses = self.pulse_count
            self.pulse_count = 0

        # Calculate frequency (pulses per second)
        if elapsed > 0:
            frequency = pulses / elapsed
        else:
            frequency = 0

        # YF-S201 formula: Frequency = 7.5 * Flow Rate (L/min)
        # Flow Rate = Frequency / 7.5
        flow_rate = frequency / self.k_factor

        # Sanity check: flow rate should be reasonable (0 to 30 L/min typically)
        if flow_rate > 30:
            log.warning(f"Flow rate spike detected: {flow_rate:.2f} L/min")
            flow_rate = config.FLOW_DEFAULT_LPM

        return flow_rate

    def close(self):
        if self.sensor:
            self.sensor.close()
            log.info("Flow sensor closed")
