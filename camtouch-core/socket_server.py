# socket_server.py - TCP Socket 服务端

import socket
import threading
import json
import time
import config

class SocketServer:
    """TCP Socket 服务器，监听 127.0.0.1:8765，接收 JSON 命令并回传状态"""
    def __init__(self, controller, host='127.0.0.1', port=8765):
        self.controller = controller
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.running = False
        self.thread = None
        self.status_thread = None

    def start(self):
        """启动服务器（独立线程）"""
        if self.thread and self.thread.is_alive():
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        self.status_thread = threading.Thread(target=self._status_loop, daemon=True)
        self.status_thread.start()

    def stop(self):
        """停止服务器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if self.client_socket:
            self.client_socket.close()
        if self.thread:
            self.thread.join(timeout=1)

    def _run_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"Socket server listening on {self.host}:{self.port}")

        while self.running:
            try:
                self.client_socket, addr = self.server_socket.accept()
                print(f"Client connected from {addr}")
                self._handle_client(self.client_socket)
            except OSError:
                break
            except Exception as e:
                print(f"Socket server error: {e}")
                time.sleep(1)

    def _handle_client(self, client_socket):
        buffer = b''
        while self.running:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    line = line.strip()
                    if line:
                        self._process_command(line.decode('utf-8'))
            except ConnectionResetError:
                break
            except Exception as e:
                print(f"Error receiving data: {e}")
                break
        client_socket.close()

    def _process_command(self, json_str):
        try:
            cmd = json.loads(json_str)
            action = cmd.get('action')
            print(f"Received command: {cmd}")

            if action == 'start':
                self.controller.start()
                self._send_response({"result": "ok", "action": "start"})
            elif action == 'stop':
                self.controller.stop()
                self._send_response({"result": "ok", "action": "stop"})
            elif action == 'calibrate':
                threading.Thread(target=self.controller.start_calibration, daemon=True).start()
                self._send_response({"result": "ok", "action": "calibrate"})
            elif action == 'set':
                key = cmd.get('key')
                value = cmd.get('value')
                self._set_parameter(key, value)
                self._send_response({"result": "ok", "action": "set", "key": key, "value": value})
            else:
                self._send_response({"result": "error", "message": f"Unknown action: {action}"})
        except json.JSONDecodeError:
            self._send_response({"result": "error", "message": "Invalid JSON"})
        except Exception as e:
            self._send_response({"result": "error", "message": str(e)})

    def _set_parameter(self, key, value):
        if key == 'fps':
            config.FPS_LIMIT = int(value)
        elif key == 'palm_erase':
            config.PALM_ERASE_ENABLED = bool(value)
        else:
            print(f"Unknown parameter: {key}")

    def _send_response(self, data):
        if self.client_socket:
            try:
                msg = json.dumps(data) + '\n'
                self.client_socket.sendall(msg.encode('utf-8'))
            except:
                pass

    def _status_loop(self):
        """每秒回传状态"""
        while self.running:
            if self.client_socket:
                status = self.controller.get_status()
                self._send_response(status)
            time.sleep(1)