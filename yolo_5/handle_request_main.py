import os
import threading

import socket
import yolo_5

local_port = 9001  # 本地处理节点端口
vehicle_port = 10000  # 小车 端口
local_ip = "192.168.0.241"  # 本地处理节点IP
vehicle_ip = "192.168.0.100"  # 小车IP

frame_size = (384, 216)         # 需和通过UDP收到的图片大小保持一致，默认一致

basepath = "input/"
g_count = 0

# 处理线程，不停轮询公共队列去图片处理
class ProcessThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.scb = StatusControlBlock()
        self.ip_port = (vehicle_ip, vehicle_port)
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)

    # 发送消息
    def send(self, msg):
        print("send data", msg)
        self.client.sendto(msg.encode(), self.ip_port)

    def run(self) -> None:
        print('ProcessThread running')
        global g_count
        count = g_count
        while True:
            while g_count == count:
                pass    # 如果g_count 未增加 一直等待
            count = g_count
            path = get_path(count)
            rects = yolo_5.start(path)  # 获取图片框
            self.scb.follow_target(rects)
            data = str({"count": count,"code": 200, "speed": self.scb.control_speed, "turn": self.scb.control_turn})
            self.send(data)


class UDPServer(threading.Thread):
    def __init__(self):
        super().__init__()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        self.server.bind((local_ip, local_port))
        print("UDP server init" + local_ip + ":" + str(local_port))
        self.count = 1  # 计数器，收到的图片序号

    # 接收发来的图片
    def run(self) -> None:
        print('server running')
        global g_count
        while (True):
            data,addr = self.server.recvfrom(400000)
            path = get_path(self.count)
            write_file(path, data)
            g_count = self.count
            self.count += 1
            print('server recv data,next count = ' + str(self.count))


class StatusControlBlock:

    def __init__(self):
        self.mid_x = frame_size[0] / 2  # 图像中心x
        self.last_x = self.mid_x  # 上一次目标的中心x
        self.last_w = 0  # 上一次目标的宽度

        self.speed_max = 0.45  # 最大速度太快容易撞  可调整
        self.back_speed = -0.15  # 后退速度
        self.t = 0.4  # 两张图片的时间间隔 (s)  可调整
        self.half_rad = 0.7  # 半角弧度
        self.base_w = self.mid_x * 0.6  # 基准框宽度 (像素)
        self.bash_y = 1  # 基准距离 (m )

        self.x_l_min = self.mid_x * 0.8  # 向左转向阈值
        self.x_r_min = self.mid_x * 1.2  # 向右转向阈值
        self.x_l_max = self.mid_x * 0.2  # 向左转向阈值
        self.x_r_max = self.mid_x * 1.8  # 向右转向阈值
        self.w_b_min = self.mid_x * 0.8  # 小车后退阈值
        self.w_f_min = self.mid_x * 0.5  # 小车前进阈值

        self.control_speed = 0  # 控制前后速度
        self.control_turn = 0  # 控制转向速度

    # 根据框框的位置判定该往哪儿走
    def follow_target(self, rects):
        target = []
        num = len(rects)

        if num == 0:  # 无框
            self.last_x = self.mid_x  # 上一次目标的中心x
            self.last_w = 0
            self.control_turn = 0
            self.control_speed = 0
        elif num == 1:
            target = rects[0]
        else:
            target = self.find_target_rect(rects)

        if target:
            self.last_x = (target[1][0] + target[0][0]) / 2  # 中心x
            self.last_w = target[1][0] - target[0][0]  # 宽度
            self.tran_turn()
            self.tran_speed()

    # 计算小车转向
    def tran_turn(self):
        if self.x_l_min <= self.last_x <= self.x_r_min:
            # 不转向
            self.control_turn = 0

        elif self.last_x < self.x_l_min:
            # 左转
            turn_rad = self.half_rad * (self.x_l_min - self.last_x) / self.mid_x  # 该转动的弧度
            self.control_turn = turn_rad / self.t
        else:
            # 右转
            turn_rad = self.half_rad * (self.x_r_min - self.last_x) / self.mid_x
            self.control_turn = turn_rad / self.t
        self.control_turn /= 2

    # 计算小车速度
    def tran_speed(self):

        if self.w_f_min <= self.last_w <= self.w_b_min:
            # 不运动
            self.control_speed = 0

        elif self.last_w > self.w_b_min:
            # 小车后退
            self.control_speed = self.back_speed
        else:
            if self.control_speed <= 0.2:
                self.control_speed = 0.2
            # 小车前进
            if self.last_x <= self.x_l_min or self.last_x >= self.x_r_max:
                # 人在边上，可能只识别半个人，速度不能太快
                # self.control_speed = 0.2
                pass
            else:
                distance = self.bash_y * (self.base_w / self.last_w) - self.bash_y  # 该移动的距离
                speed = distance / self.t  # 理应速度
                if speed > self.control_speed:
                    if self.control_speed < self.speed_max:
                        self.control_speed += 0.05  # 匀变速

                else:
                    self.control_speed = speed
                print("--- caculate distance = {} , speed = {}".format(distance, speed))

    # 目标
    def find_target_rect(self, rects):
        assert len(rects) > 1
        gap = self.mid_x * 2  # 寻找和上一个点差值最小的点
        cur_rect = []
        for rect in rects:
            cur_x = (rect[1][0] + rect[0][0]) / 2
            cur_gap = abs(cur_x - self.last_x)
            if cur_gap < gap:
                cur_rect = rect
        self.last_x = (cur_rect[1][0] + cur_rect[0][0]) / 2
        return cur_rect


def get_path(count):
    return basepath + str(count) + ".jpg"


def write_file(path, data, type='wb'):
    path_dir = os.path.split(path)[0]
    if not os.path.exists(path_dir):
        os.makedirs(path_dir)
    f = open(path, type)
    f.write(data)
    f.close()


if __name__ == '__main__':
    server = UDPServer()
    server.start()
    ProcessThread().start()
    server.join()
