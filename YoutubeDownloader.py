"""
╔══════════════════════════════════════════════════════╗
║          YT-GRABBER :: H4CK3R Edition v4.0           ║
║          Self-Updating Binary Edition                ║
╚══════════════════════════════════════════════════════╝

Принцип: программа сама скачивает свежие yt-dlp и ffmpeg с GitHub.
Всегда актуально, работает и из .py и из .exe.
"""

import customtkinter as ctk
import threading
import os
import sys
import subprocess
import platform
import math
import re
import json
import zipfile
import shutil
import stat
import requests
from pathlib import Path
from tkinter import filedialog, messagebox, Canvas
from datetime import datetime

# ═══════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════

if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent.resolve()

DOWNLOAD_DIR = APP_DIR / "downloads"
BIN_DIR = APP_DIR / "bin"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
BIN_DIR.mkdir(parents=True, exist_ok=True)

COOKIES_FILE = APP_DIR / "cookies.txt"
VERSION_CACHE = BIN_DIR / ".version_cache.json"

SYSTEM = platform.system()

COLORS = {
    "bg_dark":    "#0a0a0f", "bg_card":    "#12121a", "bg_input":   "#1a1a2e",
    "accent":     "#00ff9f", "accent_dim":  "#00cc7a", "secondary":  "#00d4ff",
    "danger":     "#ff3860", "warning":     "#ffdd57", "success":    "#00ff9f",
    "text":       "#e0e0e0", "text_dim":    "#6a6a8a", "border":     "#2a2a3e",
}


# ═══════════════════════════════════════════════════════
# ПРОГРЕСС-БАР (такой же как раньше)
# ═══════════════════════════════════════════════════════

class AnimatedProgressBar(ctk.CTkFrame):
    def __init__(self, master, height=16, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.height = height
        self.progress = 0.0
        self.target_progress = 0.0
        self.scanner_pos = 0.0
        self.pulse_phase = 0.0
        self.is_animating = False
        self.is_complete = False
        self.is_indeterminate = False
        self.fill_start, self.fill_mid, self.fill_end = "#00d4ff", "#00ff9f", "#b24bf3"
        
        self.canvas = Canvas(self, height=self.height, bg=COLORS["bg_card"], highlightthickness=0, bd=0)
        self.canvas.pack(fill="x", pady=2)
        self.canvas.bind("<Configure>", lambda e: self._render())
        self._render()
    
    def set(self, v):
        self.target_progress = max(0.0, min(1.0, v))
        if not self.is_animating: self._start()
    
    def start_indeterminate(self):
        self.is_indeterminate = True
        if not self.is_animating: self._start()
    
    def stop_indeterminate(self): self.is_indeterminate = False
    
    def complete(self):
        self.is_complete = True
        self.target_progress = 1.0
        if not self.is_animating: self._start()
    
    def reset(self):
        self.progress = self.target_progress = 0.0
        self.is_complete = self.is_indeterminate = False
        self._render()
    
    def _start(self):
        self.is_animating = True
        self._animate()
    
    def _animate(self):
        if not self.is_animating: return
        if not self.is_indeterminate:
            d = self.target_progress - self.progress
            self.progress += d * 0.15 if abs(d) > 0.001 else 0
            if abs(d) <= 0.001: self.progress = self.target_progress
        self.scanner_pos = (self.scanner_pos + 0.02) % 1.0
        self.pulse_phase += 0.08
        self._render()
        if abs(self.progress - self.target_progress) > 0.001 or self.is_indeterminate or self.is_complete:
            self.after(16, self._animate)
        else: self.is_animating = False
    
    def _render(self):
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 10: return
        r = h // 2
        ip = 2
        self._rrect(0, 0, w, h, r, COLORS["bg_input"])
        self._rrect(ip, ip, w-ip, h-ip, r-ip, "#0d0d15")
        
        if self.is_indeterminate:
            gw = w * 0.25
            xs = int(self.scanner_pos * (w + gw)) - gw
            xs, xe = max(ip, xs), min(w-ip, xs + gw)
            if xe > xs: self._gradient(xs, ip, xe, h-ip, r-ip)
        else:
            fw = int((w - ip*2) * self.progress)
            if fw > 0:
                self._gradient(ip, ip, ip + fw, h-ip, r-ip)
                if self.progress < 1.0 and fw > 5:
                    self._glow(ip + fw, ip, h-ip, 0.5 + 0.5 * math.sin(self.pulse_phase))
        
        if self.is_complete and self.progress >= 0.99:
            pa = 0.3 + 0.3 * math.sin(self.pulse_phase * 2)
            self._rrect(0, 0, w, h, r, self._blend(COLORS["bg_card"], COLORS["accent"], pa))
        
        for i in range(h // 3):
            self.canvas.create_line(4, 2+i, w-4, 2+i, fill=self._blend(COLORS["bg_dark"], "#ffffff", 0.08 * (1 - i/(h//3))))
    
    def _rrect(self, x1, y1, x2, y2, r, c):
        r = min(r, (x2-x1)//2, (y2-y1)//2)
        if r < 1:
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=c, outline=""); return
        pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2, x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        self.canvas.create_polygon(pts, fill=c, outline="", smooth=True)
    
    def _gradient(self, x1, y1, x2, y2, r):
        w = x2 - x1
        if w <= 0: return
        steps = max(1, w // 2)
        sw = w / steps
        for i in range(steps):
            t = i / steps
            c = self._lerp(self.fill_start, self.fill_mid, t*2) if t < 0.5 else self._lerp(self.fill_mid, self.fill_end, (t-0.5)*2)
            sx, ex = x1 + int(i*sw), x1 + int((i+1)*sw)
            if i == 0: self._pleft(sx, y1, ex, y2, r, c)
            elif i == steps-1: self._pright(sx, y1, ex, y2, r, c)
            else: self.canvas.create_rectangle(sx, y1, ex, y2, fill=c, outline="")
    
    def _pleft(self, x1, y1, x2, y2, r, c):
        r = min(r, (x2-x1)//2)
        pts = [x1+r,y1, x2,y1, x2,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        self.canvas.create_polygon(pts, fill=c, outline="", smooth=True)
    
    def _pright(self, x1, y1, x2, y2, r, c):
        r = min(r, (x2-x1)//2)
        pts = [x1,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2, x2-r,y2, x1,y2]
        self.canvas.create_polygon(pts, fill=c, outline="", smooth=True)
    
    def _lerp(self, c1, c2, t):
        r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
        r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
        return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"
    
    def _glow(self, x, y1, y2, i):
        for j in range(8):
            self.canvas.create_line(x+j*2, y1, x+j*2, y2, fill=self._blend(COLORS["bg_dark"], COLORS["accent"], i*(1-j/8)), width=2)
        self.canvas.create_oval(x-3, (y1+y2)//2-3, x+3, (y1+y2)//2+3, fill="#ffffff", outline="")
    
    def _blend(self, c1, c2, a):
        r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
        r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
        return f"#{int(r1+(r2-r1)*a):02x}{int(g1+(g2-g1)*a):02x}{int(b1+(b2-b1)*a):02x}"


# ═══════════════════════════════════════════════════════
# МЕНЕДЖЕР БИНАРНИКОВ (yt-dlp + ffmpeg)
# ═══════════════════════════════════════════════════════

class BinManager:
    """Скачивает и обновляет yt-dlp и ffmpeg с GitHub"""
    
    YTDLP_RELEASES_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
    
    # URL для скачивания ffmpeg (готовые сборки)
    FFMPEG_URLS = {
        "Windows": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        "Darwin":  "https://evermeet.cx/ffmpeg/getrelease/zip",  # macOS
        "Linux":   "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
    }
    
    def __init__(self):
        self.ytdlp_path = BIN_DIR / ("yt-dlp.exe" if SYSTEM == "Windows" else "yt-dlp")
        self.ffmpeg_path = BIN_DIR / ("ffmpeg.exe" if SYSTEM == "Windows" else "ffmpeg")
        self._cache = self._load_cache()
    
    # ── Кэш версий (чтобы не дёргать GitHub каждый запуск) ──
    
    def _load_cache(self):
        try:
            if VERSION_CACHE.exists():
                return json.loads(VERSION_CACHE.read_text(encoding="utf-8"))
        except: pass
        return {}
    
    def _save_cache(self):
        try:
            VERSION_CACHE.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")
        except: pass
    
    def _should_check_update(self, tool):
        """Проверять не чаще раза в 6 часов"""
        last = self._cache.get(f"{tool}_check")
        if not last: return True
        try:
            last_dt = datetime.fromisoformat(last)
            return (datetime.now() - last_dt).total_seconds() > 6 * 3600
        except: return True
    
    # ── Проверка наличия и версий ──
    
    def has_ytdlp(self):
        return self.ytdlp_path.exists()
    
    def has_ffmpeg(self):
        return self.ffmpeg_path.exists()
    
    def get_local_ytdlp_version(self):
        """Получить версию локального yt-dlp"""
        if not self.has_ytdlp(): return None
        try:
            r = subprocess.run([str(self.ytdlp_path), "--version"], 
                             capture_output=True, text=True, timeout=10)
            return r.stdout.strip() if r.returncode == 0 else None
        except: return None
    
    def get_latest_ytdlp_version(self):
        """Последняя версия с GitHub"""
        try:
            r = requests.get(self.YTDLP_RELEASES_API, timeout=10)
            if r.status_code == 200:
                return r.json().get("tag_name")
        except: pass
        return None
    
    def needs_ytdlp_update(self):
        """Нужно ли обновлять yt-dlp"""
        if not self.has_ytdlp():
            return True, None, None
        
        if not self._should_check_update("ytdlp"):
            # Используем кэш
            local = self._cache.get("ytdlp_local")
            latest = self._cache.get("ytdlp_latest")
            if local and latest:
                return local != latest, local, latest
            return False, local, latest
        
        local = self.get_local_ytdlp_version()
        latest = self.get_latest_ytdlp_version()
        
        # Обновляем кэш
        self._cache["ytdlp_check"] = datetime.now().isoformat()
        self._cache["ytdlp_local"] = local
        self._cache["ytdlp_latest"] = latest
        self._save_cache()
        
        if not local or not latest:
            return False, local, latest
        
        return local != latest, local, latest
    
    # ── Скачивание yt-dlp ──
    
    def download_ytdlp(self, progress_callback=None):
        """Скачать свежий yt-dlp с GitHub"""
        try:
            r = requests.get(self.YTDLP_RELEASES_API, timeout=10)
            if r.status_code != 200:
                return False, "Не удалось получить список релизов"
            
            data = r.json()
            version = data.get("tag_name", "unknown")
            
            # Выбираем нужный asset
            if SYSTEM == "Windows":
                asset_name = "yt-dlp.exe"
            elif SYSTEM == "Darwin":
                asset_name = "yt-dlp_macos"
            else:
                asset_name = "yt-dlp"
            
            asset_url = None
            for asset in data.get("assets", []):
                if asset["name"] == asset_name:
                    asset_url = asset["browser_download_url"]
                    break
            
            if not asset_url:
                return False, f"Не найден asset {asset_name}"
            
            # Скачиваем с прогрессом
            if progress_callback:
                progress_callback("start", f"Скачивание yt-dlp {version}...")
            
            r = requests.get(asset_url, stream=True, timeout=30)
            total = int(r.headers.get('content-length', 0))
            downloaded = 0
            
            tmp_path = self.ytdlp_path.with_suffix('.tmp')
            with open(tmp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total > 0:
                            progress_callback("progress", downloaded / total)
            
            # Заменяем старый файл
            if self.ytdlp_path.exists():
                self.ytdlp_path.unlink()
            tmp_path.rename(self.ytdlp_path)
            
            # Делаем исполняемым на Unix
            if SYSTEM != "Windows":
                self.ytdlp_path.chmod(self.ytdlp_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            
            # Обновляем кэш
            self._cache["ytdlp_local"] = version
            self._cache["ytdlp_latest"] = version
            self._cache["ytdlp_check"] = datetime.now().isoformat()
            self._save_cache()
            
            if progress_callback:
                progress_callback("done", version)
            
            return True, version
        
        except Exception as e:
            return False, str(e)
    
    # ── Скачивание ffmpeg ──
    
    def download_ffmpeg(self, progress_callback=None):
        """Скачать ffmpeg"""
        if SYSTEM not in self.FFMPEG_URLS:
            return False, f"Не поддерживается ОС: {SYSTEM}"
        
        url = self.FFMPEG_URLS[SYSTEM]
        
        try:
            if progress_callback:
                progress_callback("start", "Скачивание ffmpeg...")
            
            r = requests.get(url, stream=True, timeout=60, allow_redirects=True)
            total = int(r.headers.get('content-length', 0))
            downloaded = 0
            
            tmp_zip = BIN_DIR / "ffmpeg_download.tmp"
            with open(tmp_zip, 'wb') as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total > 0:
                            progress_callback("progress", downloaded / total)
            
            # Для Windows — извлекаем ffmpeg.exe из ZIP
            if SYSTEM == "Windows":
                with zipfile.ZipFile(tmp_zip, 'r') as z:
                    # Ищем ffmpeg.exe в архиве
                    for name in z.namelist():
                        if name.endswith('bin/ffmpeg.exe'):
                            with z.open(name) as src, open(self.ffmpeg_path, 'wb') as dst:
                                shutil.copyfileobj(src, dst)
                            break
                tmp_zip.unlink()
            
            elif SYSTEM == "Darwin":
                # macOS — это просто zip с бинарником
                with zipfile.ZipFile(tmp_zip, 'r') as z:
                    z.extractall(BIN_DIR)
                tmp_zip.unlink()
                if (BIN_DIR / "ffmpeg").exists():
                    (BIN_DIR / "ffmpeg").rename(self.ffmpeg_path)
            
            # Права на выполнение
            if SYSTEM != "Windows" and self.ffmpeg_path.exists():
                self.ffmpeg_path.chmod(self.ffmpeg_path.stat().st_mode | stat.S_IEXEC)
            
            if progress_callback:
                progress_callback("done", "ffmpeg")
            
            return True, "ffmpeg"
        
        except Exception as e:
            return False, str(e)


# ═══════════════════════════════════════════════════════
# ЗАГРУЗЧИК (через subprocess)
# ═══════════════════════════════════════════════════════

class VideoDownloader:
    """Загружает видео через yt-dlp CLI"""
    
    # Регулярки для парсинга прогресса
    RE_PROGRESS = re.compile(
        r'\[download\]\s+([\d.]+)%\s+of\s+~?([\d.]+[KMGT]?i?B)\s+at\s+([\d.]+[KMGT]?i?B/s)\s+ETA\s+([\d:]+)'
    )
    RE_DEST = re.compile(r'\[(?:Merger|ExtractAudio)\]\s+Merging formats into "([^"]+)"|\[ExtractAudio\] Destination: (.+)')
    
    def __init__(self, bin_manager):
        self.bm = bin_manager
    
    def _base_cmd(self):
        """Базовая команда с общими флагами"""
        cmd = [str(self.bm.ytdlp_path)]
        if self.bm.has_ffmpeg():
            cmd += ["--ffmpeg-location", str(self.bm.ffmpeg_path.parent)]
        return cmd
    
    def get_info(self, url, use_cookies=False):
        """Получить инфо о видео в JSON"""
        cmd = self._base_cmd() + [
            "--dump-json",
            "--no-warnings",
            "--no-playlist",
            url
        ]
        if use_cookies and COOKIES_FILE.exists():
            cmd += ["--cookies", str(COOKIES_FILE)]
        
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, 
                             timeout=30, encoding='utf-8', errors='ignore')
            if r.returncode != 0:
                return None, r.stderr.strip()
            
            info = json.loads(r.stdout)
            return info, None
        except subprocess.TimeoutExpired:
            return None, "Таймаут при получении инфо"
        except json.JSONDecodeError:
            return None, "Не удалось распарсить ответ"
        except Exception as e:
            return None, str(e)
    
    def download(self, url, format_type, quality, use_cookies=False, 
                progress_callback=None, log_callback=None):
        """Скачать видео/аудио. progress_callback(type, data), log_callback(msg)"""
        
        cmd = self._base_cmd() + [
            "--newline",           # Каждая строка прогресса на новой строке
            "--no-playlist",
            "--windows-filenames",
            "--restrict-filenames",
            "-o", str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
            url
        ]
        
        if use_cookies and COOKIES_FILE.exists():
            cmd += ["--cookies", str(COOKIES_FILE)]
        
        # Формат
        if format_type == "audio":
            bitrate_map = {"320 kbps": "320", "256 kbps": "256", "192 kbps": "192", 
                          "128 kbps": "128", "96 kbps": "96"}
            br = bitrate_map.get(quality, "320")
            cmd += [
                "-x",                      # Извлечь аудио
                "--audio-format", "mp3",
                "--audio-quality", br + "K"
            ]
        else:
            quality_map = {
                "2160p (4K)":      "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
                "1440p (2K)":      "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
                "1080p (Full HD)": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "720p (HD)":       "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "480p":            "bestvideo[height<=480]+bestaudio/best[height<=480]",
                "360p":            "bestvideo[height<=360]+bestaudio/best[height<=360]",
                "Лучшее доступное": "bestvideo+bestaudio/best",
            }
            fmt = quality_map.get(quality, "bestvideo+bestaudio/best")
            cmd += ["-f", fmt, "--merge-output-format", "mp4"]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=1
            )
            
            final_file = None
            
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                
                if log_callback:
                    # Показываем важные сообщения
                    if any(k in line for k in ["[youtube]", "ERROR", "WARNING: Unable"]):
                        log_callback(line)
                
                # Парсим прогресс
                m = self.RE_PROGRESS.search(line)
                if m and progress_callback:
                    percent = float(m.group(1))
                    size = m.group(2)
                    speed = m.group(3)
                    eta = m.group(4)
                    progress_callback("progress", {
                        "percent": percent,
                        "size": size,
                        "speed": speed,
                        "eta": eta
                    })
                
                # Финальный файл
                m2 = self.RE_DEST.search(line)
                if m2:
                    final_file = m2.group(1) or m2.group(2)
                
                if line.startswith("[download] Destination:") or line.startswith("[download] 100%"):
                    if progress_callback:
                        progress_callback("downloading", line)
                
                if "[Merger]" in line or "[ExtractAudio]" in line:
                    if progress_callback:
                        progress_callback("processing", line)
            
            process.wait()
            
            if process.returncode != 0:
                return False, "Ошибка загрузки (код {})".format(process.returncode)
            
            # Если не спарсили путь — ищем последний изменённый файл в папке
            if not final_file or not Path(final_file).exists():
                files = sorted(DOWNLOAD_DIR.glob("*"), key=os.path.getmtime, reverse=True)
                if files:
                    final_file = str(files[0])
            
            return True, final_file
        
        except Exception as e:
            return False, str(e)


# ═══════════════════════════════════════════════════════
# ОСНОВНОЙ ИНТЕРФЕЙС
# ═══════════════════════════════════════════════════════

class YTGrabber(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YT-GRABBER :: H4CK3R Edition v4.0")
        self.geometry("780x850")
        self.minsize(700, 780)
        self.configure(fg_color=COLORS["bg_dark"])
        
        self.font_body = ctk.CTkFont(family="Consolas", size=13)
        self.font_small = ctk.CTkFont(family="Consolas", size=11)
        self.font_tiny = ctk.CTkFont(family="Consolas", size=10)
        self.font_mono = ctk.CTkFont(family="Fira Code", size=11)
        
        self.bin_manager = BinManager()
        self.downloader = VideoDownloader(self.bin_manager)
        
        self.is_downloading = False
        self.last_downloaded_file = None
        self.dot_counter = 0
        self.dot_animation_running = False
        self._current_status_base = "IDLE"
        
        self._build_ui()
        self._log(f"[SYS] Папка: {DOWNLOAD_DIR}", "success")
        
        # Проверяем бинарники при старте
        self.after(100, self._startup_check)
    
    # ── UI (сокращённо, т.к. структура та же) ──
    
    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=30, pady=20)
        
        self._build_header(main)
        self._build_bin_status(main)  # Статус yt-dlp и ffmpeg
        self._build_url_section(main)
        self._build_format_section(main)
        self._build_quality_section(main)
        self._build_cookies_section(main)
        self._build_action_section(main)
        self._build_progress_section(main)
        self._build_log_section(main)
        self._build_footer(main)
    
    def _build_header(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        
        art = ["╔═╗╔╦╗  ╔═╗╦═╗╔═╗╔╗ ╔═╗╦═╗",
               "╚═╗ ║   ║ ╦╠╦╝╠═╣╠╩╗║╣ ╠╦╝",
               "╚═╝ ╩   ╚═╝╩╚═╩ ╩╚═╝╚═╝╩╚═"]
        for a in art:
            ctk.CTkLabel(header, text=a, font=self.font_small, text_color=COLORS["accent"]).pack()
        
        ctk.CTkLabel(header, text="[ Self-Updating Binary Edition :: v4.0 ]",
                     font=self.font_small, text_color=COLORS["text_dim"]).pack(pady=(5,0))
        ctk.CTkFrame(parent, height=1, fg_color=COLORS["border"]).pack(fill="x", pady=(5,10))
    
    def _build_bin_status(self, parent):
        """Панель статуса бинарников"""
        bar = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=8, 
                          border_width=1, border_color=COLORS["border"])
        bar.pack(fill="x", pady=(0, 10))
        
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=8)
        
        # Статус yt-dlp
        ytdlp_frame = ctk.CTkFrame(inner, fg_color="transparent")
        ytdlp_frame.pack(side="left")
        
        self.ytdlp_icon = ctk.CTkLabel(ytdlp_frame, text="⏳", font=self.font_body)
        self.ytdlp_icon.pack(side="left", padx=(0,6))
        
        self.lbl_ytdlp = ctk.CTkLabel(ytdlp_frame, text="yt-dlp: проверка...", 
                                      font=self.font_small, text_color=COLORS["text_dim"])
        self.lbl_ytdlp.pack(side="left")
        
        # Разделитель
        ctk.CTkLabel(inner, text="│", font=self.font_small, text_color=COLORS["border"]).pack(side="left", padx=12)
        
        # Статус ffmpeg
        ffmpeg_frame = ctk.CTkFrame(inner, fg_color="transparent")
        ffmpeg_frame.pack(side="left")
        
        self.ffmpeg_icon = ctk.CTkLabel(ffmpeg_frame, text="⏳", font=self.font_body)
        self.ffmpeg_icon.pack(side="left", padx=(0,6))
        
        self.lbl_ffmpeg = ctk.CTkLabel(ffmpeg_frame, text="ffmpeg: проверка...",
                                       font=self.font_small, text_color=COLORS["text_dim"])
        self.lbl_ffmpeg.pack(side="left")
        
        # Кнопка обновления
        self.btn_update = ctk.CTkButton(
            inner, text="🔄 Обновить всё", font=self.font_small,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_dim"],
            text_color=COLORS["bg_dark"], width=130, height=28, corner_radius=6,
            command=self._manual_update
        )
        self.btn_update.pack(side="right")
    
    def _build_url_section(self, parent):
        section = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        section.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(section, text="> ВВЕДИТЕ ЦЕЛЕВОЙ URL:", font=self.font_body, text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15,8))
        
        uf = ctk.CTkFrame(section, fg_color="transparent")
        uf.pack(fill="x", padx=20, pady=(0,15))
        
        self.entry_url = ctk.CTkEntry(uf, placeholder_text="https://youtube.com/watch?v=...", font=self.font_body, fg_color=COLORS["bg_input"], border_color=COLORS["border"], border_width=2, text_color=COLORS["text"], height=45, corner_radius=8)
        self.entry_url.pack(side="left", fill="x", expand=True, padx=(0,10))
        self.entry_url.bind("<Return>", lambda e: self._start_download())
        
        ctk.CTkButton(uf, text="⚡ SCAN", font=self.font_body, fg_color=COLORS["bg_input"], hover_color=COLORS["accent"], text_color=COLORS["accent"], border_width=2, border_color=COLORS["accent"], corner_radius=8, width=100, height=45, command=self._scan_video).pack(side="right")
    
    def _build_format_section(self, parent):
        section = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        section.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(section, text="> ФОРМАТ ВЫХОДА:", font=self.font_body, text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15,8))
        
        ff = ctk.CTkFrame(section, fg_color="transparent")
        ff.pack(fill="x", padx=20, pady=(0,15))
        
        self.format_var = ctk.StringVar(value="video")
        
        self.btn_video = ctk.CTkButton(ff, text="🎬 VIDEO", font=self.font_body, fg_color=COLORS["accent"], hover_color=COLORS["accent_dim"], text_color=COLORS["bg_dark"], corner_radius=8, height=45, command=lambda: self._select_format("video"))
        self.btn_video.pack(side="left", fill="x", expand=True, padx=(0,8))
        
        self.btn_audio = ctk.CTkButton(ff, text="🎵 AUDIO (MP3)", font=self.font_body, fg_color=COLORS["bg_input"], hover_color=COLORS["secondary"], text_color=COLORS["secondary"], border_width=2, border_color=COLORS["secondary"], corner_radius=8, height=45, command=lambda: self._select_format("audio"))
        self.btn_audio.pack(side="left", fill="x", expand=True)
    
    def _build_quality_section(self, parent):
        section = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        section.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(section, text="> КАЧЕСТВО:", font=self.font_body, text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15,8))
        
        qf = ctk.CTkFrame(section, fg_color="transparent")
        qf.pack(fill="x", padx=20, pady=(0,15))
        
        self.video_qualities = ["2160p (4K)", "1440p (2K)", "1080p (Full HD)", "720p (HD)", "480p", "360p", "Лучшее доступное"]
        self.audio_qualities = ["320 kbps", "256 kbps", "192 kbps", "128 kbps", "96 kbps"]
        self.quality_var = ctk.StringVar(value=self.video_qualities[0])
        
        self.dropdown_quality = ctk.CTkOptionMenu(qf, values=self.video_qualities, variable=self.quality_var, font=self.font_body, dropdown_font=self.font_body, fg_color=COLORS["bg_input"], button_color=COLORS["accent"], button_hover_color=COLORS["accent_dim"], dropdown_fg_color=COLORS["bg_card"], dropdown_hover_color=COLORS["bg_input"], dropdown_text_color=COLORS["text"], text_color=COLORS["text"], corner_radius=8, height=45)
        self.dropdown_quality.pack(fill="x")
    
    def _build_cookies_section(self, parent):
        section = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        section.pack(fill="x", pady=(0, 10))
        
        inner = ctk.CTkFrame(section, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=12)
        
        self.use_cookies_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(inner, text="🍪 Использовать cookies (для age-restricted)", font=self.font_small, fg_color=COLORS["accent"], hover_color=COLORS["accent_dim"], text_color=COLORS["text"], variable=self.use_cookies_var, command=self._on_cookies_toggle).pack(side="left")
        
        ctk.CTkButton(inner, text="📥 Импорт", font=self.font_small, fg_color="transparent", hover_color=COLORS["bg_input"], text_color=COLORS["secondary"], width=80, height=26, corner_radius=6, command=self._import_cookies).pack(side="right")
        
        self.lbl_cookies_status = ctk.CTkLabel(section, text="", font=self.font_tiny, text_color=COLORS["text_dim"])
        self.lbl_cookies_status.pack(anchor="w", padx=20, pady=(0, 10))
    
    def _build_action_section(self, parent):
        section = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        section.pack(fill="x", pady=(0, 10))
        
        af = ctk.CTkFrame(section, fg_color="transparent")
        af.pack(fill="x", padx=20, pady=15)
        
        self.btn_download = ctk.CTkButton(af, text="▶ НАЧАТЬ ЗАХВАТ", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), fg_color=COLORS["accent"], hover_color=COLORS["accent_dim"], text_color=COLORS["bg_dark"], corner_radius=8, height=55, command=self._start_download, state="disabled")
        self.btn_download.pack(fill="x", pady=(0,10))
        
        pf = ctk.CTkFrame(af, fg_color="transparent")
        pf.pack(fill="x")
        
        self.lbl_path = ctk.CTkLabel(pf, text=f"📁 {str(DOWNLOAD_DIR)}", font=self.font_small, text_color=COLORS["text_dim"])
        self.lbl_path.pack(side="left")
        
        ctk.CTkButton(pf, text="📂 Открыть", font=self.font_small, fg_color="transparent", hover_color=COLORS["bg_input"], text_color=COLORS["secondary"], width=90, height=28, corner_radius=6, command=self._open_download_folder).pack(side="right")
    
    def _build_progress_section(self, parent):
        section = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        section.pack(fill="x", pady=(0, 10))
        
        content = ctk.CTkFrame(section, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=15)
        
        top = ctk.CTkFrame(content, fg_color="transparent")
        top.pack(fill="x")
        
        self.lbl_status = ctk.CTkLabel(top, text="[ IDLE ]", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=COLORS["text_dim"])
        self.lbl_status.pack(side="left")
        
        self.lbl_percent = ctk.CTkLabel(top, text="0%", font=ctk.CTkFont(family="Consolas", size=18, weight="bold"), text_color=COLORS["accent"])
        self.lbl_percent.pack(side="right")
        
        self.progress_bar = AnimatedProgressBar(content, height=18)
        self.progress_bar.pack(fill="x", pady=(8,8))
        
        bottom = ctk.CTkFrame(content, fg_color="transparent")
        bottom.pack(fill="x")
        
        self.lbl_speed = ctk.CTkLabel(bottom, text="⚡ Ожидание...", font=self.font_small, text_color=COLORS["text_dim"])
        self.lbl_speed.pack(side="left")
        
        self.lbl_eta = ctk.CTkLabel(bottom, text="ETA: --:--", font=self.font_small, text_color=COLORS["text_dim"])
        self.lbl_eta.pack(side="right")
    
    def _build_log_section(self, parent):
        section = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=12, border_width=1, border_color=COLORS["border"], height=130)
        section.pack(fill="x", pady=(0, 8))
        section.pack_propagate(False)
        
        lh = ctk.CTkFrame(section, fg_color="transparent")
        lh.pack(fill="x", padx=15, pady=(10,0))
        
        ctk.CTkLabel(lh, text="> CONSOLE:", font=self.font_small, text_color=COLORS["text_dim"]).pack(side="left")
        ctk.CTkButton(lh, text="CLEAR", font=self.font_small, fg_color="transparent", hover_color=COLORS["bg_input"], text_color=COLORS["danger"], width=60, height=20, corner_radius=4, command=self._clear_log).pack(side="right")
        
        self.log_text = ctk.CTkTextbox(section, font=self.font_mono, fg_color=COLORS["bg_dark"], text_color=COLORS["text"], corner_radius=8, border_width=1, border_color=COLORS["border"], wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(8,12))
    
    def _build_footer(self, parent):
        ctk.CTkLabel(parent, text="[ Авто-обновление через GitHub :: Stay frosty ]", font=self.font_small, text_color=COLORS["text_dim"]).pack()
    
    # ── УТИЛИТЫ ──
    
    def _log(self, msg, lvl="info"):
        self.log_text.insert("end", f"[{lvl.upper()}] {msg}\n")
        self.log_text.see("end")
    
    def _clear_log(self):
        self.log_text.delete("1.0", "end")
    
    def _animate_dots(self):
        if not self.dot_animation_running: return
        self.dot_counter = (self.dot_counter + 1) % 4
        self.lbl_status.configure(text=f"[ {self._current_status_base}{'.' * self.dot_counter} ]")
        self.after(400, self._animate_dots)
    
    def _set_status(self, text, color):
        self._current_status_base = text
        self.lbl_status.configure(text=f"[ {text} ]", text_color=color)
        if text not in ["IDLE", "COMPLETE", "ERROR", "READY"]:
            if not self.dot_animation_running:
                self.dot_animation_running = True
                self._animate_dots()
        else:
            self.dot_animation_running = False
    
    # ── СТАРТОВАЯ ПРОВЕРКА ──
    
    def _startup_check(self):
        """Проверить наличие yt-dlp и ffmpeg при запуске"""
        threading.Thread(target=self._startup_thread, daemon=True).start()
    
    def _startup_thread(self):
        self.after(0, lambda: self._log("Проверка инструментов...", "info"))
        
        # yt-dlp
        if not self.bin_manager.has_ytdlp():
            self.after(0, lambda: self._log("yt-dlp не найден — скачиваю...", "warning"))
            self.after(0, lambda: self.ytdlp_icon.configure(text="⏳"))
            self.after(0, lambda: self.lbl_ytdlp.configure(text="yt-dlp: скачивание..."))
            
            success, result = self.bin_manager.download_ytdlp(
                progress_callback=lambda t, d: self.after(0, lambda: self._on_ytdlp_progress(t, d))
            )
            
            if success:
                self.after(0, lambda: self._log(f"✓ yt-dlp {result} установлен", "success"))
            else:
                self.after(0, lambda: self._log(f"✗ Ошибка: {result}", "error"))
        else:
            # Проверяем обновления
            needs, local, latest = self.bin_manager.needs_ytdlp_update()
            
            if needs:
                self.after(0, lambda: self.ytdlp_icon.configure(text="🔴", text_color=COLORS["danger"]))
                self.after(0, lambda: self.lbl_ytdlp.configure(
                    text=f"yt-dlp v{local} (доступна v{latest})",
                    text_color=COLORS["warning"]
                ))
                self.after(0, lambda: self._log(f"Доступна новая версия yt-dlp: {local} → {latest}", "warning"))
                self.after(0, lambda: self._log("Нажмите '🔄 Обновить всё'", "info"))
            else:
                self.after(0, lambda: self.ytdlp_icon.configure(text="🟢", text_color=COLORS["success"]))
                self.after(0, lambda: self.lbl_ytdlp.configure(
                    text=f"yt-dlp v{local or '?'} (актуально)",
                    text_color=COLORS["success"]
                ))
        
        # ffmpeg
        if not self.bin_manager.has_ffmpeg():
            self.after(0, lambda: self.ffmpeg_icon.configure(text="⚠️", text_color=COLORS["warning"]))
            self.after(0, lambda: self.lbl_ffmpeg.configure(
                text="ffmpeg: не установлен (MP3 не будет работать)",
                text_color=COLORS["warning"]
            ))
            self.after(0, lambda: self._log("⚠️ ffmpeg не найден — скачиваю...", "warning"))
            
            success, result = self.bin_manager.download_ffmpeg(
                progress_callback=lambda t, d: self.after(0, lambda: self._on_ffmpeg_progress(t, d))
            )
            
            if success:
                self.after(0, lambda: self._log("✓ ffmpeg установлен", "success"))
                self.after(0, lambda: self.ffmpeg_icon.configure(text="🟢", text_color=COLORS["success"]))
                self.after(0, lambda: self.lbl_ffmpeg.configure(text="ffmpeg: установлен", text_color=COLORS["success"]))
            else:
                self.after(0, lambda: self._log(f"✗ ffmpeg: {result}", "error"))
        else:
            self.after(0, lambda: self.ffmpeg_icon.configure(text="🟢", text_color=COLORS["success"]))
            self.after(0, lambda: self.lbl_ffmpeg.configure(text="ffmpeg: установлен", text_color=COLORS["success"]))
        
        # Активируем кнопку
        self.after(0, lambda: self.btn_download.configure(state="normal"))
        self.after(0, lambda: self._set_status("READY", COLORS["success"]))
        self.after(0, lambda: self._log("✓ Готов к работе", "success"))
    
    def _on_ytdlp_progress(self, ptype, data):
        if ptype == "progress":
            self.progress_bar.set(data)
    
    def _on_ffmpeg_progress(self, ptype, data):
        if ptype == "progress":
            self.progress_bar.set(data)
    
    def _manual_update(self):
        """Обновить всё вручную"""
        self.btn_update.configure(state="disabled", text="⏳ Обновление...")
        self.progress_bar.reset()
        threading.Thread(target=self._manual_update_thread, daemon=True).start()
    
    def _manual_update_thread(self):
        self.after(0, lambda: self._log("═" * 50, "info"))
        self.after(0, lambda: self._log(">>> ОБНОВЛЕНИЕ ИНСТРУМЕНТОВ <<<", "warning"))
        
        # yt-dlp — всегда перекачиваем свежий
        self.after(0, lambda: self._log("Скачиваю свежий yt-dlp...", "info"))
        success, result = self.bin_manager.download_ytdlp(
            progress_callback=lambda t, d: self.after(0, lambda: self._on_ytdlp_progress(t, d))
        )
        if success:
            self.after(0, lambda: self._log(f"✓ yt-dlp {result}", "success"))
            self.after(0, lambda: self.ytdlp_icon.configure(text="🟢", text_color=COLORS["success"]))
            self.after(0, lambda: self.lbl_ytdlp.configure(text=f"yt-dlp v{result} (актуально)", text_color=COLORS["success"]))
        else:
            self.after(0, lambda: self._log(f"✗ yt-dlp: {result}", "error"))
        
        # ffmpeg — если нет
        if not self.bin_manager.has_ffmpeg():
            self.after(0, lambda: self._log("Скачиваю ffmpeg...", "info"))
            success, result = self.bin_manager.download_ffmpeg(
                progress_callback=lambda t, d: self.after(0, lambda: self._on_ffmpeg_progress(t, d))
            )
            if success:
                self.after(0, lambda: self._log("✓ ffmpeg установлен", "success"))
                self.after(0, lambda: self.ffmpeg_icon.configure(text="🟢", text_color=COLORS["success"]))
                self.after(0, lambda: self.lbl_ffmpeg.configure(text="ffmpeg: установлен", text_color=COLORS["success"]))
            else:
                self.after(0, lambda: self._log(f"✗ ffmpeg: {result}", "error"))
        
        self.after(0, lambda: self._log("═" * 50, "success"))
        self.after(0, lambda: self.btn_update.configure(state="normal", text="🔄 Обновить всё"))
        self.after(0, lambda: self.progress_bar.reset())
    
    # ── ФОРМАТ / КАЧЕСТВО / COOKIES ──
    
    def _select_format(self, fmt):
        self.format_var.set(fmt)
        if fmt == "video":
            self.btn_video.configure(fg_color=COLORS["accent"], text_color=COLORS["bg_dark"], border_width=0)
            self.btn_audio.configure(fg_color=COLORS["bg_input"], text_color=COLORS["secondary"], border_width=2, border_color=COLORS["secondary"])
            self.dropdown_quality.configure(values=self.video_qualities)
            self.quality_var.set(self.video_qualities[0])
        else:
            self.btn_audio.configure(fg_color=COLORS["secondary"], text_color=COLORS["bg_dark"], border_width=0)
            self.btn_video.configure(fg_color=COLORS["bg_input"], text_color=COLORS["accent"], border_width=2, border_color=COLORS["accent"])
            self.dropdown_quality.configure(values=self.audio_qualities)
            self.quality_var.set(self.audio_qualities[0])
            if not self.bin_manager.has_ffmpeg():
                self._log("⚠️ Для MP3 нужен ffmpeg — скачайте его кнопкой 'Обновить всё'", "warning")
    
    def _on_cookies_toggle(self):
        if self.use_cookies_var.get() and not COOKIES_FILE.exists():
            self._log("⚠️ cookies.txt не найден — нажмите 'Импорт'", "warning")
        self._update_cookies_status()
    
    def _update_cookies_status(self):
        if self.use_cookies_var.get():
            if COOKIES_FILE.exists():
                self.lbl_cookies_status.configure(text=f"✓ {COOKIES_FILE.name} ({COOKIES_FILE.stat().st_size/1024:.1f} KB)", text_color=COLORS["success"])
            else:
                self.lbl_cookies_status.configure(text="✗ cookies.txt не найден", text_color=COLORS["danger"])
        else:
            self.lbl_cookies_status.configure(text="")
    
    def _import_cookies(self):
        fp = filedialog.askopenfilename(title="Выберите cookies.txt", filetypes=[("Cookies", "*.txt"), ("All", "*.*")])
        if fp:
            try:
                shutil.copy(fp, COOKIES_FILE)
                self.use_cookies_var.set(True)
                self._log(f"✓ Cookies импортированы", "success")
                self._update_cookies_status()
            except Exception as e:
                self._log(f"✗ Ошибка: {e}", "error")
    
    # ── СКАНИРОВАНИЕ И ЗАГРУЗКА ──
    
    def _scan_video(self):
        url = self.entry_url.get().strip()
        if not url:
            self._log("ОШИБКА: URL не указан!", "error"); return
        if not self.bin_manager.has_ytdlp():
            self._log("yt-dlp ещё не готов, подождите...", "warning"); return
        
        self._log("Сканирование...", "info")
        threading.Thread(target=self._scan_thread, args=(url,), daemon=True).start()
    
    def _scan_thread(self, url):
        info, err = self.downloader.get_info(url, self.use_cookies_var.get())
        if err:
            self.after(0, lambda: self._log(f"✗ {err}", "error"))
            return
        
        title = info.get('title', 'N/A')
        dur = info.get('duration', 0) or 0
        m, s = divmod(dur, 60)
        
        self.after(0, lambda: self._log("─" * 50, "success"))
        self.after(0, lambda: self._log(f"✓ {title[:60]}", "success"))
        self.after(0, lambda: self._log(f"✓ {m}м {s}с | {info.get('uploader', 'N/A')}", "success"))
        self.after(0, lambda: self._log(f"✓ Просмотров: {info.get('view_count', 0) or 0:,}", "success"))
        self.after(0, lambda: self._log("─" * 50, "success"))
    
    def _start_download(self):
        url = self.entry_url.get().strip()
        if not url:
            self._log("ОШИБКА: URL не указан!", "error"); return
        if not (url.startswith("http://") or url.startswith("https://")):
            self._log("ОШИБКА: Некорректный URL!", "error"); return
        if self.is_downloading:
            return
        if not self.bin_manager.has_ytdlp():
            self._log("yt-dlp не готов!", "error"); return
        
        if self.format_var.get() == "audio" and not self.bin_manager.has_ffmpeg():
            self._log("✗ Для MP3 нужен ffmpeg. Нажмите 'Обновить всё'!", "error"); return
        
        self.is_downloading = True
        self.last_downloaded_file = None
        self.progress_bar.reset()
        self.progress_bar.start_indeterminate()
        
        self.btn_download.configure(text="⏳ ЗАГРУЗКА...", fg_color=COLORS["warning"], state="disabled")
        self.btn_update.configure(state="disabled")
        self._set_status("DOWNLOADING", COLORS["warning"])
        
        threading.Thread(target=self._download_thread, args=(url,), daemon=True).start()
    
    def _download_thread(self, url):
        fmt = self.format_var.get()
        q = self.quality_var.get()
        
        self.after(0, lambda: self._log("═" * 50, "info"))
        self.after(0, lambda: self._log(">>> ЗАГРУЗКА <<<", "warning"))
        self.after(0, lambda: self._log(f"Формат: {fmt.upper()} | Качество: {q}", "info"))
        
        def on_progress(ptype, data):
            if ptype == "progress":
                def upd():
                    self.progress_bar.stop_indeterminate()
                    self.progress_bar.set(data["percent"] / 100)
                    self.lbl_percent.configure(text=f"{data['percent']:.1f}%")
                    self.lbl_speed.configure(text=f"⚡ {data['speed']}  |  {data['size']}")
                    self.lbl_eta.configure(text=f"ETA: {data['eta']}")
                self.after(0, upd)
            elif ptype == "processing":
                self.after(0, lambda: self._log("Обработка...", "info"))
        
        def on_log(msg):
            if "ERROR" in msg or "unable" in msg.lower():
                self.after(0, lambda: self._log(msg, "error"))
        
        success, result = self.downloader.download(
            url, fmt, q,
            use_cookies=self.use_cookies_var.get(),
            progress_callback=on_progress,
            log_callback=on_log
        )
        
        if success:
            self.last_downloaded_file = Path(result) if result else None
            self.after(0, self._download_success)
        else:
            self.after(0, lambda: self._download_error(result))
    
    def _download_success(self):
        self.is_downloading = False
        self.dot_animation_running = False
        self.btn_download.configure(text="✓ ГОТОВО!", fg_color=COLORS["success"], state="normal")
        self.btn_update.configure(state="normal")
        self._set_status("COMPLETE", COLORS["success"])
        self.progress_bar.complete()
        self.lbl_percent.configure(text="100%", text_color=COLORS["success"])
        self.lbl_speed.configure(text="✓ Завершено")
        self.lbl_eta.configure(text="")
        
        self._log("═" * 50, "success")
        self._log("✓✓✓ ЗАГРУЗКА ЗАВЕРШЕНА! ✓✓✓", "success")
        if self.last_downloaded_file and self.last_downloaded_file.exists():
            sz = self.last_downloaded_file.stat().st_size / (1024*1024)
            self._log(f"✓ {self.last_downloaded_file.name}", "success")
            self._log(f"✓ Размер: {sz:.2f} MB", "success")
            self._log(f"✓ Путь: {self.last_downloaded_file}", "success")
        self._log("═" * 50, "success")
        
        self.after(3000, lambda: self.btn_download.configure(text="▶ НАЧАТЬ ЗАХВАТ", fg_color=COLORS["accent"]))
    
    def _download_error(self, error):
        self.is_downloading = False
        self.dot_animation_running = False
        self.btn_download.configure(text="▶ НАЧАТЬ ЗАХВАТ", fg_color=COLORS["danger"], state="normal")
        self.btn_update.configure(state="normal")
        self._set_status("ERROR", COLORS["danger"])
        self.progress_bar.reset()
        self.lbl_percent.configure(text="0%", text_color=COLORS["danger"])
        self.lbl_speed.configure(text="✗ Ошибка")
        self.lbl_eta.configure(text="")
        
        self._log("═" * 50, "error")
        self._log(f"✗ ОШИБКА: {error[:200]}", "error")
        
        # Подсказки
        if "precondition" in error.lower() or "400" in error:
            self._log("💡 Попробуйте 'Обновить всё' — скачается свежий yt-dlp", "warning")
        elif "sign in" in error.lower() or "age" in error.lower():
            self._log("💡 Включите cookies в настройках", "warning")
        elif "ffmpeg" in error.lower():
            self._log("💡 Нажмите 'Обновить всё' для установки ffmpeg", "warning")
        
        self._log("═" * 50, "error")
    
    def _open_download_folder(self):
        try:
            if SYSTEM == "Windows":
                if self.last_downloaded_file and self.last_downloaded_file.exists():
                    subprocess.run(['explorer', '/select,', str(self.last_downloaded_file)])
                else:
                    os.startfile(str(DOWNLOAD_DIR))
            elif SYSTEM == "Darwin":
                subprocess.run(['open', str(DOWNLOAD_DIR)])
            else:
                subprocess.run(['xdg-open', str(DOWNLOAD_DIR)])
        except Exception as e:
            self._log(f"Ошибка: {e}", "error")


# ═══════════════════════════════════════════════════════
# ТОЧКА ВХОДА
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = YTGrabber()
    app.mainloop()