''' 
standarize the communication between frontend and the local node 
[Iteration2] we have remove the auto update target point function
'''
#from ui_nodes import * we do not need ui_nodes any more

from math import sqrt

import rospy
from functools import reduce
from centralized_dashboard.msg import NavigationMsg
from centralized_dashboard.msg import Drive

from userErr import * 
from cmd import *

class GPSPoint:
    def __init__(self, lati, longt):
        self.lati = lati
        self.longt = longt

    def __repr__(self):
        return '(' + str(self.lati) + ',' + str(self.longt) + ')'

class Rover:
    def __init__(self, name, frequency=100, auto_init=True):    # frequency is the commmand topic sending freq
        # NOTICE:   those fields are though read_only for outside program but not protected.
        #           make sure you did not overwrite them mistakenly
        self.gps_longt = 0.0
        self.gps_lati = 0.0
        # the current pos of the car
        self.buffer_longt = 0.0 
        self.buffer_lati = 0.0
        # the target pos of the car
        self.ori = 0.0
        self.speed = []
        # self.arm = []
        self.remark = ''
        self.name = name
        # self.warn_flag = False # indicate whenever there is a warning.
        self.route_state = []   # rover only accept cur/target and cannot accept a full path
                                # hence the path is stored locally
                                # route_state[0] stores the start point and it gets updated everytime a passing point is achieved
                                # 0-----*-O-------O--------O-------O------------O
                                # r[0]    r[1]    r[2]                            for example: it get updated when rover arrive r[1]
                                #         0--*----O--------O-------O------------O
                                #         r[0]    r[1]     r[2]
        if auto_init:
            self.ros_init()

    def ros_init(self):
        #ros init
        rospy.init_node(self.name, anonymous=False)
        print("ros node init successfully")
        #sub
        rospy.Subscriber('/nav_data', NavigationMsg, self.nav_callback)
        rospy.Subscriber('/drive_data', Drive, self.drive_callback)
        #pub
        self.navi_pub = rospy.Publisher('/set_nav_data', NavigationMsg, queue_size=1)   # it is the topic that we send command to rover 
        self.driv_pub = rospy.Publisher('/set_drive_data', Drive, queue_size=1)              # so it should have a differnt name

    def __debug_print(self, str):
        pass
        # print(str)  # currently we just output to consol
        # if self.remark == '' : 
        #   self.remark = str
        # else:
        #   self.remark = self.remark + '\n' + str

    def nav_callback(self, nav_data):
        self.ori = nav_data.heading
        self.gps_longt = nav_data.cur_long
        self.gps_lati = nav_data.cur_lat
        if self.route_state == []:
            self.route_state = [GPSPoint(self.gps_lati, self.gps_longt)]
        self.buffer_longt = nav_data.tar_long
        self.buffer_lati = nav_data.tar_lat

    def drive_callback(self, drive_data):
        self.speed = [      drive_data.wheel0,
                            drive_data.wheel1,
                            drive_data.wheel2,
                            drive_data.wheel3,
                            drive_data.wheel4,
                            drive_data.wheel5]
        self.__debug_print('drive data updated!\n')

    def send_cmd(self, command): # the API that get command object from front end and send it to rover
        if command.cmd_code & 0b0001:    # if it is a route update command
            self.set_new_route(command.new_route)                    # remote update

        if command.cmd_code & 0b0010:    # an arm gesture update command
            # pub.set_arm_gesture(command.new_arm) 
            # local-rover interface not implemented
            pass 

        if command.cmd_code & 0b0100:    # a speed update command
            self.set_new_speed(command.new_speed)
        
        self.__debug_print("one command sent") 
    
    def set_new_route(self, new_route): # new_route should be a list of GPSPoint
        self.route_state = [self.route_state[0]] + new_route # the start point(current pos) is reserved 
        self.set_new_target(new_route[0])

    def set_new_target(self, new_target):
        # invalid if it is not number
        if not isinstance(new_target, GPSPoint):
            raise InvalidTarget("non GPS format input")
        nav_data = NavigationMsg()
        nav_data.tar_lat = new_target.lati
        nav_data.tar_long = new_target.longt
        self.navi_pub.publish(nav_data) 
    
    def set_new_speed(self, new_speed):
        # invalid if it is not number
        if len(new_speed) != 6:
            raise InvalidSpeed("incorrect num of speed")
        if not reduce(lambda a,b: a and b, map(lambda a: a>=0 , new_speed)):
            raise InvalidSpeed("negative speed")
        drive_data = Drive()
        drive_data.wheel0 = new_speed[0]
        drive_data.wheel1 = new_speed[1]
        drive_data.wheel2 = new_speed[2]
        drive_data.wheel3 = new_speed[3]
        drive_data.wheel4 = new_speed[4]
        drive_data.wheel5 = new_speed[5]
        self.driv_pub.publish(drive_data)

    def get_notification(self):
        remark = self.remark
        self.clear_noti_buffer()    #clear notification buffer after everytime we read it.
        return remark

    def clear_noti_buffer(self):
        self.remark = ''

    def __repr__(self):
        return "this is Rover " + self.name + " !"

    def shut_down(self):
        rospy.signal_shutdown(self.name + " is off.")
