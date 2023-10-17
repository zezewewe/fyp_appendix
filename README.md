# fyp_appendix
Scripts featured in FYP Report Appendix 

## Initialization Phase
### Script 1 (Language: C)
The objective of this script is to initialize on ESP32 microcontrollers an Access Point configuration with specific SSIDs. 

## Data Collection Phase
### Script 2 (Language: C)
This script is used in the Data Collection phase, to initialize on 2 ESP32 microcontrollers (which forms the ESP32 Pair Station) the Station Mode configuration. This compiled program also allows the ESP32 Pair Station to scan for Recognised APs based on configured SSID and Channel and transmit collected data through the network. 

### Script 3 (Language: python)
This script is used in the Data Collection (manual) phase. This script is run on a host on the network to listen and store data sent over the UDP network from the ESP32 Pair Station. 

### Script 4 (Language: python)
This script is used in the Data Collection (automatic) phase. This script is run on a host on the network to listen and store data sent over the UDP network from the ESP32 Pair Station. This script also includes specific communication instructions with a vSLAM and ROS-enabled Robot to allow for autonomous waypoint navigation, sensing, and storing of data. 

## Inference Phase
### Script 5-1 (Language: Python)
This script is used in the Inference phase and is run on a host on the network to listen for data sent over the UDP network from the ESP32 Pair Station, before making an estimation of position and heading using Machine Learning and Deep Learning algorithms. 

### Script 5-2 (Language: Python)
This script is invoked by Script 5-1, as it contains the backend inference algorithm and logic that is used to generate a positional and heading estimate. 

### Script 5-3 (Language: C)
This script is a derivation of Script 2, except it is configured for use in the Inference phase. 
This script configures the ESP32 Pair Station with the Station Mode, and contains additional algorithms to facilitate the occasional error handling. 

## End-to-End Architecture Phase
### Script 6 (Language: js)
This script allows for the hosting of a webserver on the network using nodejs. This webserver exposes a POST API endpoint allowing for the delivery of positional and heading estimates. This script also supports a websocket to facilitate communication with the frontend display web application. 

### Script 7 (Language: html) 
This script provides a frontend web application to graphically display on a map the positional and heading estimate of the ESP32 Pair Station. 
