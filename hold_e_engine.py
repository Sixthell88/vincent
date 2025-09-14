import cv2
import numpy as np
import time
from threading import Thread, Event
import pydirectinput
from PIL import ImageGrab
import os

class HoldEEngine:
    """Auto Hold E Engine - Core logic"""
    
    def __init__(self, config):
        self.config = config
        self.templates = {}
        self.running = False
        self.holding_e = False
        self.screen_cache = None
        self.cache_time = 0
        self.cache_duration = 0.005
        
        # Default images to detect
        self.target_images = ['chatcay.png', 'chatgo.png', 'daoda.png']
        
    def load_templates(self, image_folder):
        """Load hold E templates"""
        loaded = 0
        for img_file in self.target_images:
            paths = [img_file, os.path.join(image_folder, img_file)]
            for path in paths:
                if os.path.exists(path):
                    img = cv2.imread(path)
                    if img is not None:
                        if self.config.get('fast_mode', True) and self.config.get('roi_scale', 0.5) < 1:
                            height, width = img.shape[:2]
                            scale = self.config.get('roi_scale', 0.5)
                            new_width = int(width * scale)
                            new_height = int(height * scale)
                            img = cv2.resize(img, (new_width, new_height))
                        self.templates[img_file] = img
                        loaded += 1
                        break
        return loaded
    
    def get_optimized_screen(self):
        """Get optimized screen capture"""
        current_time = time.time()
        if self.screen_cache is not None and (current_time - self.cache_time) < self.cache_duration:
            return self.screen_cache

        if self.config.get('use_roi', True):
            roi = self.config['roi']
            roi_x = roi['left']
            roi_y = roi['top']
            roi_w = roi['width']
            roi_h = roi['height']
            screenshot = ImageGrab.grab(bbox=(roi_x, roi_y, roi_x + roi_w, roi_y + roi_h))
        else:
            screenshot = ImageGrab.grab()

        screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        if self.config.get('fast_mode', True) and self.config.get('roi_scale', 0.5) < 1:
            height, width = screen.shape[:2]
            scale = self.config.get('roi_scale', 0.5)
            new_width = int(width * scale)
            new_height = int(height * scale)
            screen = cv2.resize(screen, (new_width, new_height))

        self.screen_cache = screen
        self.cache_time = current_time
        return screen
    
    def detect_targets(self):
        """Detect target images on screen"""
        try:
            screen = self.get_optimized_screen()
            found = False
            detected_image = None
            max_confidence = 0
            
            for img_name, template in self.templates.items():
                try:
                    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    if max_val >= self.config.get('threshold', 0.7):
                        found = True
                        if max_val > max_confidence:
                            max_confidence = max_val
                            detected_image = img_name
                except:
                    continue
            
            return found, detected_image, max_confidence
        except:
            return False, None, 0
    
    def hold_key_e(self):
        """Hold E key"""
        if not self.holding_e:
            try:
                pydirectinput.keyDown('e')
                self.holding_e = True
                return True
            except:
                return False
        return True
    
    def release_key_e(self):
        """Release E key"""
        if self.holding_e:
            try:
                pydirectinput.keyUp('e')
                self.holding_e = False
                return True
            except:
                return False
        return True
    
    def start_monitoring(self, status_callback=None, fps_callback=None):
        """Start Hold E monitoring"""
        self.running = True
        
        def monitor_loop():
            consecutive_no_detections = 0
            fps_counter = 0
            fps_time = time.time()
            
            while self.running:
                try:
                    loop_start = time.time()
                    found, detected_image, confidence = self.detect_targets()
                    
                    if found:
                        consecutive_no_detections = 0
                        response_time = (time.time() - loop_start) * 1000
                        
                        if not self.holding_e:
                            self.hold_key_e()
                            if status_callback:
                                status_callback("HOLDING", response_time, detected_image)
                    else:
                        consecutive_no_detections += 1
                        release_delay = self.config.get('release_delay', 1)
                        if self.holding_e and consecutive_no_detections > release_delay:
                            self.release_key_e()
                            if status_callback:
                                status_callback("NOT_HOLDING", 0, None)
                    
                    # Update FPS
                    fps_counter += 1
                    if time.time() - fps_time >= 1.0:
                        fps = fps_counter
                        fps_counter = 0
                        fps_time = time.time()
                        if fps_callback:
                            fps_callback(fps)
                    
                    scan_delay = self.config.get('scan_delay', 0.01)
                    time.sleep(max(0.001, scan_delay))
                except Exception as e:
                    time.sleep(0.01)
        
        self.monitor_thread = Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop Hold E monitoring"""
        self.running = False
        if self.holding_e:
            self.release_key_e()
