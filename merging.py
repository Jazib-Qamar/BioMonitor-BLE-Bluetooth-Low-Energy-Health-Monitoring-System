import asyncio
import subprocess
import threading
from flask import Flask, jsonify
from scan import scan_ble_devices  # BLE device scanning functionality
from connect import connect_to_device  # BLE device connection functionality

# The GATT characteristic UUIDs
WRITE_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9d"
NOTIFY_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9d"

# Flask app for serving the FBD MAC address
app = Flask(__name__)

# Variable to store the FBD MAC address
fbd_mac_address = None

# API endpoint to get the FBD MAC address
@app.route('/api/get-mac-address', methods=['GET'])
def get_mac_address():
    if fbd_mac_address:
        return jsonify({"fbd_mac_address": fbd_mac_address})
    else:
        return jsonify({"error": "FBD MAC address not found."}), 404

# Function to dynamically fetch the MAC address of the local machine (using ifconfig or ip command)
def get_local_mac_address():
    try:
        # Run the ifconfig command and capture output
        output = subprocess.check_output("ifconfig", universal_newlines=True)

        # Search for the MAC address in the output (eth0 for Ethernet or wlan0 for Wi-Fi)
        # We'll look for eth0 first, then wlan0 as a fallback
        for interface in ["eth0", "wlan0"]:
            # Check if the interface exists in the output
            if interface in output:
                # Look for the MAC address (after the word "ether")
                start_index = output.find("ether", output.find(interface))
                if start_index != -1:
                    # Extract MAC address
                    mac_address = output[start_index + 6:start_index + 23]
                    return mac_address.strip()
        
        # If no MAC address found for the interfaces
        print("No MAC address found for eth0 or wlan0.")
        return None

    except Exception as e:
        print(f"Error fetching MAC address: {e}")
        return None

# Connect to the device and extract data with retry logic
async def connect_and_extract_data(device, write_char_uuid, notify_char_uuid, max_retries=5):
    for attempt in range(max_retries):
        try:
            # Connect to the device
            print(f"Attempting to connect to {device.name} ({device.address})... (Attempt {attempt + 1})")
            await connect_to_device(device.address, write_char_uuid, notify_char_uuid)

            # Add your logic here to extract data from the device
            print(f"Data extracted from {device.name} ({device.address}) successfully.")
            return  # Exit the function if successful

        except Exception as e:
            print(f"Failed to connect to {device.name} ({device.address}): {str(e)}")
            await asyncio.sleep(2)  # Wait before retrying

    print(f"Giving up on connecting to {device.name} ({device.address}) after {max_retries} attempts.")

# Continuously scan for devices and connect to the ones that match criteria
async def continuous_scan_and_connect():
    processed_devices = set()  # Create a set to track processed devices
    while True:
        print("Starting BLE Scan...")
        devices = await scan_ble_devices()  # Run the scanner

        # Filter devices whose name starts with "GT"
        target_devices = [device for device in devices if device.name and device.name.startswith("GT")]

        # Check if there are any target devices
        if target_devices:
            # Attempt to connect to the first device found
            device = target_devices[0]  # Get the first device
            print(f"Found device: {device.name} ({device.address}). Attempting to connect...")
            asyncio.create_task(connect_and_extract_data(device, WRITE_CHAR_UUID, NOTIFY_CHAR_UUID))

        # Wait for a short period before scanning again
        await asyncio.sleep(10)  # Adjust the delay as needed

# Start the Flask server in a separate thread
def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)  # Disable Flask's reloader

if __name__ == "__main__":
    # Fetch the local MAC address and store it
    fbd_mac_address = get_local_mac_address()
    if fbd_mac_address:
        print(f"Local FBD MAC address: {fbd_mac_address}")
    
    # Start the Flask server in a background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Run the continuous scan and connect logic
    asyncio.run(continuous_scan_and_connect())
