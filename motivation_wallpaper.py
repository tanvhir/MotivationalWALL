import ctypes
import io
import json
import os
import random
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

APP_NAME = "Motivation Wallpaper"
APP_DIR = Path(os.getenv("APPDATA", Path.home())) / "MotivationWallpaper"
CACHE_DIR = APP_DIR / "wallpapers"
CONFIG_FILE = APP_DIR / "config.json"

DEFAULTS = {
    "query": "study motivation discipline success",
    "interval_minutes": 30,
    "start_with_windows": True,
}

APP_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def load_config():
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {**DEFAULTS, **data}
    except Exception:
        return DEFAULTS.copy()

def save_config(data):
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def set_wallpaper(path):
    ctypes.windll.user32.SystemParametersInfoW(20, 0, str(path), 3)

def image_urls_from_bing(query):
    # Uses the public Bing Images result page; no API key is required.
    url = "https://www.bing.com/images/search?" + urllib.parse.urlencode({
        "q": query,
        "form": "HDRSC2",
        "first": 1
    })
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"
        }
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        html = r.read().decode("utf-8", errors="ignore")

    urls = []
    # Bing commonly embeds original image URLs in murl fields.
    for match in re.findall(r'"murl":"(.*?)"', html):
        u = bytes(match, "utf-8").decode("unicode_escape")
        u = u.replace("\\/", "/")
        if u.startswith(("http://", "https://")):
            urls.append(u)

    # Fallback for alternate markup.
    if not urls:
        for match in re.findall(r'murl&quot;:&quot;(.*?)&quot;', html):
            u = match.replace("\\/", "/")
            if u.startswith(("http://", "https://")):
                urls.append(u)

    # Remove duplicates while preserving order.
    return list(dict.fromkeys(urls))

def download_image(url):
    ext = ".jpg"
    lower = urllib.parse.urlparse(url).path.lower()
    for candidate in (".jpg", ".jpeg", ".png", ".webp"):
        if candidate in lower:
            ext = candidate
            break

    name = f"wallpaper_{int(time.time())}_{random.randint(1000,9999)}{ext}"
    dest = CACHE_DIR / name
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        if len(data) < 20_000:
            return None
        # Keep cache bounded.
        dest.write_bytes(data)
        return dest
    except Exception:
        return None

def get_new_wallpaper(query):
    urls = image_urls_from_bing(query)
    random.shuffle(urls)
    for url in urls[:30]:
        p = download_image(url)
        if p:
            return p
    return None

def cleanup_cache(keep=20):
    files = sorted(
        [p for p in CACHE_DIR.iterdir() if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    for p in files[keep:]:
        try:
            p.unlink()
        except Exception:
            pass

def startup_shortcut_path():
    return Path(os.getenv("APPDATA")) / "Microsoft/Windows/Start Menu/Programs/Startup" / "MotivationWallpaper.lnk"

def set_startup(enabled):
    # Uses PowerShell to create/remove a normal Windows startup shortcut.
    shortcut = startup_shortcut_path()
    if not enabled:
        try:
            shortcut.unlink()
        except FileNotFoundError:
            pass
        return

    exe = Path(sys.executable).resolve()
    if exe.suffix.lower() != ".exe":
        # Running from source: don't create a startup shortcut.
        return

    ps = (
        "$W=New-Object -ComObject WScript.Shell;"
        f"$S=$W.CreateShortcut('{shortcut}');"
        f"$S.TargetPath='{exe}';"
        "$S.WorkingDirectory=$W.SpecialFolders('Startup');"
        "$S.Save()"
    )
    import subprocess
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

class App:
    def __init__(self, root):
        self.root = root
        self.config = load_config()
        self.running = True
        self.busy = False

        root.title(APP_NAME)
        root.geometry("430x330")
        root.resizable(False, False)

        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Motivation Wallpaper", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="Automatically find and change motivational wallpapers.",
            foreground="#666"
        ).pack(anchor="w", pady=(3, 18))

        ttk.Label(frame, text="What should the wallpapers be about?").pack(anchor="w")
        self.query = tk.StringVar(value=self.config["query"])
        ttk.Entry(frame, textvariable=self.query, width=48).pack(fill="x", pady=(5, 14))

        ttk.Label(frame, text="Change wallpaper every:").pack(anchor="w")
        self.interval = tk.StringVar(value=str(self.config["interval_minutes"]))
        combo = ttk.Combobox(
            frame,
            textvariable=self.interval,
            values=["5", "10", "15", "30", "60", "120"],
            state="readonly",
            width=12
        )
        combo.pack(anchor="w", pady=(5, 12))

        self.startup = tk.BooleanVar(value=bool(self.config["start_with_windows"]))
        ttk.Checkbutton(
            frame,
            text="Start automatically with Windows",
            variable=self.startup
        ).pack(anchor="w", pady=(0, 14))

        self.status = tk.StringVar(value="Ready.")
        ttk.Label(frame, textvariable=self.status, foreground="#555").pack(anchor="w")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(15, 0))
        ttk.Button(buttons, text="Change Wallpaper Now", command=self.change_now).pack(side="left")
        ttk.Button(buttons, text="Save Settings", command=self.save).pack(side="right")

        root.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.save(silent=True)
        threading.Thread(target=self.scheduler, daemon=True).start()

    def save(self, silent=False):
        try:
            minutes = int(self.interval.get())
            if minutes not in [5, 10, 15, 30, 60, 120]:
                raise ValueError
        except ValueError:
            messagebox.showerror(APP_NAME, "Please choose a valid interval.")
            return

        self.config.update({
            "query": self.query.get().strip() or DEFAULTS["query"],
            "interval_minutes": minutes,
            "start_with_windows": bool(self.startup.get()),
        })
        save_config(self.config)
        set_startup(self.config["start_with_windows"])
        if not silent:
            self.status.set("Settings saved.")

    def change_now(self):
        if self.busy:
            return
        self.save(silent=True)
        threading.Thread(target=self._change_worker, daemon=True).start()

    def _change_worker(self):
        self.busy = True
        self.root.after(0, lambda: self.status.set("Finding a new wallpaper..."))
        try:
            p = get_new_wallpaper(self.config["query"])
            if not p:
                raise RuntimeError("No usable image was found.")
            set_wallpaper(p)
            cleanup_cache()
            self.root.after(0, lambda: self.status.set(f"Wallpaper changed: {p.name}"))
        except Exception as e:
            self.root.after(0, lambda: self.status.set("Couldn't find a wallpaper. Will retry later."))
        finally:
            self.busy = False

    def scheduler(self):
        # Change one immediately, then wait for the selected interval.
        self._change_worker()
        while self.running:
            for _ in range(self.config["interval_minutes"] * 60):
                if not self.running:
                    return
                time.sleep(1)
            self._change_worker()

    def hide_window(self):
        self.root.withdraw()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconname(APP_NAME)
    except Exception:
        pass
    App(root)
    root.mainloop()
