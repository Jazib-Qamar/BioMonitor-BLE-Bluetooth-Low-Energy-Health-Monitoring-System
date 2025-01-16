import asyncio
from bleak import BleakScanner
from connect import send_device_setting_request, connect_to_device  # Import required functions

async def scan_ble_devices():
    print("Scanning for GTS devices...")

    devices = []

    def device_discovered(device, advertisement_data):
        if device.name and device.name.startswith("GTS"):
            rssi = advertisement_data.rssi
            print(f"Discovered device: {device.name} ({device.address}), RSSI: {rssi} dBm")
            devices.append(device)

    # Create a BleakScanner to detect devices
    scanner = BleakScanner(detection_callback=device_discovered)

    try:
        await scanner.start()
        await asyncio.sleep(20)  # Scan for 10 seconds
    except Exception as e:
        print(f"Error starting scanner: {str(e)}")
    finally:
        try:
            await scanner.stop()
            print("Scan completed.")
        except Exception as e:
            print(f"Error stopping scanner: {str(e)}")

    return devices

async def main():
    devices = await scan_ble_devices()

    if devices:
        target_device = devices[0]  # Choose the first discovered device for simplicity
        print(f"Found {len(devices)} GTS devices. Attempting to connect to {target_device.name}...")

        # Connect to the selected device
        client = await connect_to_device(target_device.address)

        if client:
            print(f"Successfully connected to {target_device.name}.")
            # Send device settings after a successful connection
            await send_device_setting_request(client)
        else:
            print("Could not connect to the device.")

