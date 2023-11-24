# 显示图像
import cv2  # 导入从cv2模块

path = './output/'

total_num = 100  # 总共帧数

rate = 3    # 每秒播放的帧数

for i in range(total_num):
    image = cv2.imread("{}/{}.jpg".format(path, i))  # 读取1.jpg图像
    cv2.imshow("image", image)  # 显示图像
    cv2.waitKey(1000//3)  # 默认为0，无限等待

cv2.destroyAllWindows()  # 释放所有窗口
