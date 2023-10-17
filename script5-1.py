# Script for inference
# Run using cmd py <path> (python 3.7 required for asyncio.run())

import asyncio
import requests
import socket

import datetime
import csv
import os
import time
import sys

from inferenceScript4 import data_inference
# Step 1: Define function to handle incoming data from ESP32

LOCAL_IP_ADDRESS = "192.168.3.202" 
LOCAL_IP_PORT = 4201 # 4205 # 4200
ESP32_IP_ADDRESS_1 = "192.168.3.200" # Left
ESP32_IP_PORT_1 = 4220


ESP32_IP_ADDRESS_2 = "192.168.3.201" # Right
ESP32_IP_PORT_2 = 4230

# // ID MAC LocalizationNetwork HomeNetwork Port
# // ESP-L 10:97:bd:d5:5e:38 192.168.3.200 192.168.1.100 4220
# // ESP-R 40:91:51:23:16:0c 192.168.3.201 192.168.1.101 4230
# // XPS13 9C-B6-D0-9A-15-B7 192.168.3.202 192.168.1.102 4200

MESSAGE = b"SCAN"
dateToday = str(datetime.datetime.now().date())

# Helper Functions
def codeToNum(codeStr):
    return [-(ord(i)-32) for i in codeStr]

def decodeStr(rx):
    '''
    Input: ASCII converted symbols 
    Output: 0/1 leading flag (L/R ESP) followed by RSSI values [AP0.1, AP0.2, ..., AP0.M, ... APN.(M-1), APN.M] for N APs and M Readings 
    '''
    outputList=[rx[0]]
    for i in rx[2:-1].split('#'):
        outputList+=codeToNum(i.replace('-',''))
    return outputList      

# def data_inference(data_L,data_R):
#     x=1.0
#     y=2.0
#     z=3.0
#     h=90 # deg
#     # consider including confidence as well
#     return x,y,z,h

def handle_udp_data():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(20.0) # 31 Aug Test Timeout
    udp_socket.bind((LOCAL_IP_ADDRESS, LOCAL_IP_PORT))
    print("UDP Socket Binded:", udp_socket)
    udp_socket.sendto(MESSAGE, (ESP32_IP_ADDRESS_1, ESP32_IP_PORT_1))
    udp_socket.sendto(MESSAGE, (ESP32_IP_ADDRESS_2, ESP32_IP_PORT_2)) 

    while True:
        # Receive Data from both ESP32 (Left and Right)
        receiveData=True
        while receiveData:
            try:    
                data_1, addr_1 = udp_socket.recvfrom(1024) # buffer size is 1024 bytes
                data_2, addr_2 = udp_socket.recvfrom(1024) # buffer size is 1024 bytes
                receiveData=False
            except TimeoutError:
                print('Timeout Error, Resend Scan Cmd to STAs')
                udp_socket.sendto(MESSAGE, (ESP32_IP_ADDRESS_1, ESP32_IP_PORT_1))
                udp_socket.sendto(MESSAGE, (ESP32_IP_ADDRESS_2, ESP32_IP_PORT_2)) 
        # print(data_1,addr_1)
        # print(data_2,addr_2)
        decoded_data_1 = data_1.decode('utf-8')
        data_flag_1 = decoded_data_1[0]
        print('Message from ESP {} = {}'.format(data_flag_1,decoded_data_1))
        decoded_data_2 = data_2.decode('utf-8')
        data_flag_2 = decoded_data_2[0]
        print('Message from ESP {} = {}'.format(data_flag_2,decoded_data_2))

        # Triage data received into first time init or subsequent pose data
        data_flag_combined = data_flag_1+data_flag_2
        if data_flag_combined == 'LR' or data_flag_combined == 'RL': # first time init (start up / reset)
            print("Set-up Complete")
            # Message = Online or something
        elif data_flag_combined == '12' or data_flag_combined == '21': # subsequent time with pose data
            decoded_data_1 = decodeStr(decoded_data_1)
            decoded_data_2 = decodeStr(decoded_data_2)

            # Left then Right data 
            if data_flag_combined == '12':
                decoded_data_L,decoded_data_R = decoded_data_1,decoded_data_2
            else:
                decoded_data_L,decoded_data_R = decoded_data_2,decoded_data_1
            print("Received message: {} {}".format(decoded_data_L, decoded_data_R))
            [xinf,yinf],oriinf=data_inference(decoded_data_L,decoded_data_R)

        else: # Error with received data streams 
            print("Failed to receive from an ESP, retry scanning.")
        
        udp_socket.sendto(MESSAGE, (ESP32_IP_ADDRESS_1, ESP32_IP_PORT_1))
        udp_socket.sendto(MESSAGE, (ESP32_IP_ADDRESS_2, ESP32_IP_PORT_2)) 

        data_to_send = {'x': xinf,'y': yinf,'alphabet': oriinf,'conf':5}
        send_data_to_webserver(data_to_send)  # Broadcast processed data to WebSocket clients

def send_data_to_webserver(data):
    url = 'http://localhost:3000/api/pose'  # Replace with the URL of your Node.js server endpoint
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print('Data sent to webserver successfully.')
        else:
            print('Failed to send data to webserver. Status code:', response)
    except requests.exceptions.RequestException as e:
        print('Error:', e)




# # Step 2: Define function to broadcast data to WebSocket clients
# async def broadcast_data(data):
#     for client in connected_clients:
#         try:
#             print(client,data)
#             await client.send(data)
#         except Exception as e:
#             print('Exception:', e)
#             connected_clients.remove(client)




# async def start_websocket_server():
#     # Create the WebSocket server and handle WebSocket client connections
#     await websockets.serve(websocket_handler, 'localhost', 8765)
#     print("Websocket server started")
#     await asyncio.Future() # This will keep the WebSocket server running

# connected_clients = set()

# # Step 4: Define function to handle WebSocket client connections
# async def websocket_handler(websocket, path):
#     print(websocket)
#     connected_clients.add(websocket) # add client to set of connected clients
#     print('Connected to a client socket',connected_clients)
#     try: 
#         while True:
#             message = await websocket.recv() # Receive message from client 
#             print('Received message:', message)
#     except Exception as e:
#         print('Exception:', e)
#         connected_clients.remove(websocket)


# Step 6: Run the asyncio event loop
if __name__ == "__main__":
    # websocket_task = asyncio.create_task(start_websocket_server())
    # udp_task = asyncio.create_task(handle_udp_data())
    
    # asyncio.run(main())
    # futures = [start_websocket_server(),handle_udp_data()]
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(asyncio.gather(futures))

    handle_udp_data()