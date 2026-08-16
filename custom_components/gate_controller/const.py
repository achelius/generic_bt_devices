DOMAIN = "gate_controller"

# BLE service and characteristic UUIDs (from ESPHome esp32_ble_server config)
SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
CHAR_GATE_CONTROL = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
CHAR_WIFI_CONTROL = "6e400004-b5a3-f393-e0a9-e50e24dcca9e"  # write to control, read for status
CHAR_BATTERY = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
CHAR_REBOOT = "6e400006-b5a3-f393-e0a9-e50e24dcca9e"

# Default PIN matching the ESPHome globals initial_value
DEFAULT_PIN = "njkgfrniu33ogrelk32"
CONF_PIN = "pin"
