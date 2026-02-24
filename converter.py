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


THEMES = {
    "dark": {
        "bg_main": "#121212",
        "bg_surface": "#1e1e1e",
        "accent": "#1db954",
        "text_main": "#ffffff",
        "text_dim": "#b3b3b3",
        "entry_bg": "#2a2a2a",
        "btn_bg": "#3e3e3e",
        "btn_active": "#333333"
    },
    "light": {
        "bg_main": "#e8e4db",
        "bg_surface": "#f5f2eb",
        "accent": "#1db954",
        "text_main": "#282828",
        "text_dim": "#6a6a6a",
        "entry_bg": "#efece6",
        "btn_bg": "#dbd6ca",
        "btn_active": "#ccc7ba"
    }
}
CURRENT_THEME = "dark"

def get_color(key):
    return THEMES[CURRENT_THEME][key]

# Шлях до файлу конфігурації
SETTINGS_DIR = os.path.join(os.getenv('APPDATA'), 'VideoToMP3Converter')
SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'settings.json')

# --- ОНОВЛЕННЯ ---
VERSION = "1.1.0"
UPDATE_URL = "https://raw.githubusercontent.com/valick18/VideoToMp3/main/version.json"

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
        self.root.geometry("600x670")
        
        self.video_path = ""
        self.auto_trim = tk.BooleanVar(value=False) # Вимкнено за замовчуванням
        self.last_source = None # "tiktok" або "file"
        self.mode = "link" # "link" або "file"
        self.theme = "dark" # Початкова тема
        
        self.load_settings()
        self.setup_ui()
        
        # Перевірка оновлень після запуску UI
        self.root.after(1000, self.check_for_updates)

    def setup_ui(self):
        self.theme_colors = THEMES[self.theme]
        self.root.configure(bg=self.theme_colors["bg_main"])
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Horizontal.TProgressbar", thickness=10, troughcolor="#333", background=self.theme_colors["accent"], borderwidth=0)
        
        self.main_container = tk.Frame(self.root, bg=self.theme_colors["bg_main"], padx=30, pady=20)
        self.main_container.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(self.main_container, bg=self.theme_colors["bg_main"])
        header.pack(fill="x", pady=(0, 20))
        
        self.label_title1 = tk.Label(header, text="TikTok & Video", font=("Segoe UI", 20, "bold"), bg=self.theme_colors["bg_main"], fg=self.theme_colors["accent"])
        self.label_title1.pack(side="left")
        self.label_title2 = tk.Label(header, text=" to MP3", font=("Segoe UI", 20, "bold"), bg=self.theme_colors["bg_main"], fg=self.theme_colors["text_main"])
        self.label_title2.pack(side="left")

        # Кнопки в заголовку (Тема та Довідка)
        header_btns = tk.Frame(header, bg=self.theme_colors["bg_main"])
        header_btns.pack(side="right")

        # Перемикач теми
        theme_icon = "☾" if self.theme == "dark" else "☼"
        theme_fg = self.theme_colors["text_main"] if self.theme == "dark" else self.theme_colors["accent"]
        self.btn_theme = tk.Button(header_btns, text=theme_icon, command=self.toggle_theme, bg=self.theme_colors["bg_surface"], fg=theme_fg, font=("Segoe UI", 14), relief="flat", width=3, height=1, cursor="hand2", activebackground=self.theme_colors["btn_active"])
        self.btn_theme.pack(side="left", padx=5)

        help_fg = self.theme_colors["text_main"] if self.theme == "dark" else self.theme_colors["accent"]
        self.btn_help = tk.Button(header_btns, text="?", command=self.show_help, bg=self.theme_colors["bg_surface"], fg=help_fg, font=("Segoe UI", 14, "bold"), relief="flat", width=3, height=1, cursor="hand2", activebackground=self.theme_colors["btn_active"])
        self.btn_help.pack(side="left")

        # Folder Selection
        self.dir_frame = tk.Frame(self.main_container, bg=self.theme_colors["bg_surface"], padx=20, pady=15)
        self.dir_frame.pack(fill="x", pady=(0, 20))
        
        self.label_dir_tag = tk.Label(self.dir_frame, text="Папка збереження:", font=("Segoe UI", 9, "bold"), bg=self.theme_colors["bg_surface"], fg=self.theme_colors["text_dim"])
        self.label_dir_tag.pack(side="left")
        self.btn_dir = tk.Button(self.dir_frame, text="📂 ВИБРАТИ ПАПКУ", command=self.select_directory, bg=self.theme_colors["btn_bg"], fg=self.theme_colors["text_main"], font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=8, cursor="hand2")
        self.btn_dir.pack(side="right")
        
        self.label_dir_path = tk.Label(self.dir_frame, text=self.output_dir, bg=self.theme_colors["bg_surface"], fg=self.theme_colors["accent"], font=("Segoe UI", 9, "italic"))
        self.label_dir_path.pack(side="left", padx=10)

        # Перемикач режимів (Link vs File)
        self.mode_frame = tk.Frame(self.main_container, bg=self.theme_colors["bg_main"])
        self.mode_frame.pack(fill="x", pady=(0, 15))
        
        self.btn_mode_link = tk.Button(self.mode_frame, text="🔗 ПОСИЛАННЯ", command=lambda: self.switch_mode("link"), bg=self.theme_colors["accent"], fg="#000", font=("Segoe UI", 10, "bold"), relief="flat", padx=20, pady=10, cursor="hand2")
        self.btn_mode_link.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        self.btn_mode_file = tk.Button(self.mode_frame, text="📂 ЛОКАЛЬНИЙ ФАЙЛ", command=lambda: self.switch_mode("file"), bg=self.theme_colors["btn_bg"], fg=self.theme_colors["text_main"], font=("Segoe UI", 10, "bold"), relief="flat", padx=20, pady=10, cursor="hand2")
        self.btn_mode_file.pack(side="left", expand=True, fill="x", padx=(5, 0))

        # TikTok Section
        self.tk_frame = tk.Frame(self.main_container, bg=self.theme_colors["bg_surface"], padx=20, pady=20)
        self.tk_frame.pack(fill="x", pady=(0, 20))
        
        tk_header = tk.Frame(self.tk_frame, bg=self.theme_colors["bg_surface"])
        tk_header.pack(fill="x", pady=(0, 10))
        self.label_tk_tag = tk.Label(tk_header, text="TikTok, YouTube, Instagram посилання", font=("Segoe UI", 10, "bold"), bg=self.theme_colors["bg_surface"], fg=self.theme_colors["text_dim"])
        self.label_tk_tag.pack(side="left")
        
        # Кнопка очищення
        self.btn_clear = tk.Button(tk_header, text="✕ ОЧИСТИТИ", command=self.clear_url, bg=self.theme_colors["bg_surface"], fg="#ff4444", font=("Segoe UI", 8, "bold"), relief="flat", padx=5, cursor="hand2")
        # self.btn_clear.pack(side="right") # Ховається за замовчуванням
        
        self.url_var = tk.StringVar(value="Вставте посилання тут...")
        self.url_var.trace_add("write", lambda *args: self.on_url_change())
        
        self.url_container = tk.Frame(self.tk_frame, bg=self.theme_colors["entry_bg"], borderwidth=1, highlightthickness=0)
        self.url_container.pack(fill="x", pady=(0, 10))
        self.url_container.config(highlightbackground=self.theme_colors["btn_bg"], highlightthickness=1)

        # ПАКУЄМО СНАЧАЛА КНОПКУ СПРАВА, ПОТІМ ПОЛЕ
        self.btn_paste = tk.Button(self.url_container, text="📋", command=self.paste_url, bg=self.theme_colors["entry_bg"], fg=self.theme_colors["text_main"], font=("Segoe UI", 14), relief="flat", padx=10, cursor="hand2", activebackground=self.theme_colors["btn_active"])
        self.btn_paste.pack(side="right")

        self.url_entry = tk.Entry(self.url_container, textvariable=self.url_var, font=("Segoe UI", 12), bg=self.theme_colors["entry_bg"], fg=self.theme_colors["text_main"], insertbackground=self.theme_colors["text_main"], borderwidth=0)
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(15, 0)) # Прибираємо padx справа
        self.url_entry.bind("<FocusIn>", lambda e: self.url_entry.delete(0, tk.END) if "Вставте" in self.url_entry.get() else None)

        # Local File Section
        self.file_frame = tk.Frame(self.main_container, bg=self.theme_colors["bg_surface"], padx=20, pady=20)
        self.file_frame.pack(fill="x", pady=(0, 20))
        
        self.btn_select = tk.Button(self.file_frame, text="📂 ВИБРАТИ ФАЙЛ НА ПК", command=self.select_video, bg=self.theme_colors["btn_bg"], fg=self.theme_colors["text_main"], font=("Segoe UI", 11, "bold"), relief="flat", pady=10, cursor="hand2")
        self.btn_select.pack(fill="x")
        self.label_file = tk.Label(self.file_frame, text="Файл не вибрано", bg=self.theme_colors["bg_surface"], fg=self.theme_colors["text_dim"], font=("Segoe UI", 9, "italic"))
        self.label_file.pack(pady=(5, 0))

        # Trim Settings
        self.trim_frame = tk.Frame(self.main_container, bg=self.theme_colors["bg_surface"], padx=20, pady=15)
        self.trim_frame.pack(fill="x", pady=(0, 30))
        
        self.cb_trim = tk.Checkbutton(self.trim_frame, text="Авто-обрізка кінця аудіофайла:", variable=self.auto_trim, bg=self.theme_colors["bg_surface"], fg=self.theme_colors["text_main"], selectcolor="#000" if self.theme == "dark" else "#fff", activebackground=self.theme_colors["bg_surface"], activeforeground=self.theme_colors["accent"], font=("Segoe UI", 10), cursor="hand2")
        self.cb_trim.pack(side="left")

        self.trim_entry = tk.Entry(self.trim_frame, width=4, font=("Segoe UI", 10, "bold"), bg=self.theme_colors["entry_bg"], fg=self.theme_colors["accent"], borderwidth=0, highlightthickness=1, highlightbackground=self.theme_colors["btn_bg"], justify="center")
        self.trim_entry.pack(side="left", padx=10)
        self.trim_entry.insert(0, "3.0")
        self.label_sec = tk.Label(self.trim_frame, text="сек.", bg=self.theme_colors["bg_surface"], fg=self.theme_colors["text_dim"], font=("Segoe UI", 10))
        self.label_sec.pack(side="left")

        # Convert Button
        self.btn_convert = tk.Button(self.main_container, text="🔥 КОНВЕРТУВАТИ В MP3", command=self.start_conversion, bg=self.theme_colors["accent"], fg="#000" if self.theme == "dark" else "#fff", font=("Segoe UI", 16, "bold"), relief="flat", pady=18, cursor="hand2", activebackground="#1ed760")
        self.btn_convert.pack(fill="x")

        # Progress & Status
        self.progress_bar = ttk.Progressbar(self.main_container, style="Horizontal.TProgressbar", mode="determinate")
        self.progress_bar.pack(fill="x", pady=(20, 5))
        
        self.status_label = tk.Label(self.main_container, text="Готово до роботи", font=("Segoe UI", 9), bg=self.theme_colors["bg_main"], fg=self.theme_colors["text_dim"])
        self.status_label.pack()

        # Початковий стан режимів
        self.switch_mode("link")

    def switch_mode(self, mode):
        self.mode = mode
        if mode == "link":
            self.tk_frame.pack(fill="x", pady=(0, 20), after=self.mode_frame)
            self.file_frame.pack_forget()
            self.btn_mode_link.config(bg=self.theme_colors["accent"], fg="#000")
            self.btn_mode_file.config(bg=self.theme_colors["btn_bg"], fg=self.theme_colors["text_main"])
        else:
            self.file_frame.pack(fill="x", pady=(0, 20), after=self.mode_frame)
            self.tk_frame.pack_forget()
            self.btn_mode_file.config(bg=self.theme_colors["accent"], fg="#000")
            self.btn_mode_link.config(bg=self.theme_colors["btn_bg"], fg=self.theme_colors["text_main"])

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.save_settings()
        # Повне оновлення UI
        for widget in self.root.winfo_children():
            widget.destroy()
        self.setup_ui()
        # Повертаємо посилання на папку та файл
        self.label_dir_path.config(text=self.output_dir)
        if self.video_path:
            self.label_file.config(text=os.path.basename(self.video_path), fg=self.theme_colors["accent"])

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
                    self.theme = settings.get('theme', 'dark')
            except: pass

    def save_settings(self):
        try:
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump({'output_dir': self.output_dir, 'theme': self.theme}, f, ensure_ascii=False, indent=4)
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
            self.label_file.config(text=os.path.basename(path), fg=self.theme_colors["accent"])
            # Якщо є посилання, натякаємо що зараз пріоритет у файлу
            if self.url_var.get() and "Вставте" not in self.url_var.get():
                self.status_label.config(text="Пріоритет: Локальний файл", fg=self.theme_colors["accent"])

    def clear_url(self):
        self.url_var.set("")
        if self.last_source == "tiktok":
            self.last_source = "file" if self.video_path else None
        self.status_label.config(text="Посилання видалено", fg=self.theme_colors["text_dim"])
        self.btn_clear.pack_forget() # Ховаємо кнопку після очищення

    def on_url_change(self):
        val = self.url_var.get().strip()
        if val and "Вставте" not in val and val != "":
            self.last_source = "tiktok"
            if self.video_path:
                self.status_label.config(text="Пріоритет: TikTok посилання", fg=self.theme_colors["accent"])
            # Показуємо кнопку очищення
            self.btn_clear.pack(side="right")
        else:
            # Ховаємо кнопку очищення, якщо поле порожнє або містить плейсхолдер
            self.btn_clear.pack_forget()

    def paste_url(self):
        try:
            cb = self.root.clipboard_get()
            if "http" in cb:
                self.url_var.set(cb)
                self.last_source = "tiktok"
        except: pass

    def start_conversion(self):
        url = self.url_var.get().strip()
        is_tiktok_url = url.startswith("http")
        
        # Визначаємо пріоритет на основі обраного режиму
        use_tiktok = False
        if self.mode == "link":
            if not is_tiktok_url or "Вставте" in url:
                messagebox.showwarning("Помилка", "Вставте коректне посилання!")
                return
            use_tiktok = True
        else:
            if not self.video_path:
                messagebox.showwarning("Помилка", "Виберіть файл на комп'ютері!")
                return
            use_tiktok = False
            
        self.btn_convert.config(state="disabled", bg="#333")
        self.status_label.config(text="Запуск процесу...", fg=self.theme_colors["accent"])
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
        self.btn_convert.config(state="normal", bg=self.theme_colors["accent"])
        if success:
            file_name = os.path.basename(msg)
            self.status_label.config(text=f"ЗБЕРЕЖЕНО: {file_name}", fg=self.theme_colors["accent"])
            messagebox.showinfo("Успіх", f"Збережено:\n{msg}")
        else:
            self.status_label.config(text="ПОМИЛКА ОБРОБКИ", fg="#ff4444")
            messagebox.showerror("Помилка", msg)

    def show_help(self):
        help_window = tk.Toplevel(self.root)
        help_window.title("Довідка та Інструкція")
        help_window.geometry("520x600")
        help_window.configure(bg=self.theme_colors["bg_surface"])
        help_window.resizable(False, False)
        help_window.transient(self.root) # Поверх головного вікна
        help_window.grab_set() # Блокує взаємодію з головним вікном
        
        # Центрування відносно головного вікна
        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 260
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 300
        help_window.geometry(f"+{x}+{y}")

        content = tk.Frame(help_window, bg=self.theme_colors["bg_surface"], padx=30, pady=30)
        content.pack(fill="both", expand=True)

        tk.Label(content, text="📖 ІНСТРУКЦІЯ ТА МОЖЛИВОСТІ", font=("Segoe UI", 14, "bold"), bg=self.theme_colors["bg_surface"], fg=self.theme_colors["accent"]).pack(pady=(0, 20))

        help_text = (
            "🔗 ПОСИЛАННЯ: Вставте лінк (TikTok, YT, Insta) та тисніть 'Конвертувати'.\n\n"
            "📂 ФАЙЛ: Оберіть відео на ПК та тисніть 'Конвертувати'.\n\n"
            "⚙️ ОПЦІЇ: Авто-обрізка аудіо та зміна папки зверху.\n\n"
            "🌓 ТЕМА: Кнопка ☾/☼ для перемикання кольорів.\n\n"
            "--------------------------------------------------\n"
            "🌟 Спеціально розроблено для Олега Сотника"
        )
        
        desc = tk.Label(content, text=help_text, font=("Segoe UI", 11), bg=self.theme_colors["bg_surface"], fg=self.theme_colors["text_main"], justify="left", wraplength=460)
        desc.pack(fill="both", expand=True)

        tk.Button(content, text="ЗАКРИТИ", command=help_window.destroy, bg=self.theme_colors["accent"], fg="#000", font=("Segoe UI", 10, "bold"), relief="flat", pady=10, cursor="hand2", activebackground="#1ed760").pack(fill="x", pady=(20, 0))

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
        self.status_label.config(text="Завантаження оновлення...", fg=self.theme_colors["accent"])
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
