# calibrate.py - 16点homography标定，tkinter全屏目标点+光标跟随

import cv2
import numpy as np
import tkinter as tk
import threading
import time
import config
import mediapipe as mp

class Calibrator:
    def __init__(self):
        self.cap = None
        self.calib_points_cam = []
        self.calib_points_screen = []
        self.current_point_index = 0
        self.running = False
        self.root = None
        self.canvas = None
        self.latest_cam_pos = None
        self.homography = None

    def start(self):
        """启动标定流程，返回是否成功"""
        self.cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        if not self.cap.isOpened():
            print("无法打开摄像头，标定取消")
            return False

        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='black')
        self.canvas = tk.Canvas(self.root, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 生成16个目标点（4x4网格），留边距
        margin = 50
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        cols, rows = 4, 4
        self.target_points = []
        for r in range(rows):
            for c in range(cols):
                x = margin + c * (screen_w - 2*margin) / (cols-1)
                y = margin + r * (screen_h - 2*margin) / (rows-1)
                self.target_points.append((x, y))

        self.current_point_index = 0
        self.running = True

        # 相机线程
        self.camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.camera_thread.start()

        self._show_target_point()

        # 绑定鼠标点击（用于调试，实际应通过接触判定触发）
        self.root.bind('<Button-1>', self._on_click)
        self.root.mainloop()
        return self.homography is not None

    def _camera_loop(self):
        """持续检测手部指尖位置，用于光标跟随"""
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)
            if results.multi_hand_landmarks:
                tip = results.multi_hand_landmarks[0].landmark[8]
                cam_x = tip.x * config.CAMERA_WIDTH
                cam_y = tip.y * config.CAMERA_HEIGHT
                self.latest_cam_pos = (cam_x, cam_y)
                # 更新光标显示
                self.root.after(0, self._update_cursor, cam_x, cam_y)
            time.sleep(0.01)
        hands.close()
        self.cap.release()

    def _update_cursor(self, cam_x, cam_y):
        """在屏幕上显示光标（小圆点）"""
        if hasattr(self, 'cursor_id'):
            self.canvas.delete(self.cursor_id)
        screen_x = cam_x / config.CAMERA_WIDTH * self.root.winfo_screenwidth()
        screen_y = cam_y / config.CAMERA_HEIGHT * self.root.winfo_screenheight()
        self.cursor_id = self.canvas.create_oval(screen_x-5, screen_y-5, screen_x+5, screen_y+5, fill='red', outline='')

    def _show_target_point(self):
        self.canvas.delete('all')
        x, y = self.target_points[self.current_point_index]
        self.canvas.create_oval(x-15, y-15, x+15, y+15, fill='white', outline='black', width=2)
        self.canvas.create_text(x, y-30, text=f"第 {self.current_point_index+1}/{config.CALIB_POINTS} 点", fill='yellow', font=('Arial', 20))

    def _record_point(self):
        """记录当前目标点的相机坐标和屏幕坐标"""
        if not self.latest_cam_pos:
            print("尚未检测到手指，请确保手指对准摄像头")
            return
        cam_x, cam_y = self.latest_cam_pos
        screen_x, screen_y = self.target_points[self.current_point_index]
        self.calib_points_cam.append([cam_x, cam_y])
        self.calib_points_screen.append([screen_x, screen_y])
        print(f"点 {self.current_point_index+1}: cam=({cam_x:.1f},{cam_y:.1f}) -> screen=({screen_x:.1f},{screen_y:.1f})")
        self.current_point_index += 1
        if self.current_point_index >= config.CALIB_POINTS:
            self._finish_calibration()
        else:
            self._show_target_point()

    def _on_click(self, event):
        self._record_point()

    def _finish_calibration(self):
        self.running = False
        if len(self.calib_points_cam) >= 4:
            src = np.array(self.calib_points_cam, dtype=np.float32)
            dst = np.array(self.calib_points_screen, dtype=np.float32)
            self.homography, _ = cv2.findHomography(src, dst)
            np.save(config.CALIB_FILE, self.homography)
            print(f"标定完成，矩阵已保存至 {config.CALIB_FILE}")
        else:
            print("标定点不足，标定失败")
        self.root.destroy()