import asyncio
from bleak import BleakClient
from currentdata import fetch_current_data  # Fetch current data functionality
from back import send_alert1  # Import send_alert from back.py

import subprocess  # To fetch the local machine's MAC address

# Function to get the host machine's MAC address using ifconfig
def get_host_machine_mac():
    """Fetch the MAC address of the host machine (local machine)."""
    try:
        result = subprocess.run(['ifconfig'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout

        # Searching for MAC address in the output
        for line in output.split('\n'):
            if 'ether' in line:  # 'ether' is the keyword used in 'ifconfig' output
                mac_address = line.split()[1]
                return mac_address
        return "UNKNOWN_HOST_MAC"
    except Exception as e:
        print(f"Error fetching MAC address: {e}")
        return "UNKNOWN_HOST_MAC"

async def connect_to_device(address, write_char_uuid, notify_char_uuid, max_retries=3, retry_interval=5):
    print(f"Attempting to connect to device: {address}")

    retries = 0
    client = None

    # Fetch the host MAC address in advance
    host_mac_address = get_host_machine_mac()
    smartwatch_mac_address = address  # The smartwatch MAC address is the device address we're trying to connect to.

    # Define alert parameters
    alert_type1 = "connection_error"  # Define the alert type
    alert_text1 = f"Failed to connect to device {address} after {max_retries} attempts."
  
    while retries < max_retries:
        try:
            print(f"Connecting to {address}... Attempt {retries + 1}/{max_retries}")
            client = BleakClient(address)  # Create BleakClient instance
            await client.connect()  # Attempt to connect to the device

            if client.is_connected:
                print(f"Connected to {address}")

                # Fetch and send commands after successful connection
                await sensorsON(client, write_char_uuid, notify_char_uuid)
                await MasterS(client, write_char_uuid, notify_char_uuid)
                await send_device_setting_request(client, write_char_uuid, notify_char_uuid)

                # Fetch and send current data with the smartwatch and host MAC addresses
                await fetch_current_data(client, write_char_uuid, notify_char_uuid, smartwatch_mac_address, host_mac_address)

                return client  # Return the connected client instance
            else:
                print(f"Failed connecting to {address}")
        except Exception as e:
            print(f"Connection attempt {retries + 1}/{max_retries} failed: {str(e)}")
            print(f"Smartwatch MAC address attempted: {smartwatch_mac_address}")  # Print the MAC address

        retries += 1
        if retries < max_retries:
            print(f"Retrying in {retry_interval} seconds...")
            await asyncio.sleep(retry_interval)

    # If connection fails after max retries, send an alert and print the MAC address
    print(f"Failed to connect to device {address} after {max_retries} attempts.")
    
    # Send an alert with the real MAC addresses
    send_alert1(
        smartwatch_mac_address=smartwatch_mac_address if smartwatch_mac_address else "UNKNOWN_SMARTWATCH_MAC",
        host_mac_address=host_mac_address,
        alert_type1=alert_type1,
        alert_text1=alert_text1
    )

  

    return None

# Function to send the binding request and handle response
async def send_binding_request(client, write_char_uuid, notify_char_uuid):
    binding_request = "DA0101000009EF"
    print(f"Sending Binding Request")
    await client.write_gatt_char(write_char_uuid, bytes.fromhex(binding_request))

    # Define a response handler for the notify characteristic
    def response_handler(sender, data):
        response_code = data.hex().upper()
        if response_code == "DA81010002A1EE":
            print("ERROR, Binding Failed.")
        elif response_code == "DA8102000000EF5C":
            print("No response.")
        elif response_code == "DA8102000001EF5C":
            print("Successfully Bound.")
        elif response_code == "DA81020000002E9C":
            print("Binding Rejected")
        else:
            print("No response.")

    await client.start_notify(notify_char_uuid, response_handler)
    print("Awaiting Binding Response...")
    await asyncio.sleep(10)
    await client.stop_notify(notify_char_uuid)
    print("Binding DONE.")

# Function to send the sensor ON command after binding
async def sensorsON(client, write_char_uuid, notify_char_uuid):
    device_setting_request = "DA700700112131415161717B2D"
   #print(f"Sending sensors ON command")
    
    response_received = False
    
    def sensorsON_handler(sender, data):
        nonlocal response_received
        response_code = data.hex().upper()

        if response_code == "DAF00100003B13":
            print("Sensors ON, SUCCESSFUL")
            response_received = True

    await client.start_notify(notify_char_uuid, sensorsON_handler)
    
    attempts = 0
    max_attempts = 10
    
    while attempts < max_attempts:
        if response_received:
            break
        
        print(f"Attempt {attempts + 1}/{max_attempts}: Sending sensors ON command...")
        await client.write_gatt_char(write_char_uuid, bytes.fromhex(device_setting_request))

        await asyncio.sleep(5)
        attempts += 1

    if not response_received:
        print(f"Failed after {max_attempts} attempts.")
    await client.stop_notify(notify_char_uuid)
    print("Switching ON Sensors DONE.")
    print("")

# Function to send Heartrate Synchronization
async def MasterS(client, write_char_uuid, notify_char_uuid):
    device_setting_request = "DA0E060001010101010144BE"
    print(f"Master Switching")
    
    response_received = False
    
    def MasterS(sender, data):
        nonlocal response_received
        response_code = data.hex().upper()

        if response_code == "DA8E010000233B":
            print("Master Switching, SUCCESSFUL")
            response_received = True

    await client.start_notify(notify_char_uuid, MasterS)
    
    attempts = 0
    max_attempts = 10
    
    while attempts < max_attempts:
        if response_received:
            break
        
        print(f"Attempt {attempts + 1}/{max_attempts}: Switching on Master Sensors..")
        await client.write_gatt_char(write_char_uuid, bytes.fromhex(device_setting_request))

        await asyncio.sleep(5)
        attempts += 1

    if not response_received:
        print(f"Failed after {max_attempts} attempts.")
    await client.stop_notify(notify_char_uuid)
    print("Master Switching, DONE.")
    print("")

# Function to send the device setting command after binding
async def send_device_setting_request(client, write_char_uuid, notify_char_uuid):
    device_setting_request = "DA310600000000000164FD49"
    print(f"Setting Device Measurement Interval")
    
    response_received = False
    
    def device_setting_response_handler(sender, data):
        nonlocal response_received
        response_code = data.hex().upper()

        if response_code == "DAB10100002F2F":
            print("Measurement Interval Setting, SUCCESSFUL")
            response_received = True

    await client.start_notify(notify_char_uuid, device_setting_response_handler)
    
    attempts = 0
    max_attempts = 10
    
    while attempts < max_attempts:
        if response_received:
            break
        
        print(f"Attempt {attempts + 1}/{max_attempts}: Sending measurement interval setting request...")
        await client.write_gatt_char(write_char_uuid, bytes.fromhex(device_setting_request))

        await asyncio.sleep(5)
        attempts += 1

    if not response_received:
        print(f"Failed to set after {max_attempts} attempts.")
    await client.stop_notify(notify_char_uuid)
    print("Measurement Interval process DONE.")
    print("")
