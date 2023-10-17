
###############
### UdpCmds ###
###############

# Script to keep listening and storing data (XPS13)
# To Run: python main\UDP.py mode pos

import datetime
import csv
import socket
import os
import time
import sys

import roslib #; roslib.load_manifest('rbx1_nav')
import rospy
import actionlib
from actionlib_msgs.msg import *
from geometry_msgs.msg import Pose, Point, Quaternion, Twist
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from tf.transformations import quaternion_from_euler
from visualization_msgs.msg import Marker
from math import radians, pi


machine = 2 
if machine==1: # XPS13
    LOCAL_IP_ADDRESS = "192.168.3.202" 
    path_prefix = "C:/Users/ngzew/fyp/scan/data_output/reading_logs/"
    LOCAL_IP_PORT = 4200
elif machine==2: # Robot
    LOCAL_IP_ADDRESS = "192.168.3.57" # to check and adjust before each experiment (cli: ifconfig)
    path_prefix = "/home/nuc/Documents/FYP/data_output/reading_logs/"
    LOCAL_IP_PORT = 4210
ESP32_IP_ADDRESS_1 = "192.168.3.200" # Left
ESP32_IP_PORT_1 = 4220
ESP32_IP_ADDRESS_2 = "192.168.3.201" # Right
ESP32_IP_PORT_2 = 4230
MESSAGE = b"SCAN"
dateToday = str(datetime.datetime.now().date())
path_readLog = path_prefix+"{}-readings.txt".format(dateToday)
path_posLog = path_prefix+"{}-positions.txt".format(dateToday)

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

    print(pos) 
    
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
                with open(path_posLog,mode_posLog) as f:
                    f.write('{}:{}\n'.format(datetime.datetime.now().strftime('%H%M%S'),pos))
                    f.close()

            decoded_data_1 = decodeStr(decoded_data_1)
            decoded_data_2 = decodeStr(decoded_data_2)

            if data_flag_combined == '12':
                decoded_data_L,decoded_data_R = decoded_data_1,decoded_data_2
            else:
                decoded_data_L,decoded_data_R = decoded_data_2,decoded_data_1

            print("Received message: {} {}".format(decoded_data_L, decoded_data_R))

            mode = 'a' if os.path.exists(path_readLog) else 'w'
            with open(path_readLog,mode) as f:
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
    print('hi')
    # d - Transmit "SCAN" to ESP32-L and -R and repeat from step a
    # Time to repeat the scanning (communicate with the 2 ESP32s)
    print("Reached new location. Instruct ESPs to start Scanning.")
    sock.sendto(MESSAGE, (ESP32_IP_ADDRESS_1, ESP32_IP_PORT_1))
    sock.sendto(MESSAGE, (ESP32_IP_ADDRESS_2, ESP32_IP_PORT_2)) 


path='/home/nuc/Documents/FYP/waypoint2.txt'
waypoints_file=open(path,'r')
contents=waypoints_file.read()
waypoints_list=[i.split(',') for i in contents.split('\r\n')[:-1]]
numWaypoints=len(waypoints_list)

class MoveBaseNavigation():
    def __init__(self):
        rospy.init_node('nav_test', anonymous=False)
        
        #rospy.on_shutdown(self.shutdown)
        
        # Create a list to hold the target quaternions (orientations)
        quaternions = list()
        

        euler_angles = (pi/2, pi, 3*pi/2, 0) # 0 is the original heading (positive y direction)
        symbol_to_number = {'A':0,'B':1,'C':2,'D':3}    
    
        # Then convert the angles to quaternions
        for angle in euler_angles:
            q_angle = quaternion_from_euler(0, 0, angle, axes='sxyz')
            q = Quaternion(*q_angle)
            quaternions.append(q)
        
        # Create a list to hold the waypoint poses
        waypoints = list()
        
        for i in waypoints_list:
            x,y,orientationSymbol=i
            orientationIdx=symbol_to_number[orientationSymbol]
            waypoints.append(Pose(Point(float(x),float(y),0.0),quaternions[orientationIdx])) # to test if this works
        print('check first 10 waypoints',waypoints[:10])

        # Subscribe to the move_base action server
        self.move_base = actionlib.SimpleActionClient("move_base", MoveBaseAction)
        rospy.loginfo("Waiting for move_base action server...")
        
        # Wait 60 seconds for the action server to become available
        wait = self.move_base.wait_for_server(rospy.Duration(60))
        if not wait:
            rospy.logerr("Action server not available.")
            rospy.signal_shutdown("Action server not available.")
            return
        rospy.loginfo("Connected to move base server")
        rospy.loginfo("Starting navigation ...")
        
        # Initialize a counter to track waypoints
        i = 0
        
        # Cycle through the four waypoints
        while i < numWaypoints and not rospy.is_shutdown():
            # Update the marker display
            # self.marker_pub.publish(self.markers)
            
            # Intialize the waypoint goal
            goal = MoveBaseGoal()
            
            # Use the map frame to define goal poses
            goal.target_pose.header.frame_id = 'map'
            
            # Set the time stamp to "now"
            goal.target_pose.header.stamp = rospy.Time.now()
            
            # Set the goal pose to the i-th waypoint
            goal.target_pose.pose = waypoints[i]
            
            # Start the robot moving toward the goal
            self.move(goal)

            espScanComplete = False
            espStoreComplete = False
            while not espScanComplete: # ensure scan is complete
            	sendToScan()
                espScanComplete = True
            while not espStoreComplete: # ensure read and store is complete
                readAndStore(waypoints_list[i])
                espStoreComplete = True
            i+= 1




    def move(self, goal):
            # Send the goal pose to the MoveBaseAction server
            self.move_base.send_goal(goal)
            
            # Allow 1 minute to get there
            finished_within_time = self.move_base.wait_for_result(rospy.Duration(90)) 
            
            # If we don't get there in time, abort the goal
            if not finished_within_time:
                self.move_base.cancel_goal()
                rospy.loginfo("Timed out achieving goal")
            else:
                # We made it!
                state = self.move_base.get_state()
                if state == GoalStatus.SUCCEEDED:
                    rospy.loginfo("Goal succeeded!")

if __name__ == '__main__':
    try:
        MoveBaseNavigation()
    except rospy.ROSInterruptException:
        rospy.loginfo("Navigation test finished.")


