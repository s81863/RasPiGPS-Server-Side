import subprocess
import threading
import socket
import bluetooth
import serial
import pynmea2
import time
import pyproj

source_epsg = 'EPSG:4326'
target_epsg = 'EPSG:25833'

proj = pyproj.Transformer.from_crs(source_epsg, target_epsg, always_xy=True)

def find_usb_bluetooth_device():
    hciconfig_output = subprocess.run(["hciconfig"], capture_output=True, text=True).stdout

    for line in hciconfig_output.split('\n'):
        if "USB" in line:
            device_name = line.split()[0]
            return device_name
    return None

def enable_bluetooth():
    usb_device_name = find_usb_bluetooth_device()

    if usb_device_name is None:
        print("USB dongle not found")
        exit(1)
    
    check_output = subprocess.run(["hciconfig", usb_device_name], capture_output=True, text=True)
    if "UP_RUNNING" in check_output.stdout:
        return

    subprocess.run(["sudo", "hciconfig", usb_device_name, "up"])
    time.sleep(1)

def make_discoverable():
    usb_device_name = find_usb_bluetooth_device()
    if usb_device_name is None:
        print("USB dongle not found")
        exit(1)
        
    subprocess.run(["sudo", "hciconfig", usb_device_name, "piscan"])

def check_usb_device(device_path):
    # Try to open the device path
    try:
        with open(device_path) as f:
            return True
    except FileNotFoundError:
        return False

def send_status(client_sock, status):
    client_sock.send(status.encode())

def handle_rtk_command(client_sock, stop_event):
    while not stop_event.is_set():
        # read bluetooth data
        received_data = client_sock.recv(1024).decode().strip()
        
        # check for RTK start command
        if received_data == "START_RTK":
            print("Button Pressed")
            # check internet connection
            try:
                socket.create_connection(("www.google.com", 80))
                internet_connected = True
                print("Internet Connection:", internet_connected)
            except OSError:
                internet_connected = False
                print("Internet Connection:", internet_connected)

            if internet_connected:
                try:
                    print("starting str2str...")
                    subprocess.run(["str2str", "-in", "ntrip://<USER>:<PASSWORD>@<IPAddress>:<PORT>/<MOUNTPOINT>",
                                    "-b", "1", "-out", "serial://ttyACM0:38400:8:n:1"], check=True)
                    client_sock.send("01: RTK started".encode())
                except subprocess.CalledProcessError:
                    client_sock.send("02: Error executing str2str command".encode())
            else:
                client_sock.send("03: No internet connection".encode())

def run_server():
    # Initialize Bluetooth server socket
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.bind(("", bluetooth.PORT_ANY))
    server_sock.listen(1)

    # Get the port number
    port = server_sock.getsockname()[1]

    # UUID for the Bluetooth service
    uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"

    # Advertise the Bluetooth service
    bluetooth.advertise_service(server_sock, "GNSS_Server", service_id=uuid,
                                 service_classes=[uuid, bluetooth.SERIAL_PORT_CLASS],
                                 profiles=[bluetooth.SERIAL_PORT_PROFILE])

    print("Waiting for connection on RFCOMM channel", port)

    # Accept incoming connection
    client_sock, client_info = server_sock.accept()
    print("Accepted connection from", client_info)

    # Open serial connection to GPS device if available
    while True:
        if check_usb_device('/dev/ttyUSB0'):
            try:
                ser = serial.Serial('/dev/ttyUSB0', 38400, timeout=1.0)
                break
            except serial.SerialException:
                print("GPS device not ready, waiting...")
                send_status(client_sock, "STATUS: Receiver not connected")
                time.sleep(5)
        else:
            print("GPS device not found, waiting...")
            send_status(client_sock, "STATUS: Receiver not connected")
            time.sleep(5)
            
    client_sock.send("STATUS: Receiver connected".encode())

    stop_event = threading.Event()
    rtk_thread = threading.Thread(target=handle_rtk_command, args=(client_sock, stop_event))
    rtk_thread.start()

    try:
        while True:
            # Read GPS data
            line = ser.readline().decode('utf-8')
            #print(ser.readline())
            
            if line.startswith('$GNGGA'):
                msg = pynmea2.parse(line)
                time = msg.timestamp
                n_sats = msg.num_sats
                qual = msg.gps_qual
                lat = round(msg.latitude, 8)
                lat_d = msg.lat_dir
                lon = round(msg.longitude, 8)
                lon_d = msg.lon_dir
                alt = msg.altitude
                h_dil = msg.horizontal_dil

                x, y = proj.transform(lon, lat)
                x = round(x, 3)
                y = round(y, 3)
                utm_data = f"UTM:,{y},{x}"

                # Format GPS data
                gps_data = f"{time},{n_sats},{qual},{lat},{lat_d},{lon},{lon_d},{alt},{h_dil}"

                # Send GPS data over Bluetooth
                str = gps_data + ',' + utm_data
                client_sock.send(str.encode())
                #client_sock.send(utm_data.encode())


    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        rtk_thread.join()
        # Close connections
        client_sock.close()
        server_sock.close()
        ser.close()
        print("Programm beendet")

if __name__ == "__main__":
    enable_bluetooth()
    make_discoverable()
    run_server()
