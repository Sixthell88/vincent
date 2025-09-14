# Core functions for AUTO SPAM and AUTO E
# This file will be hosted on GitHub as raw content
# Upload this to GitHub and get the raw URL

import cv2
import numpy as np
import mss
import time
from threading import Thread
from PIL import ImageGrab

def spam_key_core(self, key):
    """Core spam key logic"""
    try:
        while self.active_keys.get(key, False) and self.is_running:
            self.send_key(key)
            time.sleep(self.SPAM_DELAY)
    except Exception as e:
        pass

def scan_screen_core(self):
    """Core screen scanning logic"""
    detected = set()
    try:
        with mss.mss() as sct:
            screenshot = np.array(sct.grab(self.ROI))
            img_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
            
            for img_name, template in self.templates.items():
                try:
                    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(res)
                    if max_val >= self.THRESHOLD:
                        key = self.image_key_map[img_name]
                        detected.add(key)
                except:
                    continue
    except Exception as e:
        self.error_count += 1
        if self.error_count > self.max_errors:
            self.stop_tool()
    
    return detected

def spam_manager_core(self):
    """Core spam manager logic"""
    while self.is_running and not self.stop_event.is_set():
        try:
            detected_keys = self.scan_screen()
            
            for key in detected_keys:
                if not self.active_keys.get(key, False):
                    self.active_keys[key] = True
                    thread = Thread(target=self.spam_key, args=(key,), daemon=True)
                    thread.start()
                    self.key_threads[key] = thread
            
            for key in list(self.active_keys.keys()):
                if self.active_keys[key] and key not in detected_keys:
                    self.active_keys[key] = False
            
            if detected_keys:
                active_list = [k.upper() for k in detected_keys]
                self.root.after(0, lambda: self.active_keys_label.config(
                    text=f"Active: {', '.join(active_list)}", fg='#2ecc71'))
            else:
                self.root.after(0, lambda: self.active_keys_label.config(
                    text="Active: None", fg='#95a5a6'))
            
            time.sleep(self.SCAN_DELAY)
        except Exception as e:
            self.error_count += 1
            if self.error_count > self.max_errors:
                self.stop_tool()
                break
            time.sleep(0.1)

def hold_e_manager_core(self):
    """Core hold E manager logic"""
    consecutive_no_detections = 0
    fps_counter = 0
    fps_time = time.time()
    
    while self.hold_e_running and self.auto_hold_e_enabled:
        try:
            loop_start = time.time()
            screen = self.get_optimized_screen()
            found = False
            detected_image = None
            max_confidence = 0
            
            for img_name, template in self.hold_e_templates.items():
                try:
                    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    if max_val >= self.hold_e_threshold:
                        found = True
                        if max_val > max_confidence:
                            max_confidence = max_val
                            detected_image = img_name
                except:
                    continue
            
            if found:
                consecutive_no_detections = 0
                response_time = (time.time() - loop_start) * 1000
                self.root.after(0, lambda: self.response_label.config(
                    text=f"Response: {response_time:.0f}ms", fg='#2ecc71'))
                
                if not self.holding_e:
                    self.hold_key_e()
            else:
                consecutive_no_detections += 1
                if self.holding_e and consecutive_no_detections > self.hold_e_release_delay:
                    self.release_key_e()
            
            fps_counter += 1
            if time.time() - fps_time >= 1.0:
                fps = fps_counter
                fps_counter = 0
                fps_time = time.time()
                fps_color = '#2ecc71' if fps >= 60 else '#f39c12' if fps >= 30 else '#e74c3c'
                self.root.after(0, lambda: self.fps_label.config(text=f"FPS: {fps}", fg=fps_color))
            
            time.sleep(max(0.001, self.hold_e_scan_delay))
        except Exception as e:
            time.sleep(0.01)

def get_optimized_screen_core(self):
    """Core optimized screen capture"""
    current_time = time.time()
    if self.screen_cache is not None and (current_time - self.cache_time) < self.cache_duration:
        return self.screen_cache

    if self.hold_e_use_roi:
        roi_x = self.ROI['left']
        roi_y = self.ROI['top']
        roi_w = self.ROI['width']
        roi_h = self.ROI['height']
        screenshot = ImageGrab.grab(bbox=(roi_x, roi_y, roi_x + roi_w, roi_y + roi_h))
    else:
        screenshot = ImageGrab.grab()

    screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    if self.hold_e_fast_mode and self.hold_e_roi_scale < 1:
        height, width = screen.shape[:2]
        new_width = int(width * self.hold_e_roi_scale)
        new_height = int(height * self.hold_e_roi_scale)
        screen = cv2.resize(screen, (new_width, new_height))

    self.screen_cache = screen
    self.cache_time = current_time
    return screen
