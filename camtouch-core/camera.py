# camera.py - 主控制器：相机循环、手势识别、VMulti上报

import cv2
import mediapipe as mp
import numpy as np
import time
import threading
import ctypes
import config

class VMultiClient:
    """VMulti 虚拟 HID 客户端封装（需根据实际 DLL 调整）"""
    def __init__(self):
        try:
            self.dll = ctypes.WinDLL(config.VMULTI_DLL_PATH)
            # 假设 DLL 提供以下函数（根据实际驱动接口修改）
            # 这里仅为示例，实际需根据 VMulti 驱动文档调整
            self.dll.vmulti_open.restype = ctypes.c_void_p
            self.dll.vmulti_close.argtypes = [ctypes.c_void_p]
            self.dll.vmulti_update.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                               ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                               ctypes.c_int, ctypes.c_int]
            self.handle = self.dll.vmulti_open()
            self.connected = self.handle is not None
            if not self.connected:
                print("VMulti 连接失败")
        except Exception as e:
            print(f"VMulti DLL 加载失败: {e}")
            self.connected = False

    def send_touch(self, contact_id, x, y, is_pressed, width=60, height=60, confidence=1.0):
        """上报单个触点状态（坐标归一化 0~1）"""
        if not self.connected:
            return
        # 映射到 0~65535
        x_scaled = int(x * 65535)
        y_scaled = int(y * 65535)
        w_scaled = int(width * 100)   # 示例缩放
        h_scaled = int(height * 100)
        conf = int(confidence * 255)
        pressed = 1 if is_pressed else 0
        # 实际调用（根据 DLL 函数签名调整）
        # self.dll.vmulti_update(self.handle, contact_id, x_scaled, y_scaled,
        #                        w_scaled, h_scaled, conf, pressed)
        # 调试输出
        print(f"上报: ID={contact_id}, x={x:.2f}, y={y:.2f}, pressed={is_pressed}, conf={confidence}")

    def close(self):
        if self.connected:
            # self.dll.vmulti_close(self.handle)
            self.connected = False


class TouchScreenController:
    """主控制器：相机循环、手势识别、触控上报"""
    def __init__(self):
        self.calib_matrix = None
        self.vmulti = VMultiClient()
        self.running_event = threading.Event()
        self.running_event.clear()
        self.thread = None
        self.cap = None
        self.fps = 0
        self.hand_count = 0

        # MediaPipe Hands 初始化
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=config.MAX_HANDS,
            model_complexity=config.MODEL_COMPLEXITY,
            min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE
        )

        # 触点状态跟踪 {contact_id: {'x':.., 'y':.., 'pressed':.., 'debounce':..}}
        self.active_contacts = {}

    def load_calibration(self, filepath=config.CALIB_FILE):
        """加载标定矩阵"""
        try:
            self.calib_matrix = np.load(filepath)
            print(f"标定矩阵已加载: {filepath}")
            return True
        except:
            print("未找到标定文件，请先校准")
            return False

    def start(self):
        """启动触控主循环（若未运行）"""
        if self.thread and self.thread.is_alive():
            return
        self.running_event.set()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("触控已启动")

    def stop(self):
        """停止触控主循环"""
        self.running_event.clear()
        if self.thread:
            self.thread.join(timeout=2)
        self._release_all_contacts()
        if self.cap:
            self.cap.release()
            self.cap = None
        print("触控已停止")

    def start_calibration(self):
        """进入标定模式（在新线程中运行）"""
        threading.Thread(target=self._run_calibration, daemon=True).start()

    def _run_calibration(self):
        from calibrate import Calibrator
        calib = Calibrator()
        calib.start()
        self.load_calibration()

    def get_status(self):
        """返回状态信息"""
        return {
            "fps": round(self.fps, 1),
            "status": "running" if self.running_event.is_set() else "stopped",
            "hands": self.hand_count
        }

    def _init_camera(self):
        """初始化摄像头，失败返回 False"""
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
        return self.cap.isOpened()

    def _run_loop(self):
        """主循环：持续读取摄像头、处理手势、上报触点"""
        # 初始化相机
        if not self._init_camera():
            print("相机初始化失败，尝试重连...")
            while self.running_event.is_set() and not self._init_camera():
                time.sleep(1)
        if not self.running_event.is_set():
            return

        frame_count = 0
        last_time = time.time()

        while self.running_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                print("相机读取失败，尝试重连...")
                self._release_all_contacts()
                if not self._init_camera():
                    time.sleep(0.5)
                    continue
                else:
                    continue

            # 处理帧
            self._process_frame(frame)

            # 计算 FPS
            frame_count += 1
            elapsed = time.time() - last_time
            if elapsed >= 1.0:
                self.fps = frame_count / elapsed
                frame_count = 0
                last_time = time.time()

            # 帧率限制
            if config.FPS_LIMIT > 0:
                sleep_time = 1.0 / config.FPS_LIMIT - (time.time() - last_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def _process_frame(self, frame):
        """处理一帧图像"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        rgb.flags.writeable = True

        if not results.multi_hand_landmarks:
            self.hand_count = 0
            self._release_all_contacts()
            return

        self.hand_count = len(results.multi_hand_landmarks)

        detected_contacts = {}
        contact_id = 0
        for hand_landmarks in results.multi_hand_landmarks:
            if contact_id >= 2:  # 最多两个触点
                break
            # 获取食指指尖 (8) 和中指指尖 (12)
            index_tip = hand_landmarks.landmark[8]
            middle_tip = hand_landmarks.landmark[12]

            # 接触判定：指尖与对应近端关节的距离
            index_mcp = hand_landmarks.landmark[5]
            middle_mcp = hand_landmarks.landmark[9]

            dist_index = np.sqrt((index_tip.x - index_mcp.x)**2 + (index_tip.y - index_mcp.y)**2 + (index_tip.z - index_mcp.z)**2)
            dist_middle = np.sqrt((middle_tip.x - middle_mcp.x)**2 + (middle_tip.y - middle_mcp.y)**2 + (middle_tip.z - middle_mcp.z)**2)

            index_pressed = dist_index < config.TOUCH_DISTANCE_THRESHOLD
            middle_pressed = dist_middle < config.TOUCH_DISTANCE_THRESHOLD

            # 优先使用食指作为触点0，中指作为触点1
            if contact_id == 0:
                cam_x, cam_y = index_tip.x, index_tip.y
                pressed = index_pressed
            else:
                cam_x, cam_y = middle_tip.x, middle_tip.y
                pressed = middle_pressed

            # 坐标映射
            if self.calib_matrix is not None:
                pt_cam = np.array([cam_x * config.CAMERA_WIDTH, cam_y * config.CAMERA_HEIGHT, 1.0])
                pt_screen = self.calib_matrix @ pt_cam
                screen_x = pt_screen[0] / pt_screen[2] / config.SCREEN_WIDTH
                screen_y = pt_screen[1] / pt_screen[2] / config.SCREEN_HEIGHT
            else:
                screen_x, screen_y = cam_x, cam_y  # 无标定时使用相机坐标（仅调试）

            detected_contacts[contact_id] = (screen_x, screen_y, pressed)
            contact_id += 1

        # 手掌擦除检测（简化示例，可根据需要扩展）
        if config.PALM_ERASE_ENABLED and len(results.multi_hand_landmarks) > 0:
            # 可以添加判断手掌张开的逻辑，并上报擦除事件
            pass

        self._update_contacts(detected_contacts)

    def _update_contacts(self, detected_contacts):
        """更新触点状态并上报"""
        # 释放未检测到的触点
        for cid in list(self.active_contacts.keys()):
            if cid not in detected_contacts:
                if self.active_contacts[cid]['pressed']:
                    self.vmulti.send_touch(cid, self.active_contacts[cid]['x'],
                                           self.active_contacts[cid]['y'], False)
                del self.active_contacts[cid]

        # 更新检测到的触点
        for cid, (x, y, pressed) in detected_contacts.items():
            if cid not in self.active_contacts:
                self.active_contacts[cid] = {'x': x, 'y': y, 'pressed': pressed, 'debounce': 0}
                self.vmulti.send_touch(cid, x, y, pressed)
            else:
                state = self.active_contacts[cid]
                state['x'] = x
                state['y'] = y
                if pressed == state['pressed']:
                    state['debounce'] = 0
                else:
                    state['debounce'] += 1
                    if state['debounce'] >= config.DEBOUNCE_FRAMES:
                        state['pressed'] = pressed
                        state['debounce'] = 0
                        self.vmulti.send_touch(cid, x, y, pressed)
                if state['pressed']:
                    # 持续上报位置（模拟移动）
                    self.vmulti.send_touch(cid, x, y, True)

    def _release_all_contacts(self):
        """释放所有活动触点"""
        for cid, state in self.active_contacts.items():
            if state['pressed']:
                self.vmulti.send_touch(cid, state['x'], state['y'], False)
        self.active_contacts.clear()