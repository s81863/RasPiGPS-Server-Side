# Overview
This project contains a Python script that can be used in combination with the [RasPiGPS](https://github.com/s81863/RasPiGPS) project. 
To use the RTK function, please adjust the parameters in <>. If you are located in Germany, you can obtain access to the [SAPOS](https://sapos.de/) satellite 
positioning service free of charge. This also offers correction services for your data. Another option is [RTK2GO](http://rtk2go.com/)

## Setup
- Set up Python on your Raspberry Pi and download all the necessary dependencies
- Make sure the python script runs without any issues
- If you want the python script to execute on boot, set up a service (with vim or nano or something similar):
```bash
sudo nano /etc/systemd/system/<YOUR-SERVICE>.service
```
- The content of the service file should look something like this:
```bash
[UNIT]
Description=Bluetooth Server Service
After=multi-user.target bluetooth.service

[Service]
ExecStart=/bin/bash -c „sleep 10 && /usr/bin/python3 /directory/of/gnss_data_server-to-client.py>
WorkingDirectory=<Verzeichnis/Python-Datei>
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```
- Activate the service
```bash
sudo systemctl daemon-reload
sudo systemctl enable <YOUR-SERVICE>.service
sudo systemctl start <YOUR-SERVICE>.service
```
- Check the service's status
```bash
sudo systemctl status <YOUR-SERVICE>.service
```
If you managed to set up everything correctly, the python script should now start on boot and you should be able to connect your phone to the RPi via the app.
