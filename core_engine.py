import cv2
import numpy as np
import mss
import time
import os
from threading import Thread, Lock, Event
import ctypes
from ctypes import wintypes
import win32api
import win32con
import pyautogui
import pydirectinput
from PIL import ImageGrab
import json

class AutoEngine:
    """Core automation engine - Main logic"""
    
    def __init__(self, config):
        self.config = config
        self.templates = {}
        self.image_key_map = {}
        self.active_keys = {}
        self.key_threads = {}
        self.is_running = False
        self.stop_event = Event()
        self.error_count = 0
        self.max_errors = 10
        
        # VK Codes for key sending
        self.VK_CODES = {
            'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46, 'g': 0x47, 'h': 0x48, 
            'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 
            'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 
            'y': 0x59, 'z': 0x5A
        }
        
        pyautogui.FAILSAFE = False
        pydirectinput.FAILSAFE = False
    
    def load_templates(self, image_folder, supported_keys):
        """Load spam key templates"""
        count = 0
        for key in supported_keys:
            filename = f"{key}.png"
            path = os.path.join(image_folder, filename)
            if os.path.exists(path):
                template = cv2.imread(path, 0)
                if template is not None:
                    self.image_key_map[filename] = key.lower()
                    self.templates[filename] = template
                    count += 1
        return count
    
    def send_key_directinput(self, key):
        """Send key using DirectInput"""
        try:
            pydirectinput.press(key)
        except:
            self.send_key_win32(key)
    
    def send_key_win32(self, key):
        """Send key using Win32 API"""
        try:
            vk_code = self.VK_CODES.get(key.lower(), ord(key.upper()))
            win32api.keybd_event(vk_code, 0, 0, 0)
            time.sleep(self.config['key_press_duration'])
            win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)
        except:
            pass
    
    def send_key_sendinput(self, key):
        """Send key using SendInput"""
        try:
            PUL = ctypes.POINTER(ctypes.c_ulong)
            
            class KeyBdInput(ctypes.Structure):
                _fields_ = [("wVk", ctypes.c_ushort),
                           ("wScan", ctypes.c_ushort),
                           ("dwFlags", ctypes.c_ulong),
                           ("time", ctypes.c_ulong),
                           ("dwExtraInfo", PUL)]

            class HardwareInput(ctypes.Structure):
                _fields_ = [("uMsg", ctypes.c_ulong),
                           ("wParamL", ctypes.c_short),
                           ("wParamH", ctypes.c_ushort)]

            class MouseInput(ctypes.Structure):
                _fields_ = [("dx", ctypes.c_long),
                           ("dy", ctypes.c_long),
                           ("mouseData", ctypes.c_ulong),
                           ("dwFlags", ctypes.c_ulong),
                           ("time", ctypes.c_ulong),
                           ("dwExtraInfo", PUL)]

            class Input_I(ctypes.Union):
                _fields_ = [("ki", KeyBdInput),
                           ("mi", MouseInput),
                           ("hi", HardwareInput)]

            class Input(ctypes.Structure):
                _fields_ = [("type", ctypes.c_ulong),
                           ("ii", Input_I)]

            vk_code = self.VK_CODES.get(key.lower(), ord(key.upper()))
            extra = ctypes.c_ulong(0)
            ii_ = Input_I()
            ii_.ki = KeyBdInput(vk_code, 0x48, 0, 0, ctypes.pointer(extra))
            x = Input(ctypes.c_ulong(1), ii_)
            ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
            
            time.sleep(self.config['key_press_duration'])
            
            ii_.ki = KeyBdInput(vk_code, 0x48, 0x0002, 0, ctypes.pointer(extra))
            x = Input(ctypes.c_ulong(1), ii_)
            ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
        except:
            pass
    
    def send_key_pyautogui(self, key):
        """Send key using PyAutoGUI"""
        try:
            pyautogui.press(key)
        except:
            pass
    
    def send_key(self, key):
        """Send key using selected method"""
        method = self.config.get('input_method', 'win32')
        if method == "directinput":
            self.send_key_directinput(key)
        elif method == "win32":
            self.send_key_win32(key)
        elif method == "sendinput":
            self.send_key_sendinput(key)
        else:
            self.send_key_pyautogui(key)
    
    def scan_screen(self):
        """Scan screen for templates"""
        detected = set()
        try:
            roi = self.config['roi']
            with mss.mss() as sct:
                screenshot = np.array(sct.grab(roi))
                img_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
                
                for img_name, template in self.templates.items():
                    try:
                        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(res)
                        if max_val >= self.config['threshold']:
                            key = self.image_key_map[img_name]
                            detected.add(key)
                    except:
                        continue
        except Exception as e:
            self.error_count += 1
            if self.error_count > self.max_errors:
                self.is_running = False
        
        return detected
    
    def spam_key(self, key):
        """Spam individual key"""
        try:
            while self.active_keys.get(key, False) and self.is_running:
                self.send_key(key)
                time.sleep(self.config['spam_delay'])
        except Exception as e:
            pass
    
    def start_spam(self, callback=None):
        """Start spam detection"""
        self.is_running = True
        self.stop_event.clear()
        self.error_count = 0
        
        def spam_manager():
            while self.is_running and not self.stop_event.is_set():
                try:
                    detected_keys = self.scan_screen()
                    
                    # Start spam for new keys
                    for key in detected_keys:
                        if not self.active_keys.get(key, False):
                            self.active_keys[key] = True
                            thread = Thread(target=self.spam_key, args=(key,), daemon=True)
                            thread.start()
                            self.key_threads[key] = thread
                    
                    # Stop spam for keys no longer detected
                    for key in list(self.active_keys.keys()):
                        if self.active_keys[key] and key not in detected_keys:
                            self.active_keys[key] = False
                    
                    # Callback for UI updates
                    if callback:
                        callback(detected_keys)
                    
                    time.sleep(self.config['scan_delay'])
                except Exception as e:
                    self.error_count += 1
                    if self.error_count > self.max_errors:
                        self.is_running = False
                        break
                    time.sleep(0.1)
        
        self.main_thread = Thread(target=spam_manager, daemon=True)
        self.main_thread.start()
    
    def stop_spam(self):
        """Stop spam detection"""
        self.is_running = False
        self.stop_event.set()
        
        for key in list(self.active_keys.keys()):
            self.active_keys[key] = False
