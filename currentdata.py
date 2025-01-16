import asyncio
from bleak import BleakClient
from crc_utils import verify_crc
import time
import subprocess  # To fetch the local machine's MAC address
import back  # Import the backend communication module

# Centralized error handling function
def log_error(message, details=None):
    if details:
        print(f"Error: {message} | Details: {details}")
    else:
        print(f"Error: {message}")

# Function to get the host machine's MAC address using ifconfig
def get_host_machine_mac():
    """Fetch the MAC address of the host machine (local machine)."""
    try:
        result = subprocess.run(['ifconfig'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout
        
        for line in output.split('\n'):
            if 'ether' in line:
                mac_address = line.split()[1]
                return mac_address
        return None
    except Exception as e:
        log_error("Error fetching MAC address", str(e))
        return None

# Parsing function for general data
def parse_watch_data_with_crc(response):
    if len(response) < 6:
        return {"error": "Response too short for CRC verification."}

    data_hex = response[:-4]
    received_crc = response[-4:]
    data_bytes = bytes.fromhex(data_hex)
    
    if not verify_crc(data_bytes, received_crc):
        return {"error": "CRC verification failed."}

    data_length = int(data_hex[4:8], 16)
    data_payload = data_hex[8:]

    if len(data_payload) < 44:
        return {"error": "Measuring Vitals"}

    try:
        systolic = int(data_payload[40:42], 16)
        diastolic = int(data_payload[42:44], 16)

        return {"Heart Rate": int(data_payload[38:40], 16), "Blood Pressure": f"{systolic}/{diastolic}", "Blood Oxygen": int(data_payload[44:46], 16), "Blood Glucose": int(data_payload[56:58], 16)}

    except ValueError as e:
        return {"error": f"Error parsing values: {str(e)}"}

# Parsing function for battery data
def parse_battery_data(response):
    if len(response) < 10:
        return {"error": "Battery response too short."}

    try:
        battery_hex = response[8:12]
        battery_level = int(battery_hex, 16)
        return {"Battery Level": battery_level}
    except ValueError as e:
        return {"error": f"Error parsing battery data: {str(e)}"}

# Function to fetch current data
async def fetch_current_data(client, write_char_uuid, notify_char_uuid, smartwatch_mac_address, host_mac_address):
    fixed_command = "DA0D0000AADB"
    battery_command = "DA060000DB19"

    # Create a dictionary to store shared data
    shared_data = {
        "last_parsed_data": None,
        "last_check_time": time.time(),
        "unchanged_count": 0  # Counter to track unchanged iterations
    }

    if client.is_connected:
        def notification_handler(sender, data):
            nonlocal shared_data
            response = data.hex().upper()

            if response.startswith("DA86"):
                print(f"{smartwatch_mac_address} Fetching Battery Level...")
                result = parse_battery_data(response)
                if "error" in result:
                    log_error(result["error"])
                else:
                    battery_level = result["Battery Level"]
                    print(f"Battery Level: {battery_level}%")

                    # Save battery level in shared data
                    if shared_data["last_parsed_data"]:
                        shared_data["last_parsed_data"]["Battery_Level"] = battery_level
                    else:
                        shared_data["last_parsed_data"] = {"Battery_Level": battery_level}
            else:
                result = parse_watch_data_with_crc(response)
                if "error" in result:
                    if result["error"] != "Measuring Vitals":
                        log_error(result["error"])
                else:
                    print("Parsed Data:")
                    for key, value in result.items():
                        print(f"{key}: {value}")

                    # Add battery level to the parsed data if available
                    if shared_data["last_parsed_data"] and "Battery_Level" in shared_data["last_parsed_data"]:
                        result["Battery Level"] = shared_data["last_parsed_data"]["Battery_Level"]

                    if all(k in result for k in ["Heart Rate", "Blood Pressure", "Blood Oxygen"]):
                        # Check if the data is unchanged to determine if the watch is worn
                        if shared_data["last_parsed_data"]:
                            unchanged = all(result[key] == shared_data["last_parsed_data"].get(key) for key in ["Heart Rate", "Blood Pressure", "Blood Oxygen"])

                            if unchanged:
                                shared_data["unchanged_count"] += 1
                            else:
                                shared_data["unchanged_count"] = 0

                        # If data hasn't changed for 2 iterations, assume the watch is not worn
                        if shared_data["unchanged_count"] >= 2:
                            print(f"{smartwatch_mac_address}: Watch is not worn")
                            result["Watch Status"] = "Not Worn"
                        else:
                            print(f"{smartwatch_mac_address}: Watch is being worn")
                            result["Watch Status"] = "Worn"

                        # Update shared data for the next iteration
                        shared_data["last_parsed_data"] = result
                        shared_data["last_check_time"] = time.time()

                    # Send parsed data to the backend (now includes battery level)
                    print("Sending data to the server...")
                    success = back.send_data_to_backend(result, client, smartwatch_mac_address, host_mac_address)
                    if success:
                        print("Data sent successfully.")
                    else:
                        log_error("Failed to send data to the backend.")

        # Start notifications
        await client.start_notify(notify_char_uuid, notification_handler)

        while True:
            # Send fixed command to the smartwatch
            await client.write_gatt_char(write_char_uuid, bytes.fromhex(fixed_command))
            await asyncio.sleep(1)  # Wait for a second before sending the battery command
            await client.write_gatt_char(write_char_uuid, bytes.fromhex(battery_command))
            await asyncio.sleep(30)  # Wait for 30 seconds before the next iteration

# Main function to connect to the smartwatch and start fetching data
async def main(smartwatch_mac_address):
    host_mac_address = get_host_machine_mac()
    async with BleakClient(smartwatch_mac_address) as client:
        write_char_uuid = "YOUR_WRITE_CHARACTERISTIC_UUID"
        notify_char_uuid = "YOUR_NOTIFY_CHARACTERISTIC_UUID"
        await fetch_current_data(client, write_char_uuid, notify_char_uuid, smartwatch_mac_address, host_mac_address)

# Entry point of the script
if __name__ == "__main__":
    smartwatch_mac_address = "YOUR_SMARTWATCH_MAC_ADDRESS"
    asyncio.run(main(smartwatch_mac_address))
