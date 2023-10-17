# # Script to keep listening and storing data (XPS13)
# # To Run: python main\UDP.py mode pos
# # Run using CMD
# Manual mode 

import datetime
import csv
import socket
import os
import time
import sys

machine = 1 
if machine==1: # XPS13
    LOCAL_IP_ADDRESS = "192.168.1.102" 
    # path_prefix = "C:/Users/ngzew/fyp/scan/data_output/reading_logs/"
    path_prefix = "/mnt/c/Users/ngzew/fyp/scan/data_output/reading_logs/"
    LOCAL_IP_PORT = 4200
elif machine==2: # Robot
    LOCAL_IP_ADDRESS = "192.168.3.203" 
    path_prefix = "C:/Users/ngzew/fyp/scan/data_output/reading_logs/"
    LOCAL_IP_PORT = 4210
ESP32_IP_ADDRESS_1 = "192.168.1.100" # Left
ESP32_IP_PORT_1 = 4220
ESP32_IP_ADDRESS_2 = "192.168.1.101" # Right
ESP32_IP_PORT_2 = 4230
MESSAGE = b"SCAN"
dateToday = str(datetime.datetime.now().date())
path_readLog = path_prefix+"{}-readings.txt".format(dateToday)
path_posLog = path_prefix+"{}-positions.txt".format(dateToday)


path='C:/Users/ngzew/fyp/scan/main/HostFiles/waypoint3.txt'
path='/mnt/c/Users/ngzew/fyp/scan/main/HostFiles/waypoint3.txt'
waypoints_file=open(path,'r')
contents=waypoints_file.read()
waypoints_list=[i.split(',') for i in contents.split('\n')[:-1]]
numWaypoints=len(waypoints_list)

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

sock = socket.socket(socket.AF_INET, # Internet
                    socket.SOCK_DGRAM) # UDP
sock.bind((LOCAL_IP_ADDRESS, LOCAL_IP_PORT))
print('Sock Binded')


def readAndStore(pos):

    print('Running readAndStore: ',pos) 
    
    success = 0
    while success == 0:
        # a - Get data from both ESP32-L and ESP32-R
        data_1, addr_1 = sock.recvfrom(1024) # buffer size is 1024 bytes
        decoded_data_1 = data_1.decode('utf-8')
        data_flag_1 = decoded_data_1[0]
        print('Message from ESP {} = {}'.format(data_flag_1,decoded_data_1))
        data_2, addr_2 = sock.recvfrom(1024) # buffer size is 1024 bytes
        decoded_data_2 = data_2.decode('utf-8')
        data_flag_2 = decoded_data_2[0]
        print('Message from ESP {} = {}'.format(data_flag_2,decoded_data_2))
        
        data_flag_combined = data_flag_1+data_flag_2

        if data_flag_combined == 'LR' or data_flag_combined == 'RL': # start-up / reset
            print("Set-up Complete")
            success = 1
        
        elif data_flag_combined == '12' or data_flag_combined == '21': # store received information
            # data_waypoint, addr_waypoint = sock.recvfrom(1024) # buffer size is 1024 bytes
            # decoded_data_waypoint = data_waypoint.decode('utf-8')
            if machine == 2: # only robot needs to log position
                mode_posLog = 'a' if os.path.exists(path_posLog) else 'w'
                with open(path_posLog,mode_posLog,newline='') as f:
                    f.write('{}:{}\n'.format(datetime.datetime.now().strftime('%H%M%S'),pos))
                    f.close()

            decoded_data_1 = decodeStr(decoded_data_1)
            decoded_data_2 = decodeStr(decoded_data_2)

            if data_flag_combined == '12':
                decoded_data_L,decoded_data_R = decoded_data_1,decoded_data_2
            else:
                decoded_data_L,decoded_data_R = decoded_data_2,decoded_data_1

            print("Received message: {} {}".format(decoded_data_L, decoded_data_R))

            mode_posLog = 'a' if os.path.exists(path_posLog) else 'w'
            with open(path_posLog,mode_posLog) as f:
                f.write('{}:{}\n'.format(datetime.datetime.now().strftime('%H%M%S'),pos))
                f.close()

            mode = 'a' if os.path.exists(path_readLog) else 'w'
            with open(path_readLog,mode,newline='') as f:
                writer=csv.writer(f)
                writer.writerow(decoded_data_L)
                writer.writerow(decoded_data_R)
    
                f.close()

            success = 1

        else:
            print("Failed to receive from an ESP, retry scanning.")
            sendToScan() 
    
    # return 1

def sendToScan():
    # d - Transmit "SCAN" to ESP32-L and -R and repeat from step a
    # Time to repeat the scanning (communicate with the 2 ESP32s)
    print("Reached new location. Instruct ESPs to start Scanning.")
    sock.sendto(MESSAGE, (ESP32_IP_ADDRESS_1, ESP32_IP_PORT_1))
    sock.sendto(MESSAGE, (ESP32_IP_ADDRESS_2, ESP32_IP_PORT_2)) 


# if __name__ == "__main__":
#     # Mode 1: Read  
#     # Mode 2: Scan 
#     mode=sys.argv[1]
#     pos=sys.argv[2] # for mode 2: A/B/C/D, for mode 1: one random character
#     # print(type(mode))

#     if mode == '1':
#         while(1):
#             readAndStore(pos) # 
#     elif mode == '2':
#         sendToScan()
#         readAndStore(pos)
#     elif mode == '3':
#         sendToScan() #retransmit

if __name__ == "__main__":
    # Mode 1: Read  
    # Mode 2: Scan 

    for pos in waypoints_list:
        print('MAIN: Move to: {}. Once done, hit enter.'.format(pos))
        input()
        sendToScan()
        readAndStore(pos)
        print('pos')
    print('Data collection complete.')

    



'''
# QUICK INIT
import socket
LOCAL_IP_ADDRESS = "192.168.3.202" # Localization
LOCAL_IP_PORT = 4210
ESP32_IP_ADDRESS_1 = "192.168.3.200" # Left
ESP32_IP_PORT_1 = 4220
ESP32_IP_ADDRESS_2 = "192.168.3.201" # Right
ESP32_IP_PORT_2 = 4230
sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.bind((LOCAL_IP_ADDRESS, LOCAL_IP_PORT))

def decodeStr(rx):
    tmpList = [rx[0],',']+[-(ord(j)-48) if i%2==0 else j for i,j in enumerate(rx[1:])]
    cleanedList = []
    for i in tmpList:
        if i!=',':
            cleanedList.append(i)
    return cleanedList   

def readAndPrint():
    data_1, addr_1 = sock.recvfrom(1024) # buffer size is 1024 bytes
    data_flag_1 = data_1.decode('utf-8')[0]
    print('Message from ESP {} ...'.format(data_flag_1))
    data_2, addr_2 = sock.recvfrom(1024) # buffer size is 1024 bytes
    data_flag_2 = data_2.decode('utf-8')[0]
    print('Message from ESP {} ...'.format(data_flag_2))
    decoded_data_1 = decodeStr(data_1.decode('utf-8'))
    decoded_data_2 = decodeStr(data_2.decode('utf-8'))
    print("Received message: {} {}".format(decoded_data_1, decoded_data_2))


def sendToScan():
    MESSAGE = b"SCAN"
    sock.sendto(MESSAGE, (ESP32_IP_ADDRESS_1, ESP32_IP_PORT_1))
    sock.sendto(MESSAGE, (ESP32_IP_ADDRESS_2, ESP32_IP_PORT_2)) 

def decodeMsgs():
    decoded_data_1 = decodeStr(data_1.decode('utf-8'))
    decoded_data_2 = decodeStr(data_2.decode('utf-8'))
    print("Received message: {} {}".format(decoded_data_1, decoded_data_2))

sendToScan()
readAndPrint()
'''