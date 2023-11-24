#!/usr/bin/env python
# coding=utf-8
import socket

import rospy

from geometry_msgs.msg import Twist

import sys, select, termios, tty ,time

local_ip = "192.168.0.100"
local_port = 10000

def shutdown():
    twist = Twist()
    twist.linear.x = 0
    twist.angular.z = 0
    pub.publish(twist)
    print ("stop")

#主函数
if __name__=="__main__":
    settings = termios.tcgetattr(sys.stdin) #获取键值初始化，读取终端相关属性
    
    rospy.init_node('turtlebot_teleop') #创建ROS节点
    rospy.on_shutdown(shutdown)
    pub = rospy.Publisher('~cmd_vel', Twist, queue_size=1) #创建速度话题发布者，'~cmd_vel'='节点名/cmd_vel'

    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    server.bind((local_ip, local_port))

    control_speed = 0 #前进后退实际控制速度
    control_turn  = 0 #转向实际控制速度
    print("---init finish--")
    s = time.time()
    try:
        while not rospy.is_shutdown():
            e = time.time()
            print("------delta = {}-----".format(e-s))
            s=e
            msg = server.recv(1024)
            data = eval(msg)
            print(data)
            control_speed = data['speed']
            control_turn = data['turn']
            twist = Twist()
            twist.linear.x = control_speed # control_speed
            twist.angular.z = control_turn #control_turn
            pub.publish(twist)  # ROS发布速度话题
    except Exception as e:
        print(e)
    # 程序结束前发布速度为0的速度话题
    finally:
        twist = Twist()
        twist.linear.x = 0
        twist.angular.z = 0
        pub.publish(twist)
