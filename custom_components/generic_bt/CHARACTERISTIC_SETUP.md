# Generic Bluetooth Integration - Characteristic Reader Setup

## Overview
This integration allows you to read Bluetooth Low Energy (BLE) characteristic values from Bluetooth devices. Each characteristic is configured as a sensor entity that reads its value from the device.

## Initial Setup

### 1. Add the Device
1. Go to **Settings → Devices & Services → Create Automation → Integrations**
2. Click **Create Integration** and search for "Generic Bluetooth"
3. Select your Bluetooth device from the discovered devices list
4. Click **Next**

### 2. Configure Your First Characteristic Reader
After selecting the device, you'll be prompted to configure a characteristic reader:

- **Characteristic Name**: The name for your sensor (e.g., "Temperature", "Battery Level")
- **Target UUID**: The UUID of the GATT characteristic you want to read
  - Format: Standard UUID format (e.g., `0000180a-0000-1000-8000-00805f9b34fb`)
  - Or simplified format: `180a` for 16-bit UUIDs

### 3. Complete Setup
After entering the characteristic details, click **Create**. The sensor will be created and will start reading the characteristic value.

## Adding More Characteristics

After initial setup, you can add more characteristic readers:

1. Go to **Settings → Devices & Services**
2. Find your device under "Generic Bluetooth"
3. Click on the device entry
4. Click **Options** or **Configure**
5. Enter the new characteristic name and UUID
6. Click **Save**

The new sensor will be added to your device.

## Finding Characteristic UUIDs

To find the UUID of a characteristic you want to read:

1. Use a BLE scanner app (e.g., "BLE Scanner" or "nRF Connect")
2. Connect to your device
3. Browse the services and characteristics
4. Note the UUID of the characteristic you want to read
5. Use that UUID in the configuration

## Characteristic Value Formats

- **Binary values** (bytes): Displayed as hexadecimal strings (e.g., `0a1b2c`)
- **Numeric values**: Displayed as-is
- **Text values**: Displayed as UTF-8 strings (if decodable)

## Example Configurations

### Temperature Sensor
- Name: `Room Temperature`
- UUID: `2a1c` (16-bit Environmental Sensing Service characteristic)

### Battery Level
- Name: `Battery Level`
- UUID: `2a19` (Battery Level characteristic)

### Custom Device
- Name: `Custom Sensor`
- UUID: `12345678-1234-5678-1234-567812345678`

## Troubleshooting

### Sensor shows "unavailable"
- Check that the device is powered on and in range
- Verify the characteristic UUID is correct
- Ensure the device supports the characteristic

### Cannot connect to device
- Move closer to the device
- Check that Bluetooth is enabled on your Home Assistant device
- Restart the Bluetooth adapter

### Wrong UUID format
- Use standard full UUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- Or 16-bit short format: `xxxx`
- Do not include curly braces

## Service and Entity Calls

Once configured, the sensor entity supports service calls through Home Assistant automation:

```yaml
service: generic_bt.read_gatt
target:
  entity_id: sensor.device_name_characteristic_name
data:
  target_uuid: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

service: generic_bt.write_gatt
target:
  entity_id: binary_sensor.device_name_state
data:
  target_uuid: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  data: "0a1b2c"
```
