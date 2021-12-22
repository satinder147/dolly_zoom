import time

import cv2
import numpy as np


class Track:
    def __init__(self, first_frame, box):
        frame = first_frame
        # cv2.namedWindow("select the bounding box")
        # box = cv2.selectROI("select the bounding box", frame)
        # cv2.imshow("select the bounding box", frame)
        # print(type(box))
        # print(box)
        self.x, self.y, self.w, self.h = box
        # print(self.x, self.y, self.w, self.h)
        self.tracker = cv2.TrackerCSRT_create()
        self.tracker.init(frame, tuple(box))
        self.initial = box[2] * box[3]
        self.ind = 0

    def track(self, frame):
        (success, box) = self.tracker.update(frame)
        x, y, w, h = box
        x, y, w, h = int(x), int(y), int(w), int(h)
        self.ind += 1
        # frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        center_point = [x + w // 2, y + h // 2]
        # frame = cv2.circle(frame, (center_point[0], center_point[1]), 5, (255, 0, 0))
        # cv2.imshow("frame", frame)
        # cv2.waitKey(1)
        return self.ind, self.initial / (w * h), center_point


class DollyZoom:

    def __init__(self, video_path, skip_frames=0):

        self.smoothing_radius = 150
        self.video_path = video_path
        self.cap = cv2.VideoCapture(self.video_path)
        self.n_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.n_frames -= skip_frames
        self.skip_frames = skip_frames
        self.w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.out_path = video_path.split('.')[0] + '_stabilized' + '.mp4'
        """
        Conditions:
        1. Resolution should be atleast 720p
        2. Should we pass another parameter to say if user can compromise with quality. 
        """
        if self.w > self.h:
            # landscape
            self.out_resolution = (1280, 720)
            self.processing_resolution = (1280, 720)
        else:
            self.out_resolution = (720, 1280)
            self.processing_resolution = (720, 1280)
        self.max_zoom = self.w / self.out_resolution[0]  # Quality vs zoom compromise.

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def process(self, box=None):

        # We need to find a code that does some lossy compression.
        out = cv2.VideoWriter(self.out_path, cv2.VideoWriter_fourcc(*'MJPG'), self.fps, self.out_resolution)
        frames = []
        s = time.time()
        while 1:
            ret, frame = self.cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, self.out_resolution)
            frames.append(frame)

        frames = frames[::-1]
        frames = frames[self.skip_frames:]
        video_decoding_time = time.time() - s
        prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.resize(prev_gray, self.processing_resolution)
        s = time.time()
        transforms = np.zeros((self.n_frames, 3), np.float32)
        tracker = Track(prev_gray, box)
        zoom_details = []
        for i in range(1, self.n_frames - 1):
            # Detect feature points in previous frame
            prev_pts = cv2.goodFeaturesToTrack(prev_gray,
                                               maxCorners=200,
                                               qualityLevel=0.01,
                                               minDistance=30,
                                               blockSize=3)

            curr_gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.resize(curr_gray, self.processing_resolution)
            zoom_details.append(tracker.track(curr_gray))
            curr_pts, status, err = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, prev_pts, None)

            idx = np.where(status == 1)[0]
            prev_pts = prev_pts[idx]
            curr_pts = curr_pts[idx]

            # Find transformation matrix
            m, _ = cv2.estimateAffinePartial2D(prev_pts, curr_pts)

            # Translation
            dx = m[0, 2]
            dy = m[1, 2]

            da = np.arctan2(m[1, 0], m[0, 0])
            transforms[i] = [dx, dy, da]
            prev_gray = curr_gray

        trajectory = np.cumsum(transforms, axis=0)
        smoothed_trajectory = self.smooth(trajectory)
        difference = smoothed_trajectory - trajectory
        transforms_smooth = transforms + difference

        # Reset stream to first frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        arr_x, arr_y, centers = zip(*zoom_details)
        x, y = np.array(arr_x), np.array(arr_y)
        # plt.scatter(x, y)
        # plt.show()
        z = np.polyfit(x, y, 1)
        function = np.poly1d(z)
        # n_y = function(x)
        # plt.scatter(x, n_y)
        # plt.show()
        transform_calculation_time = time.time() - s
        s = time.time()
        rate = 2
        prev = None
        for i in range(1, self.n_frames - 1):
            frame = frames[i]
            # frame = cv2.resize(frame, (1920, 1080))
            # Extract transformations from the new transformation array
            dx = transforms_smooth[i, 0]
            dy = transforms_smooth[i, 1]
            da = transforms_smooth[i, 2]

            # Reconstruct transformation matrix accordingly to new values
            m = np.zeros((3, 3), np.float32)
            m[0, 0] = np.cos(da)
            m[0, 1] = -np.sin(da)
            m[1, 0] = np.sin(da)
            m[1, 1] = np.cos(da)
            m[0, 2] = dx
            m[1, 2] = dy
            m[2, 2] = 1
            zoom = function(i)
            if zoom >= 0:
                # print("within")
                updated_scale = 1 + zoom / 10
                if updated_scale > self.max_zoom:
                    break
                zoom_area = ((centers[i-1][0] / self.processing_resolution[0]) * self.out_resolution[0],
                             (centers[i-1][1] / self.processing_resolution[1]) * self.out_resolution[1])
                zoom_matrix = cv2.getRotationMatrix2D(zoom_area, 0, updated_scale)
                m2 = np.zeros((3, 3), np.float32)
                m2[0, 0] = zoom_matrix[0, 0]
                m2[0, 1] = zoom_matrix[0, 1]
                m2[1, 0] = zoom_matrix[1, 0]
                m2[1, 1] = zoom_matrix[1, 1]
                m2[0, 2] = zoom_matrix[0, 2]
                m2[1, 2] = zoom_matrix[1, 2]
                m2[2, 2] = 1
                m = np.dot(m, m2)
                m = m[:2, :3]
                # Apply affine wrapping to the given frame

                # if i % 180 == 1:
                #     rate *= 2
                # if i % rate == 1:
                # print("wrote")
                frame_stabilized = cv2.warpAffine(frame, m, self.out_resolution)
                out.write(frame_stabilized)

        out.release()
        video_encoding_time = time.time() - s
        return self.out_path, video_decoding_time, transform_calculation_time,\
               video_encoding_time, self.w, self.h, self.fps

    @staticmethod
    def moving_average(curve, radius):
        window_size = 2 * radius + 1
        f = np.ones(window_size)/window_size
        curve_pad = np.lib.pad(curve, (radius, radius), 'edge')
        curve_smoothed = np.convolve(curve_pad, f, mode='same')
        curve_smoothed = curve_smoothed[radius: -radius]
        return curve_smoothed

    def smooth(self, trajectory):
        smoothed_trajectory = np.copy(trajectory)
        # Filter the x, y and angle curves
        for i in range(3):
            smoothed_trajectory[:, i] = self.moving_average(trajectory[:, i],
                                                            radius=self.smoothing_radius)
        return smoothed_trajectory

    @staticmethod
    def fix_border(frame):
        s = frame.shape
        # Scale the image 4% without moving the center
        m = cv2.getRotationMatrix2D((s[1]/2, s[0]/2), 0, 1.04)
        frame = cv2.warpAffine(frame, m, (s[1], s[0]))
        return frame


if __name__ == '__main__':
    obj = DollyZoom('media/C0002.MP4', 0)
    obj.process([1, 2, 3, 4])


# Decrease disk reads
# Decrease Disk write.
# center the person
