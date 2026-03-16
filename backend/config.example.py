# config.example.py

# ── MODBUS ──────────────────────────────────────────
MODBUS_PORT      = '/dev/ttyUSB0'
MODBUS_BAUDRATE  = 9600
MODBUS_PARITY    = 'N'
MODBUS_STOPBITS  = 1
MODBUS_BYTESIZE  = 8
MODBUS_TIMEOUT   = 1

SENSOR_MAP = {
    (1, 1): (1, 0),
    (1, 2): (2, 0),
    # ... ajoute tes capteurs
}

POSITION_MAP = {1: 'gauche', 2: 'centre', 3: 'droite'}
TEMP_SCALE_FACTOR = 0.1

# ── TEMPERATURE THRESHOLDS ───────────────────────────
T_HEATER        = 45.0
T_MOLD_CRITICAL = 42.0
T_TOLERANCE     = 3.0

# ── INFLUXDB ─────────────────────────────────────────
INFLUX_URL    = 'http://localhost:8086'
INFLUX_TOKEN  = 'YOUR_INFLUXDB_TOKEN_HERE'
INFLUX_ORG    = 'YOUR_ORG_HERE'
INFLUX_BUCKET = 'YOUR_BUCKET_HERE'

# ── TELEGRAM ─────────────────────────────────────────
TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'
TELEGRAM_CHAT_ID   = 'YOUR_CHAT_ID_HERE'

# ── LED STRIP ────────────────────────────────────────
LED_GPIO_PIN   = 18
LED_COUNT      = 30
LED_BRIGHTNESS = 128

# ── FLOW SENSOR ──────────────────────────────────────
FLOW_SENSOR_ENABLED  = False
FLOW_DEFAULT_LPM     = 16.5
FLOW_SENSOR_SLAVE    = 13
FLOW_SENSOR_REGISTER = 0

# ── GREY-BOX PHYSICAL PARAMETERS ─────────────────────
PIPE_DIAMETER   = 0.013
PIPE_LENGTH     = 3.0
LAMBDA_CALCAIRE = 1.0
N_MOLDS         = 12
RHO_WATER       = 1000.0
CP_WATER        = 4186.0

# ── ML ───────────────────────────────────────────────
FEATURE_WINDOW_SECONDS = 30
RIDGE_MIN_DAYS         = 7
BOOTSTRAP_N            = 1000
RETRAIN_HOUR           = 2

# ── WEBSOCKET ────────────────────────────────────────
WS_HOST = '0.0.0.0'
WS_PORT = 8000

# ── ACQUISITION ──────────────────────────────────────
ACQUISITION_HZ = 1