# config.py - 集中配置参数

# 相机设置
CAMERA_INDEX = 0                 # 笔记本内置摄像头索引
CAMERA_WIDTH = 640               # 实际使用分辨率
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

# MediaPipe 设置
MODEL_COMPLEXITY = 0             # 0 = lite 模型
MIN_DETECTION_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5
MAX_HANDS = 2                    # 最多追踪手数

# VMulti 虚拟触屏设置
VMULTI_DLL_PATH = "vmulticlient.dll"   # 根据实际 DLL 文件名修改
SCREEN_WIDTH = 1920              # 电视分辨率（根据实际调整）
SCREEN_HEIGHT = 1080

# 标定设置
CALIB_POINTS = 16                # 4x4 网格
CALIB_FILE = "calib.npy"         # 标定矩阵保存文件

# 接触判定参数
TOUCH_DISTANCE_THRESHOLD = 0.05  # 指尖与关节距离阈值
DEBOUNCE_FRAMES = 2              # 去抖帧数

# 动态可调参数（通过 socket set 命令修改）
FPS_LIMIT = 30                   # 帧率上限
PALM_ERASE_ENABLED = True        # 手掌擦除开关