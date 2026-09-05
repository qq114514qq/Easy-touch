# main.py - 程序入口

import camera
import socket_server
import time

def main():
    controller = camera.TouchScreenController()
    server = socket_server.SocketServer(controller)
    server.start()
    print("camtouch-core 已启动，等待命令...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        controller.stop()

if __name__ == "__main__":
    main()