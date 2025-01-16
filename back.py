import requests
import subprocess  # To fetch the MAC address

# Backend API URLs
vital_url = "http://51.20.63.166:8000/api/v1/fbd-device/vitals"
alert_url = "http://51.20.63.166:8000/api/v1/fbd-device/alerts"

# Function to fetch the host machine's MAC address
def get_host_machine_mac():
    try:
        result = subprocess.run(['ifconfig'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout
        for line in output.split("\n"):
            if "ether" in line:
                return line.split()[1]
        return None
    except Exception as e:
        print(f"Error fetching MAC address: {e}")
        return None

# Function to send vital data to the backend
def send_data_to_backend(parsed_data, client, smartwatch_mac_address, host_mac_address):
    # Extract the heart rate, battery level, and other data from the parsed data
    heart_rate = parsed_data.get("Heart Rate", "")
    battery_level = parsed_data.get("Battery Level", "")
    
    # Prepare the payload with the extracted values
    payload = {
        "heart_rate": heart_rate,
        "blood_pressure": parsed_data.get("Blood Pressure", ""),
        "spo2": parsed_data.get("Blood Oxygen", ""),
        "device_id": parsed_data.get("1", 12345),
        "timestamp": parsed_data.get("timestamp", "1222"),
        "smartwatch_mac_address": smartwatch_mac_address,
        "fbd_mac_address": host_mac_address,
        "watch_battery": battery_level if battery_level is not None else 0,  # Updated key for battery level
        "blood_glucose": parsed_data.get("Blood Glucose", ""),
        "watch_status": parsed_data.get("Watch Status", ""),
    }

    print("Sending vital data with payload:", payload)
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(vital_url, json=payload, headers=headers, verify=False)
        if response.status_code in [200, 201]:
            print("Vital data sent successfully.")
            # Check heart rate and battery levels for alerts
            if isinstance(heart_rate, (int, float)) and (heart_rate > 100 or heart_rate < 84):
                alert_text = f"Heart rate is {'too high' if heart_rate > 100 else 'too low'}: {heart_rate}"
                send_alert2(smartwatch_mac_address, host_mac_address, "heart_rate", alert_text)
            if isinstance(battery_level, int) and battery_level < 20:
                alert_text = f"Battery level is low: {battery_level}%"
                send_alert2(smartwatch_mac_address, host_mac_address, "battery_level", alert_text)
            return True
        else:
            print(f"Failed to send data. Status: {response.status_code}, Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error sending data: {e}")
        return False

# Function to send an alert
def send_alert1(smartwatch_mac_address, host_mac_address, alert_type1, alert_text1):
    payload = {
        "alert_type": alert_type1,
        "alert_text": alert_text1,
        "smartwatch_mac_address": smartwatch_mac_address,
        "fbd_mac_address": host_mac_address,
    }
    print("Sending Alert1 with payload:", payload)
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(alert_url, json=payload, headers=headers, verify=False)
        if response.status_code in [200, 201]:
            print("Alert1 sent successfully.")
        else:
            print(f"Failed to send alert. Status: {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending alert: {e}")

# Function to send an alert for battery level or heart rate
def send_alert2(smartwatch_mac_address, host_mac_address, alert_type2, alert_text2):
    payload = {
        "alert_type": alert_type2,
        "alert_text": alert_text2,
        "smartwatch_mac_address": smartwatch_mac_address,
        "fbd_mac_address": host_mac_address,
    }
    print("Sending Alert2 with payload:", payload)
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(alert_url, json=payload, headers=headers, verify=False)
        if response.status_code in [200, 201]:
            print("Alert2 sent successfully.")
        else:
            print(f"Failed to send alert. Status: {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending alert: {e}")
