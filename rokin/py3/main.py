import os
import time
import socket
import cv2
import numpy as np

local_ip = "192.168.0.100"  # 本小车ip
remote_ip = "192.168.0.241"  # pc的ip
remote_port = 9001
frame_gap = 1 # 每隔多少取一帧

# 此代码运行在小车上
# 作用是不停从摄像头获取图片，发送给pc处理

class UDPClient:
    def __init__(self, ip, port):
        self.ip_port = (ip, port)
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)

    # 发送消息
    def send(self, msg):
        self.client.sendto(msg, self.ip_port)

# 每隔times帧取一帧
def read_times(cap, times):
    for _ in range(times):
        cap.read()
    return cap.read()

# 给frame编码成jpg格式发送
def img_encode(img, img_type='.jpg'):
    encode = cv2.imencode(img_type, img)[1].tobytes()
    data_encode = np.array(encode)
    str_encode = data_encode.tobytes()
    return str_encode

client = UDPClient(remote_ip, remote_port)  # 连接本地client节点

cap = cv2.VideoCapture(0)  # 从摄像头获取视频流
# 注意：默认用的摄像头是1920 * 1080 的，
# 若不是，设置像素cap.set(3, 1920)，cap.set(4, 1080)
# 若不是16:9，下面的resize也设置成对应比例

count = 1   # test rate
while True:
    a = time.time()
    ret, frame = cap.read()
    b = time.time()
    print("read times = " + str(b-a))
    if ret:
        frame = cv2.resize(frame,(384,216)) # 源frame太大，UDP发不了，进行对应比例压缩，默认是16:9 
        data = img_encode(frame)
        client.send(data)
        print('count = ' + str(count))
        count+=1