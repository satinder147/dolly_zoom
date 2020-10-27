import os
import time
import cv2
import numpy as np


def nothing(para):
    pass


class Track:
    def __init__(self, cap, frame_number):
        for _ in range(frame_number-1):
            cap.read()
        frame = cap.read()[1]
        frame = cv2.resize(frame, (960, 540))
        cv2.namedWindow("select the bounding box")
        box = cv2.selectROI("select the bounding box",frame)
        cv2.imshow("select the bounding box", frame)
        self.x, self.y, self.w, self.h = box
        self.cap = cap
        self.tracker = cv2.TrackerCSRT_create()
        self.tracker.init(frame, box)
        self.initial = box[2]*box[3]

    def track(self):
        print("tracking started")
        arr_x = []
        arr_y = []
        ind = 0
        while 1:
            ret, frame = self.cap.read()
            if ret is False:
                break
            frame = cv2.resize(frame, (960, 540))
            (success, box) = self.tracker.update(frame)
            x, y, w, h = box
            x = int(x)
            y = int(y)
            w = int(w)
            h = int(h)
            arr_x.append(ind)
            arr_y.append(self.initial/(w*h))
            ind += 1
        print("tracking ended")
        return np.array(arr_x), np.array(arr_y)
        

class Dolly:

    def __init__(self, seconds, name):
        self.cap = cv2.VideoCapture(name)
        self.rev_name = name.split(".")[0] + '_reversed' + '.mp4'
        self.seconds = seconds
        if self.rev_name not in os.listdir(os.getcwd()):
            self.reverse_video()
        else:
            print("reversed video already present, moving on")
        self.cap = cv2.VideoCapture(self.rev_name)
        self.tracker = Track(self.cap, self.seconds)
        self.initial = None
        self.p = None
        self.w = 2560
        self.h = 1440

    def reverse_video(self):
        print("reversal start")
        out = cv2.VideoWriter(self.rev_name, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), 30, (self.w, self.h))
        frames = []
        for _ in range(self.seconds):
            self.cap.read()
        while 1:
            ret, frame = self.cap.read()
            if ret is False:
                break
            frame = cv2.resize(frame, (self.w, self.h))
            frames.append(frame)
        frames.reverse()
        for frame in frames:
            out.write(frame)
        print("reversal ended")
        out.release()

    def get_scales(self):
        x, y = self.tracker.track()
        # plt.scatter(x, y)
        # plt.show()
        z = np.polyfit(x, y, 3)
        self.p = np.poly1d(z)
        # n_y = self.p(x)
        # plt.scatter(x, n_y)
        # plt.show()

    def apply_zoom(self):
        out = cv2.VideoWriter('res.mp4', cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), 30, (self.w, self.h))
        self.cap = cv2.VideoCapture(self.rev_name)
        for _ in range(self.seconds):
            self.cap.read()
        w = self.w
        h = self.h
        frames = []
        while 1:
            ret, frame = self.cap.read()
            if ret is False:
                break
            frame = cv2.resize(frame, (w, h))
            frames.append(frame)
        cv2.namedWindow('frame')
        # cv2.createTrackbar('num', 'frame', 0, len(frames)-1, nothing)
        for (i, frame) in enumerate(frames):
            # ret, frame = self.cap.read()
            # frame = frames[i]
            # i = cv2.getTrackbarPos('num', 'frame')
            # frame = frames[i]
            # print(scale)
            scale = 1 + self.p(i) / 10  # How to decide this 10
            m = cv2.getRotationMatrix2D((w//2, h//2), 0, scale)
            frame = cv2.warpAffine(frame, m, (w, h))
            # frame = cv2.resize(frame, (640, 480))
            # cv2.imshow('frame', frame)
            # cv2.waitKey(1)
            out.write(frame)
        out.release()


if __name__ == '__main__':
    s = time.time()
    obj = Dolly(45, 'satinder.mp4')
    obj.get_scales()
    obj.apply_zoom()
    print(time.time()-s)
   

