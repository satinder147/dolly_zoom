import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from test_widerface import *


def nothing(para):
    pass


class Track:
    def __init__(self, cap, frame_number, box):
        for _ in range(frame_number):
            cap.read()
        self.cap = cap
        self.box = box
    
    def track(self):
        # Track the object
        

    

class Dolly:
    def __init__(self, seconds, name):
        self.cap = cv2.VideoCapture(name)
        self.rev_name = name.split(".")[0]+'_reversed'+'.mp4'
        self.seconds = seconds
        if self.rev_name not in os.listdir(os.getcwd()):
            self.reverse_video()
        else:
            print("reversed video already present, moving on")
        self.cap = cv2.VideoCapture(self.rev_name)
        self.per = per
        self.initial = None
        
        self.p = None

    def reverse_video(self):
        print("reversal start")
        out = cv2.VideoWriter(self.rev_name, cv2.VideoWriter_fourcc('M','J','P','G'), 30, (1920,1080))
        frames = []
        while 1:
            ret, frame = self.cap.read()
            if ret is False:
                break
            frame = cv2.resize(frame, (1920, 1080))
            frames.append(frame)
        frames.reverse()
        for frame in frames:
            out.write(frame)
        print("reversal ended")
        out.release()

    def get_scales(self):
        x = []
        y = []
        points = []
        i = 0
        frame = None
        for _ in range(self.seconds):
            frame = self.cap.read()[1]
            # cv2.imshow("frame",frame)
            # cv2.waitKey(1)
        _, self.initial = func(frame)
        while 1:
            ret, frame = self.cap.read()
            if ret is False:
                break
            if i % self.per == 0:
                point, new_scale = func(frame)
                increase = self.initial/new_scale
                x.append(i)
                y.append(increase)
            i += 1
        x = np.array(x)
        y = np.array(y)
        plt.scatter(x, y)
        plt.show()
        z = np.polyfit(x, y, 5)
        self.p = np.poly1d(z)
        n_y = self.p(x)
        plt.scatter(x, n_y)
        plt.show()

    
    def apply_zoom(self):
        self.cap = cv2.VideoCapture(self.rev_name)
        for _ in range(self.seconds):
            self.cap.read()
        w = 960
        h = 540
        frames = []
        while 1:
            ret, frame = self.cap.read()
            if ret is False:
                break
            frame = cv2.resize(frame, (w, h))
            frames.append(frame)
        i = 0
        cv2.namedWindow('frame')
        cv2.createTrackbar('num', 'frame', 0, len(frames)-1, nothing)
        while 1:
            # ret, frame = cap.read()
            i = cv2.getTrackbarPos('num', 'frame')
            frame = frames[i]
            scale = 1 + self.p(i)
            print(scale)
            # i += 1
            m = cv2.getRotationMatrix2D((w//2,h//2), 0, scale)
            frame = cv2.warpAffine(frame, m, (w, h))
            frame = cv2.resize(frame, (640, 480))
            cv2.imshow('frame', frame)
            cv2.waitKey(1)


if __name__ == '__main__':
    obj = Dolly(180, 'satinder.mp4')
    obj.get_scales()
    obj.apply_zoom()





"""
Increse speed of obtaining frames
"""