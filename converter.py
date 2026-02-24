import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from moviepy import VideoFileClip
import os
import threading
import json
import yt_dlp
from proglog import ProgressBarLogger
import urllib.request
import subprocess
import sys
import shutil

# --- ДИЗАЙН ---
BG_MAIN = "#121212"
BG_SURFACE = "#1e1e1e"
ACCENT = "#1db954" 
TEXT_MAIN = "#ffffff"
TEXT_DIM = "#b3b3b3"

# Шлях до файлу конфігурації
SETTINGS_DIR = os.path.join(os.getenv('APPDATA'), 'VideoToMP3Converter')
SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'settings.json')

# --- ОНОВЛЕННЯ ---
VERSION = "1.0.0"
UPDATE_URL = "https://raw.githubusercontent.com/USER/REPO/main/version.json" # ЗАМІНІТЬ НА ВАШ URL

class MyBarLogger(ProgressBarLogger):
    def __init__(self, progress_callback):
        super().__init__()
        self.progress_callback = progress_callback

    def bars_callback(self, bar, attr, value, old_value=None):
        if bar == 't':
            try:
                total = self.bars[bar]['total']
                if total and total > 0:
                    percentage = (value / total) * 100
                    # Викликаємо з ігноруванням зайвих аргументів
                    self.progress_callback(percentage)
            except:
                pass

class ConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TikTok & Video to MP3 Converter")
        self.root.geometry("600x650")
        self.root.configure(bg=BG_MAIN)
        
        self.video_path = ""
        self.auto_trim = tk.BooleanVar(value=False) # Вимкнено за замовчуванням
        self.last_source = None # "tiktok" або "file"
        
        self.load_settings()
        self.setup_ui()
        
        # Перевірка оновлень після запуску UI
        self.root.after(1000, self.check_for_updates)

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Horizontal.TProgressbar", thickness=10, troughcolor="#333", background=ACCENT, borderwidth=0)
        
        container = tk.Frame(self.root, bg=BG_MAIN, padx=30, pady=30)
        container.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(container, bg=BG_MAIN)
        header.pack(fill="x", pady=(0, 20))
        tk.Label(header, text="TikTok & Video", font=("Segoe UI", 20, "bold"), bg=BG_MAIN, fg=ACCENT).pack(side="left")
        tk.Label(header, text=" to MP3", font=("Segoe UI", 20, "bold"), bg=BG_MAIN, fg=TEXT_MAIN).pack(side="left")

        # Кнопка Довідки (?)
        self.btn_help = tk.Button(header, text="?", command=self.show_help, bg=BG_SURFACE, fg=ACCENT, font=("Segoe UI", 12, "bold"), relief="flat", padx=10, cursor="hand2", activebackground="#333", activeforeground=ACCENT)
        self.btn_help.pack(side="right")

        # Folder Selection (Prominent)
        dir_frame = tk.Frame(container, bg=BG_SURFACE, padx=20, pady=15)
        dir_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(dir_frame, text="Папка збереження:", font=("Segoe UI", 9, "bold"), bg=BG_SURFACE, fg=TEXT_DIM).pack(side="left")
        self.btn_dir = tk.Button(dir_frame, text="📁 ВИБРАТИ ПАПКУ", command=self.select_directory, bg="#3e3e3e", fg=TEXT_MAIN, font=("Segoe UI", 9, "bold"), relief="flat", padx=15, pady=5, cursor="hand2")
        self.btn_dir.pack(side="right")
        
        self.label_dir_path = tk.Label(dir_frame, text=self.output_dir, bg=BG_SURFACE, fg=ACCENT, font=("Segoe UI", 9, "italic"))
        self.label_dir_path.pack(side="left", padx=10)

        # TikTok Section
        tk_frame = tk.Frame(container, bg=BG_SURFACE, padx=20, pady=20)
        tk_frame.pack(fill="x", pady=(0, 20))
        
        tk_header = tk.Frame(tk_frame, bg=BG_SURFACE)
        tk_header.pack(fill="x", pady=(0, 10))
        tk.Label(tk_header, text="TikTok Посилання", font=("Segoe UI", 10, "bold"), bg=BG_SURFACE, fg=TEXT_DIM).pack(side="left")
        
        # Кнопка очищення (Червоний хрестик)
        self.btn_clear = tk.Button(tk_header, text="✕ ОЧИСТИТИ", command=self.clear_url, bg=BG_SURFACE, fg="#ff4444", font=("Segoe UI", 8, "bold"), relief="flat", padx=5, cursor="hand2")
        self.btn_clear.pack(side="right")
        
        self.url_var = tk.StringVar(value="Вставте посилання тут...")
        self.url_var.trace_add("write", lambda *args: self.on_url_change())
        self.url_entry = tk.Entry(tk_frame, textvariable=self.url_var, font=("Segoe UI", 12), bg="#2a2a2a", fg=TEXT_MAIN, insertbackground=TEXT_MAIN, borderwidth=0, highlightthickness=1, highlightbackground="#3e3e3e")
        self.url_entry.pack(fill="x", ipady=8, pady=(0, 10))
        self.url_entry.bind("<FocusIn>", lambda e: self.url_entry.delete(0, tk.END) if "Вставте" in self.url_entry.get() else None)

        tk.Button(tk_frame, text="📋 ВСТАВИТИ З БУФЕРУ", command=self.paste_url, bg="#3e3e3e", fg=TEXT_MAIN, font=("Segoe UI", 9, "bold"), relief="flat", pady=8, cursor="hand2").pack(fill="x")

        # Local File Section
        file_frame = tk.Frame(container, bg=BG_SURFACE, padx=20, pady=20)
        file_frame.pack(fill="x", pady=(0, 20))
        
        self.btn_select = tk.Button(file_frame, text="📂 ВИБРАТИ ФАЙЛ НА ПК", command=self.select_video, bg="#3e3e3e", fg=TEXT_MAIN, font=("Segoe UI", 10, "bold"), relief="flat", pady=10, cursor="hand2")
        self.btn_select.pack(fill="x")
        self.label_file = tk.Label(file_frame, text="Файл не вибрано", bg=BG_SURFACE, fg=TEXT_DIM, font=("Segoe UI", 9, "italic"))
        self.label_file.pack(pady=(5, 0))

        # Trim Settings
        trim_frame = tk.Frame(container, bg=BG_SURFACE, padx=20, pady=15)
        trim_frame.pack(fill="x", pady=(0, 30))
        
        self.cb_trim = tk.Checkbutton(trim_frame, text="Авто-обрізка заставки в кінці:", variable=self.auto_trim, bg=BG_SURFACE, fg=TEXT_MAIN, selectcolor="#000", activebackground=BG_SURFACE, activeforeground=ACCENT, font=("Segoe UI", 10), cursor="hand2")
        self.cb_trim.pack(side="left")

        self.trim_entry = tk.Entry(trim_frame, width=4, font=("Segoe UI", 10, "bold"), bg="#2a2a2a", fg=ACCENT, borderwidth=0, highlightthickness=1, highlightbackground="#3e3e3e", justify="center")
        self.trim_entry.pack(side="left", padx=10)
        self.trim_entry.insert(0, "3.0")
        tk.Label(trim_frame, text="сек.", bg=BG_SURFACE, fg=TEXT_DIM, font=("Segoe UI", 10)).pack(side="left")

        # Convert Button
        self.btn_convert = tk.Button(container, text="🔥 КОНВЕРТУВАТИ В MP3", command=self.start_conversion, bg=ACCENT, fg="#000", font=("Segoe UI", 16, "bold"), relief="flat", pady=18, cursor="hand2", activebackground="#1ed760")
        self.btn_convert.pack(fill="x")

        # Progress & Status
        self.progress_bar = ttk.Progressbar(container, style="Horizontal.TProgressbar", mode="determinate")
        self.progress_bar.pack(fill="x", pady=(20, 5))
        
        self.status_label = tk.Label(container, text="Готово до роботи", font=("Segoe UI", 9), bg=BG_MAIN, fg="#555")
        self.status_label.pack()

    def load_settings(self):
        default_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        self.output_dir = default_dir
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_dir = settings.get('output_dir')
                    if saved_dir and os.path.exists(saved_dir):
                        self.output_dir = saved_dir
            except: pass

    def save_settings(self):
        try:
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump({'output_dir': self.output_dir}, f, ensure_ascii=False, indent=4)
        except: pass

    def select_directory(self):
        directory = filedialog.askdirectory(initialdir=self.output_dir)
        if directory:
            self.output_dir = directory
            self.label_dir_path.config(text=directory)
            self.save_settings()

    def select_video(self):
        path = filedialog.askopenfilename(filetypes=[("Відео", "*.mp4 *.avi *.mkv *.mov *.flv *.webm")])
        if path:
            self.video_path = path
            self.last_source = "file"
            self.label_file.config(text=os.path.basename(path), fg=ACCENT)
            # Якщо є посилання, натякаємо що зараз пріоритет у файлу
            if self.url_var.get() and "Вставте" not in self.url_var.get():
                self.status_label.config(text="Пріоритет: Локальний файл", fg=ACCENT)

    def clear_url(self):
        self.url_var.set("")
        if self.last_source == "tiktok":
            self.last_source = "file" if self.video_path else None
        self.status_label.config(text="Посилання видалено", fg=TEXT_DIM)

    def on_url_change(self):
        val = self.url_var.get()
        if val and "Вставте" not in val and val.strip() != "":
            self.last_source = "tiktok"
            if self.video_path:
                self.status_label.config(text="Пріоритет: TikTok посилання", fg=ACCENT)

    def paste_url(self):
        try:
            cb = self.root.clipboard_get()
            if "http" in cb:
                self.url_var.set(cb)
                self.last_source = "tiktok"
        except: pass

    def start_conversion(self):
        url = self.url_var.get().strip()
        is_tiktok_url = url.startswith("http") and "tiktok" in url.lower()
        
        # Визначаємо пріоритет
        use_tiktok = False
        if self.last_source == "tiktok" and is_tiktok_url:
            use_tiktok = True
        elif self.last_source == "file" and self.video_path:
            use_tiktok = False
        elif is_tiktok_url: # Фоллбек якщо last_source не стабільно спрацював
            use_tiktok = True
        elif self.video_path:
            use_tiktok = False
        else:
            messagebox.showwarning("Помилка", "Виберіть файл або вставте посилання на TikTok!")
            return
            
        self.btn_convert.config(state="disabled", bg="#333")
        self.status_label.config(text="Запуск процесу...", fg=ACCENT)
        self.progress_bar["value"] = 0
        
        threading.Thread(target=self._process_logic, args=(use_tiktok, url), daemon=True).start()

    def _process_logic(self, is_tiktok, url):
        try:
            target_video = self.video_path
            
            # Якщо TikTok - завантажуємо тимчасово
            if is_tiktok:
                self.root.after(0, self.status_label.config, {"text": "Завантаження з TikTok..."})
                temp_video = os.path.join(SETTINGS_DIR, "tk_temp.mp4")
                os.makedirs(SETTINGS_DIR, exist_ok=True)
                
                ydl_opts = {'format': 'best', 'outtmpl': temp_video, 'quiet': True, 'overwrites': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    # Чистимо назву від символів
                    safe_title = "".join(x for x in info.get('title', 'tiktok') if x.isalnum() or x in ' -_').strip()
                target_video = temp_video
                title = safe_title
            else:
                title = os.path.splitext(os.path.basename(self.video_path))[0]

            out_path = os.path.join(self.output_dir, f"{title}.mp3")
            
            # Конвертація з обрізкою
            logger = MyBarLogger(self._update_progress)
            clip = VideoFileClip(target_video)
            
            trim_val = 0.0
            if self.auto_trim.get():
                try: trim_val = float(self.trim_entry.get().replace(',', '.'))
                except: trim_val = 3.0
            
            final_end = clip.duration
            if self.auto_trim.get():
                final_end = max(0, clip.duration - trim_val)
            
            self.root.after(0, self.status_label.config, {"text": "Конвертація в MP3..."})
            
            # Сумісність з MoviePy 1.0 та 2.0
            audio_track = clip.audio
            if hasattr(audio_track, 'subclipped'):
                processed_audio = audio_track.subclipped(0, final_end)
            else:
                processed_audio = audio_track.subclip(0, final_end)
                
            processed_audio.write_audiofile(out_path, logger=logger)
            clip.close()
            
            if is_tiktok and os.path.exists(target_video):
                try: os.remove(target_video)
                except: pass
                
            self.root.after(0, self._finish, True, out_path)
        except Exception as e:
            msg = str(e)
            self.root.after(0, self._finish, False, msg)

    def _update_progress(self, val, *args, **kwargs):
        # Використовуємо self.root.after для безпечного оновлення з іншого потоку
        self.root.after(0, lambda: self.progress_bar.config(value=val))

    def _finish(self, success, msg):
        self.btn_convert.config(state="normal", bg=ACCENT)
        if success:
            file_name = os.path.basename(msg)
            self.status_label.config(text=f"ЗБЕРЕЖЕНО: {file_name}", fg=ACCENT)
            messagebox.showinfo("Успіх", f"Збережено:\n{msg}")
        else:
            self.status_label.config(text="ПОМИЛКА ОБРОБКИ", fg="#ff4444")
            messagebox.showerror("Помилка", msg)

    def show_help(self):
        help_text = (
            "📖 ЯК КОРИСТУВАТИСЬ ПРОГРАМОЮ:\n\n"
            "1. Виберіть папку для збереження (за замовчуванням — Робочий стіл).\n"
            "2. Вставте посилання або виберіть файл на комп'ютері.\n"
            "   💡 Можна використовувати НЕ ТІЛЬКИ TikTok, а й YouTube, Instagram та багато інших сайтів!\n"
            "3. Налаштуйте авто-обрізку (якщо потрібно прибрати заставку в кінці).\n"
            "4. Натисніть 'КОНВЕРТУВАТИ В MP3' та дочекайтеся завершення.\n\n"
            "--------------------------------------------------\n"
            "🌟 Програма розроблена персонально для Олега Сотника"
        )
        messagebox.showinfo("Довідка та Інструкція", help_text)

    def check_for_updates(self):
        """Перевіряє наявність нової версії на сервері."""
        def _check():
            try:
                with urllib.request.urlopen(UPDATE_URL, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    remote_version = data.get("version")
                    download_url = data.get("url")
                    notes = data.get("notes", "")

                    if remote_version and remote_version > VERSION:
                        self.root.after(0, lambda: self.prompt_update(remote_version, download_url, notes))
            except Exception as e:
                print(f"Update check failed: {e}")

        threading.Thread(target=_check, daemon=True).start()

    def prompt_update(self, new_version, download_url, notes):
        """Запитує користувача про оновлення."""
        msg = f"Доступна нова версія: {new_version}\n\nЩо нового:\n{notes}\n\nБажаєте оновити зараз?"
        if messagebox.askyesno("Оновлення", msg):
            self._start_update_download(download_url)

    def _start_update_download(self, url):
        """Завантажує нову версію в окремому потоці."""
        self.status_label.config(text="Завантаження оновлення...", fg=ACCENT)
        self.btn_convert.config(state="disabled")

        def _download():
            try:
                temp_exe = os.path.join(SETTINGS_DIR, "converter_new.exe")
                os.makedirs(SETTINGS_DIR, exist_ok=True)
                
                urllib.request.urlretrieve(url, temp_exe)
                self.root.after(0, self._apply_update, temp_exe)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Помилка оновлення", f"Не вдалося завантажити: {e}"))
                self.root.after(0, lambda: self.btn_convert.config(state="normal"))

        threading.Thread(target=_download, daemon=True).start()

    def _apply_update(self, new_exe_path):
        """Створює бат-файл для заміни поточного EXE та перезапуску."""
        current_exe = sys.executable
        if not current_exe.endswith(".exe"):
            # Якщо запущено як скрипт, просто повідомляємо про завершення завантаження
            messagebox.showinfo("Оновлення", f"Нова версія завантажена в:\n{new_exe_path}\n(Оскільки ви запустили скрипт, автоматична заміна неможлива)")
            return

        batch_path = os.path.join(SETTINGS_DIR, "update.bat")
        
        # Код бат-файлу:
        # 1. Зачекати поки закриється програма
        # 2. Видалити стару версію
        # 3. Перемістити нову на місце старої
        # 4. Запустити нову версію
        # 5. Видалити бат-файл
        batch_content = f"""
@echo off
timeout /t 2 /nobreak > nul
:retry
del /f /q "{current_exe}"
if exist "{current_exe}" (
    timeout /t 1 /nobreak > nul
    goto retry
)
move /y "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
        try:
            with open(batch_path, "w", encoding="cp1251") as f:
                f.write(batch_content)
            
            subprocess.Popen(["cmd.exe", "/c", batch_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            self.root.quit()
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося запустити процес оновлення: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConverterApp(root)
    root.mainloop()
