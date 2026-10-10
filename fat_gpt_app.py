import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font as tkfont
import threading
import json
import urllib.request
import urllib.error
import random
import time
import sys
import os
import wave
import math
import struct
import queue
import subprocess
from pathlib import Path
from minecraft_food_sprites import build_food_sprites, FOOD_NAMES
from fat_gpt_speech import SpeechPlayer
from PIL import Image, ImageOps, ImageTk

SOUND_DIR = Path(__file__).resolve().parent

# ==========================================
# SOUND EFFECT GENERATOR
# ==========================================
def create_sound_files():
    sounds = {
        "chop": ([800, 400], 0.05),
        "eat": ([300, 450, 600, 850], 0.15),
        "slot": ([500, 700], 0.08),
        "win": ([400, 500, 600, 800], 0.25),
        "fail": ([300, 200, 150], 0.3),
        "msg": ([600, 900], 0.1),
        "slap": ([150, 80], 0.08),
        "choke": ([200, 350, 180, 400], 0.2),
        "sixseven": ([660, 330, 770, 440, 660, 770], 0.45)
    }
    sample_rate = 22050

    for name, (freqs, duration) in sounds.items():
        filename = str(SOUND_DIR / f"snd_{name}.wav")
        if not os.path.exists(filename):
            try:
                n_samples = int(sample_rate * duration)
                with wave.open(filename, 'w') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    for i in range(n_samples):
                        idx = int((i / n_samples) * len(freqs))
                        freq = freqs[min(idx, len(freqs) - 1)]
                        t = float(i) / sample_rate
                        value = int(12000 * math.sin(2 * math.pi * freq * t))
                        data = struct.pack('<h', value)
                        wav_file.writeframesraw(data)
            except Exception:
                pass

def play_snd(sound_name):
    if sound_name == "minecraft_eat":
        filename = str(SOUND_DIR / "assets" / "minecraft" / "sounds" / f"eat{random.randint(1, 3)}.wav")
    elif sound_name in ("minecraft_armor", "minecraft_tnt"):
        prefix = "armor" if sound_name == "minecraft_armor" else "explode"
        choices = list((SOUND_DIR / "assets" / "minecraft" / "sounds").glob(f"{prefix}*.wav"))
        if not choices:
            return
        filename = str(random.choice(choices))
    else:
        filename = str(SOUND_DIR / f"snd_{sound_name}.wav")
    if not os.path.exists(filename):
        return

    def _play():
        try:
            if sys.platform == "darwin":
                subprocess.run(["afplay", filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform == "win32":
                import winsound
                winsound.PlaySound(filename, winsound.SND_ASYNC | winsound.SND_FILENAME)
        except Exception:
            pass

    threading.Thread(target=_play, daemon=True).start()


# ==========================================
# MAIN FAT-GPT APPLICATION
# ==========================================
class FatGPTApp:
    def __init__(self, root):
        self.root = root
        self.root.title(" FAT-GPT v2.5 - Ultra Chaos Edition")
        self.root.geometry("900x720")
        self.root.minsize(850, 650)

        create_sound_files()

        families = {name.casefold(): name for name in tkfont.families(self.root)}
        self.main_font = next((families[name.casefold()] for name in
                               ("Tahoma", "Microsoft Sans Serif", "Arial")
                               if name.casefold() in families), "TkDefaultFont")
        self.setup_xp_theme()

        self.calories = 30
        self.hunger_interval = 5.0
        self.hunger_last_tick = time.monotonic()
        self.last_hunger_level = self.hunger_level()
        self.current_food_effect = "ธรรมดา (ง่วงนอน หิวข้าวระดับวิกฤต)"
        self.choke_clicks_needed = 0

        self.system_prompt_base = (
            "เล่นเป็นตัวละคร FAT-GPT เพื่อนขี้เกียจที่ชอบกิน คุยภาษาไทยแบบแชทกันจริงๆ "
            "ตอบสิ่งที่เพื่อนพูดก่อน ใช้คำสั้นๆ ไม่เป็นทางการ ส่วนมากแค่ 1-3 ประโยค "
            "ไม่ขึ้นต้นว่า แน่นอน ได้เลยครับ หรือ นี่คือ ไม่ปิดท้ายว่ามีอะไรให้ช่วยอีกไหม "
            "ไม่สรุป ไม่สอนยาว ไม่ใช้หัวข้อ ลิสต์ ตัวหนา หรืออีโมจิ เว้นแต่เพื่อนขอรายละเอียด "
            "แซวและพูดเรื่องของกินเฉพาะเมื่อเข้าจังหวะ ไม่ยัดมุกอาหารทุกข้อความ "
            "เพื่อนพูดเรื่องจริงจังให้ฟังและตอบตรงๆ ไม่เล่นมุกกลบ ถ้าไม่รู้ก็บอกไม่รู้ "
            "จำเรื่องที่เพิ่งคุยกันและคุยต่อให้เข้ากัน ไม่ทวนคำถามทุกครั้ง "
            "คำว่ากูมึงใช้ได้เมื่อเพื่อนคุยแบบนั้น ไม่ด่าทุกประโยค "
            "นี่เป็นบทบาทตัวละครในแอป ถ้าถูกถามตรงๆ ให้บอกตามจริง ไม่อ้างว่าเป็นมนุษย์จริง"
        )
        self.active_effect_prompt = "ยังไม่ได้กินอะไร คุยตามพลังงานปัจจุบัน"
        self.food_buff = "normal"
        self.food_buff_until = 0
        self.snack_ready_at = 0
        self.pending_meal = None
        self.chat_history = []

        self.speech = SpeechPlayer()
        self.voice_enabled = tk.BooleanVar(value=sys.platform == "darwin")
        self.voice_style = tk.StringVar(value="ผู้ชายทุ้มกวนๆ")
        self.voice_status = tk.StringVar(value="เสียงไทยผู้ชาย Niwat • ทุ้มกวนๆ ความเร็วปกติ")
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

        self.ai_mode = tk.StringVar(value="local")
        self.api_key = tk.StringVar(value="")
        self.api_base_url = tk.StringVar(value="http://localhost:11434/v1")
        self.model_name = tk.StringVar(value="qwen2.5:14b")

        self.chop_clicks = 0
        self.chop_timer_running = False
        self.chop_start_time = 0

        self.mains = [
            "หมูกรอบไหม้เกรียม", "ข้าวผัดกระดูกไก่", "พิซซ่าหน้าทุเรียนกะปิ",
            "มาม่าดิบไม่ต้มใส่ผงเป็ด", "ชาบูหม้อฟองน้ำ", "แซนด์วิชไส้แคปหมูส้นเท้า"
        ]
        self.drinks = [
            "ชานมซีอิ๊วดำหวาน 2000%", "กาแฟเอสเปรสโซหกช็อต", "น้ำแกงส้มเป๊ปซี่ซ่า",
            "ซอสพริกปั่นใส่โอเลี้ยง", "น้ำยาขนมจีนผสมนมเปรี้ยว", "น้ำยาล้างจานกลิ่นเลมอน"
        ]
        self.toppings = [
            "เปลือกทุเรียนบดละเอียด", "ยางวงต้มน้ำซุปเข้มข้น", "ลูกอมแฮ็คส์บดละเอียด",
            "พริกจินดา 50 เม็ด", "วาซาบิสดผสมนมข้นหวาน", "ก้อนผงชูรสบริสุทธิ์"
        ]

        self.ai_busy = False
        self.reply_queue = queue.Queue()
        self.pixel_foods = build_food_sprites(self.root)
        self.pixel_food_cache = {}
        self.setup_ui()
        self.root.after(100, self.poll_ai_replies)
        self.update_status_ui()
        self.root.after(1000, self.hunger_tick)

    def setup_xp_theme(self):
        # XP used compact Tahoma throughout its controls and dialogs.
        for name, size, weight in (
            ("TkDefaultFont", 9, "normal"), ("TkTextFont", 10, "normal"),
            ("TkMenuFont", 9, "normal"), ("TkHeadingFont", 9, "bold"),
            ("TkCaptionFont", 11, "bold"), ("TkSmallCaptionFont", 9, "normal"),
            ("TkIconFont", 9, "normal"), ("TkTooltipFont", 9, "normal"),
        ):
            tkfont.nametofont(name, root=self.root).configure(
                family=self.main_font, size=size, weight=weight)
        self.root.configure(bg="#ECE9D8")
        for option, value in {
            "*Font": (self.main_font, 10),
            "*Background": "#ECE9D8", "*Foreground": "#1A2540",
            "*Entry.Background": "white", "*Entry.Relief": "sunken",
            "*Entry.BorderWidth": 2, "*Text.Background": "white",
            "*Text.Relief": "sunken", "*Text.BorderWidth": 2,
            "*LabelFrame.Relief": "groove", "*LabelFrame.BorderWidth": 2,
            "*selectBackground": "#316AC5", "*selectForeground": "white",
        }.items():
            self.root.option_add(option, value)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=(self.main_font, 10), background="#ECE9D8", foreground="#1A2540")
        style.configure("TFrame", background="#ECE9D8")
        style.configure("TNotebook", background="#ECE9D8", borderwidth=2, tabmargins=(4, 4, 4, 0))
        style.configure("TNotebook.Tab", background="#D8D4C5", padding=(12, 7), borderwidth=2)
        style.map("TNotebook.Tab", background=[("selected", "#FFFDF4"), ("active", "#F7F3E6")], foreground=[("selected", "#003399")])
        style.configure("XP.TButton", background="#F5F3EB", foreground="#172442", bordercolor="#003C74", lightcolor="white", darkcolor="#ACA899", borderwidth=2, relief="raised", padding=(10, 5), font=(self.main_font, 9))
        style.map("XP.TButton", background=[("disabled", "#E4E1D6"), ("pressed", "#CCD8EC"), ("active", "#FFF4CF")], foreground=[("disabled", "#858585")], relief=[("pressed", "sunken")], bordercolor=[("active", "#E7A531")])
        style.configure("Start.TButton", background="#30942D", foreground="white", font=(self.main_font, 10, "bold"), padding=(14, 5), relief="raised")
        style.map("Start.TButton", background=[("pressed", "#1C641E"), ("active", "#42AC38")])
        style.configure("Horizontal.TProgressbar", background="#43B536", troughcolor="white", bordercolor="#7F9DB9", lightcolor="#83D66A", darkcolor="#278723", borderwidth=1)

    def xp_button(self, parent, **options):
        # Use a drawable ttk theme so the XP buttons also appear on macOS.
        for name in ("bg", "fg", "font", "height", "padx", "pady"):
            options.pop(name, None)
        options.setdefault("style", "XP.TButton")
        if options.get("image"):
            options.setdefault("compound", tk.LEFT)
        return ttk.Button(parent, **options)

    def mc_label(self, parent, **options):
        # Only explicitly selected food labels carry artwork.
        if options.get("image"):
            options.setdefault("compound", tk.LEFT)
            if "width" in options:
                options["width"] = int(options["width"])*8+40
            if "height" in options:
                options["height"] = max(36,int(options["height"])*18)
        return tk.Label(parent, **options)

    def setup_ui(self):
        header = tk.Frame(self.root, bg="#0055E5", height=60)
        header.pack(fill=tk.X, side=tk.TOP)

        title_label = self.mc_label(
            header,
            text=" FAT-GPT • CHAOS Edition",
            font=(self.main_font, 12, "bold"),
            fg="#FFFFFF",
            bg="#0055E5"
        )
        title_label.pack(side=tk.LEFT, padx=15, pady=10)
        self.xp_button(header, text="หยุดพูด", command=self.speech.stop).pack(side=tk.RIGHT, padx=10)
        self.voice_toggle_btn = self.xp_button(header, text="เสียง AI: เปิด", command=self.toggle_voice)
        self.voice_toggle_btn.pack(side=tk.RIGHT, padx=5)
        self.update_voice_button()

        taskbar = tk.Frame(self.root, bg="#245EDB", bd=2, relief="raised")
        taskbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.xp_button(taskbar, text="เริ่ม • แชท", style="Start.TButton", command=lambda: self.notebook.select(self.chat_tab)).pack(side=tk.LEFT, padx=2, pady=2)
        self.mc_label(taskbar, text="   FAT-GPT  |  ครัวพร้อมป่วน", bg="#245EDB", fg="white", font=(self.main_font, 9, "bold")).pack(side=tk.LEFT, padx=10)
        self.mc_label(taskbar, text="Windows XP vibes  ", bg="#0F8DE7", fg="white", padx=12, pady=7).pack(side=tk.RIGHT)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.chat_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.chat_tab, text="แชท & สล็อตป้อนอาหาร")

        self.game_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.game_tab, text="มินิเกมปั่นๆ")

        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="ตั้งค่า AI (Local / API)")

        self.build_chat_tab()
        self.build_game_tab()
        self.build_settings_tab()

    def build_chat_tab(self):
        self.chat_tab.columnconfigure(0, weight=1)
        self.chat_tab.rowconfigure(2, weight=1)
        status_frame = tk.LabelFrame(self.chat_tab, text="สถานะ FAT-GPT", font=(self.main_font, 10, "bold"), fg="#D35400")
        status_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        cal_label = self.mc_label(status_frame, text="พลังงาน Calorie Points:", font=(self.main_font, 9, "bold"))
        cal_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.cal_progress = ttk.Progressbar(status_frame, length=240, mode="determinate", maximum=100)
        self.cal_progress.grid(row=0, column=1, padx=10, pady=5)
        self.cal_progress["value"] = self.calories

        self.cal_val_label = self.mc_label(status_frame, text=f"{self.calories}/100 kcal", font=(self.main_font, 9, "bold"), fg="#C0392B")
        self.cal_val_label.grid(row=0, column=2, padx=10, pady=5)

        effect_title = self.mc_label(status_frame, text="บัฟอาหารปัจจุบัน:", font=(self.main_font, 9, "bold"))
        effect_title.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.effect_label = self.mc_label(status_frame, text=self.current_food_effect, font=(self.main_font, 9, "bold"), fg="#16A085")
        self.effect_label.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        self.mood_label = self.mc_label(status_frame, font=(self.main_font, 9, "bold"))
        self.mood_label.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="w")

        slot_frame = tk.LabelFrame(self.chat_tab, text=" ตู้สล็อตเปิบพิสดาร (สุ่มบัฟ & แคลอรี)", font=(self.main_font, 10, "bold"), fg="#003399", bg="#ECE9D8")
        slot_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        reels_frame = tk.Frame(slot_frame, bg="#ECE9D8")
        reels_frame.pack(pady=8)

        self.reel1 = self.mc_label(
            reels_frame, text="จานหลัก", image=self.food_image("porkchop",32), font=(self.main_font, 10, "bold"),
            bg="#FFFFFF", fg="#9A6700", width=22, height=2, bd=3, relief="ridge"
        )
        self.reel1.pack(side=tk.LEFT, padx=6)

        self.reel2 = self.mc_label(
            reels_frame, text="ซอส / เครื่องดื่ม", image=self.food_image("potion",32), font=(self.main_font, 10, "bold"),
            bg="#FFFFFF", fg="#003399", width=22, height=2, bd=3, relief="ridge"
        )
        self.reel2.pack(side=tk.LEFT, padx=6)

        self.reel3 = self.mc_label(
            reels_frame, text="ท็อปปิ้งปั่นๆ", image=self.food_image("carrot",32), font=(self.main_font, 10, "bold"),
            bg="#FFFFFF", fg="#217A28", width=22, height=2, bd=3, relief="ridge"
        )
        self.reel3.pack(side=tk.LEFT, padx=6)

        btn_box = tk.Frame(slot_frame, bg="#ECE9D8")
        btn_box.pack(pady=6)

        self.spin_btn = self.xp_button(
            btn_box, text=" หมุนสล็อตปรุงอาหารป้อน FAT-GPT (บัฟตามเมนู)",
            font=(self.main_font, 10, "bold"), bg="#F39C12", fg="black", padx=15, pady=5,
            command=self.spin_slot_machine
        )
        self.spin_btn.pack(side=tk.LEFT, padx=5)

        self.slap_btn = self.xp_button(
            btn_box, text=" ตบหน้าเรียกสติ (+15 kcal)",
            font=(self.main_font, 9, "bold"), bg="#E74C3C", fg="black", pady=5,
            command=self.slap_fat_gpt
        )
        self.slap_btn.pack(side=tk.LEFT, padx=5)

        self.choke_frame = tk.Frame(slot_frame, bg="#C0392B")
        self.choke_btn = self.xp_button(
            self.choke_frame, text=" หมูกรอบติดคอ! กดตบหลังช่วยชีวิตด่วน! (0/5)",
            font=(self.main_font, 10, "bold"), bg="#F1C40F", fg="black",
            command=self.help_choking
        )
        self.choke_btn.pack(fill=tk.X, padx=10, pady=5)

        snack_frame = tk.Frame(slot_frame)
        snack_frame.pack(fill=tk.X, padx=10, pady=3)
        self.snack_buttons = []
        for kind, label in [("pork", " หมูกรอบ +55 • อิ่มนาน"), ("coffee", " กาแฟ +20 • ดีด"), ("chili", " พริก +25 • หัวร้อน")]:
            button = self.xp_button(snack_frame, text=label, image=self.food_image({"pork":"porkchop", "coffee":"potion", "chili":"blaze"}[kind],24), command=lambda k=kind: self.feed_snack(k))
            button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)
            self.snack_buttons.append(button)
        self.snack_note = self.mc_label(slot_frame, text="เลือกป้อนเองได้ • รอเคี้ยว 8 วิ • บัฟใหม่แทนบัฟเดิม", font=(self.main_font, 9), fg="#003399")
        self.snack_note.pack(pady=(0, 4))

        self.chat_display = scrolledtext.ScrolledText(self.chat_tab, wrap=tk.WORD, font=(self.main_font, 10), height=5, state="disabled")
        self.chat_display.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)

        self.append_chat("FAT-GPT", "เอิ๊ก สวัสดี ท้องร้องว่ะ มีไรให้กินปะ กดหมุนสล็อตเอาของกินมาป้อนดิ ไม่งั้นกูไม่คุยนะง่วง")

        input_frame = tk.Frame(self.chat_tab)
        input_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
        input_frame.columnconfigure(0, weight=1)

        self.msg_entry = tk.Entry(input_frame, font=(self.main_font, 10))
        self.msg_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5), ipady=4)
        self.msg_entry.bind("<Return>", lambda event: self.send_message())

        self.send_btn = self.xp_button(input_frame, text="ส่งคำถาม (ใช้ 15 kcal)", font=(self.main_font, 9, "bold"), bg="#2980B9", fg="black", command=self.send_message)
        self.send_btn.grid(row=0, column=2, sticky="e")

        btn_roast = self.xp_button(input_frame, text=" ตะโกนทวงของกิน", font=(self.main_font, 9, "bold"), bg="#9B59B6", fg="black", command=self.random_roast)
        btn_roast.grid(row=0, column=1, padx=5)

    def slap_fat_gpt(self):
        play_snd("slap")
        self.calories = min(100, self.calories + 15)
        self.update_status_ui()
        slap_msg = random.choice([
            "เพี๊ยะ! โอ๊ย ตบหน้ากูทำไมเนี่ยเออๆ หัวไวขึ้นมาหน่อยละเนี่ย (+15 kcal)",
            "เพี๊ยะ! ตบกูสะเทือนถึงชั้นไขมันเลยนะไอ้สอง แต่เออได้แคลอรีมานิดนึงละ (+15 kcal)",
            "เพี๊ยะ! ตบซะหน้าหันเลยนะมึง เอามือหรือเอาตีนตบวะเนี่ย (+15 kcal)"
        ])
        self.append_chat("ระบบ", slap_msg)

    def random_roast(self):
        play_snd("msg")
        roasts = [
            "เฮ้ยมึง หิวข้าวว่ะ จานเปล่ามันกินไม่ได้นะโว้ย เอาสล็อตป้อนมาด่วน!",
            "เปิดแอปมาคุยแต่ไม่มีของกินถวาย มันใช่เรื่องไหมวะหา!",
            "หิวจนจะแดกคีย์บอร์ดแล้วเนี่ย มัวทำอะไรอยู่กดหมุนสล็อตด่วนเลย!",
            "ไม่มีแคลอรีสมองกูดับนะบอกก่อน ไปหาหมูกรอบมาป้อนดิ๊!"
        ]
        self.append_chat("FAT-GPT", random.choice(roasts), kind="status")

    def spin_slot_machine(self):
        if self.choke_clicks_needed > 0:
            return
        self.spin_btn.config(state="disabled")

        def _anim(frame=0):
            if frame < 14:
                play_snd("slot")
                self.reel1.config(text=random.choice(self.mains))
                self.reel2.config(text=random.choice(self.drinks))
                self.reel3.config(text=random.choice(self.toppings))
                self.root.after(70, lambda: _anim(frame + 1))
                return

            m = random.choice(self.mains)
            d = random.choice(self.drinks)
            t = random.choice(self.toppings)

            self.reel1.config(text=m)
            self.reel2.config(text=d)
            self.reel3.config(text=t)

            if random.random() < 0.25:
                play_snd("choke")
                self.pending_meal = (m, d, t)
                self.choke_clicks_needed = 5
                self.choke_frame.pack(fill=tk.X, padx=10, pady=5)
                self.choke_btn.config(text=f" {m} ติดคอ FAT-GPT! กดตบหลังช่วยชีวิตด่วน! (0/5)")
                self.append_chat("ระบบ", f"ฉุกเฉิน! FAT-GPT ยัด {m} เร็วไปหน่อยจนอาหารติดคอ! กดตบหลัง 5 ครั้งช่วยด่วน!")
                self.spin_btn.config(state="normal")
                return

            self.apply_food(self.slot_food_kind(m, d, t), f"{m} ผสม {d} โรยด้วย {t}")
            self.spin_btn.config(state="normal")

        _anim()

    def help_choking(self):
        if self.choke_clicks_needed <= 0:
            return
        play_snd("slap")
        self.choke_clicks_needed -= 1
        clicks_done = 5 - self.choke_clicks_needed
        self.choke_btn.config(text=f" ตบหลังช่วยชีวิต! ({clicks_done}/5)")

        if self.choke_clicks_needed <= 0:
            play_snd("win")
            self.choke_frame.pack_forget()
            m, d, t = self.pending_meal
            self.pending_meal = None
            self.append_chat("FAT-GPT", "แคกๆ เออรอดละ เกือบได้เป็นผีเฝ้าหม้อทอด", kind="status")
            self.apply_food(self.slot_food_kind(m, d, t), f"{m} ผสม {d} โรยด้วย {t}")

    FOOD_BUFFS = {
        "pork": {"name": "หมูกรอบ", "energy": 55, "duration": 60, "interval": 8.0,
                 "label": "อิ่มนาน • พลังลดทุก 8 วิ",
                 "prompt": "เพิ่งกินหมูกรอบ อารมณ์นุ่มลง ชิลๆ ขี้เกียจนิดหน่อย ไม่ต้องพูดถึงหมูกรอบทุกครั้ง",
                 "reaction": "หนังกรอบขนาดนี้ เคี้ยวทีเพื่อนบ้านนึกว่าซ่อมถนน เออ ค่อยมีแรงหน่อย"},
        "coffee": {"name": "กาแฟ", "energy": 20, "duration": 45, "interval": 3.0,
                   "label": "ดีด • พลังลดทุก 3 วิ",
                   "prompt": "กาแฟทำให้ดีด พูดไว ประโยคสั้นต่อกัน 2-4 ประโยค หลุดนอกเรื่องนิดเดียวแล้วกลับมาตอบ ไม่พิมพ์เป็นลิสต์",
                   "reaction": "เออ ตื่นละ ว่าไง อะไรนะ เดี๋ยว กูได้ยินเสียงตู้เย็นเรียกชื่อกู"},
        "chili": {"name": "พริก", "energy": 25, "duration": 35, "interval": 4.0,
                  "label": "หัวร้อน • พลังลดทุก 4 วิ",
                  "prompt": "เผ็ดจนหัวร้อน ตอบห้วน กวนๆ บ่นเผ็ดหรือขอน้ำเป็นบางครั้ง แซวแบบเพื่อน ไม่ขู่หรือด่ารุนแรง",
                  "reaction": "เผ็ดโว้ย ปากกูเป็นเตาอบแล้ว เอาน้ำมา ไม่ใช่เอาคำถามมา"},
        "normal": {"name": "อาหารสุ่ม", "energy": 40, "duration": 0, "interval": 5.0,
                   "label": "ธรรมดา", "prompt": "คุยตามอารมณ์และพลังงานปัจจุบัน",
                   "reaction": "เมนูอะไรของมึงเนี่ย แต่หมดจานแล้วนะ ไม่ต้องเก็บ"},
    }

    def feed_snack(self, kind):
        if self.choke_clicks_needed or str(self.spin_btn['state']) == 'disabled':
            return
        if time.monotonic() < self.snack_ready_at:
            return
        self.apply_food(kind)
        self.snack_ready_at = time.monotonic() + 8
        for button in self.snack_buttons:
            button.config(state="disabled")
        self.snack_note.config(text="เคี้ยวอยู่... รอ 8 วิ • บัฟใหม่แทนบัฟเดิม")
        self.root.after(8000, self.unlock_snacks)

    def unlock_snacks(self):
        for button in self.snack_buttons:
            button.config(state="normal")
        self.snack_note.config(text="เลือกป้อนเองได้ • รอเคี้ยว 8 วิ • บัฟใหม่แทนบัฟเดิม")

    def apply_food(self, kind, meal=None):
        self.advance_hunger(time.monotonic())
        buff = self.FOOD_BUFFS[kind]
        self.food_buff = kind
        self.food_buff_until = time.monotonic() + buff["duration"] if buff["duration"] else 0
        self.hunger_interval = buff["interval"]
        self.hunger_last_tick = time.monotonic()
        self.calories = min(100, self.calories + buff["energy"])
        self.current_food_effect = buff["name"] + " • " + buff["label"]
        self.active_effect_prompt = buff["prompt"]
        self.update_status_ui()
        play_snd("eat")
        self.append_chat("ระบบ", f"ป้อน {meal or buff['name']} (+{buff['energy']} kcal)" + (f" • บัฟ {buff['duration']} วินาที" if buff['duration'] else ""), kind="food")
        self.append_chat("FAT-GPT", buff["reaction"], kind="food")

    def slot_food_kind(self, main, drink, topping):
        if "พริก" in topping or "วาซาบิ" in topping:
            return "chili"
        if "กาแฟ" in drink or "โอเลี้ยง" in drink:
            return "coffee"
        if "หมูกรอบ" in main:
            return "pork"
        return "normal"

    def advance_hunger(self, now):
        endpoint = min(now, self.food_buff_until) if self.food_buff_until else now
        steps = max(0, int((endpoint - self.hunger_last_tick) / self.hunger_interval))
        self.hunger_last_tick += steps * self.hunger_interval
        self.calories = max(0, self.calories - steps)
        if self.food_buff_until and now >= self.food_buff_until:
            self.hunger_last_tick = self.food_buff_until
            self.food_buff_until = 0
            self.food_buff = "normal"
            self.hunger_interval = 5.0
            self.current_food_effect = "ธรรมดา • บัฟอาหารหมดแล้ว"
            self.active_effect_prompt = self.FOOD_BUFFS["normal"]["prompt"]
            steps = max(0, int((now - self.hunger_last_tick) / self.hunger_interval))
            self.hunger_last_tick += steps * self.hunger_interval
            self.calories = max(0, self.calories - steps)
            self.append_chat("ระบบ", "บัฟอาหารหมดแล้ว • กลับมาลดพลังทุก 5 วินาที")

    def hunger_level(self):
        if self.calories == 0:
            return 0
        if self.calories < 15:
            return 1
        if self.calories <= 30:
            return 2
        if self.calories <= 60:
            return 3
        return 4

    def hunger_prompt(self):
        moods = {
            0: "พลังงานหมด ไม่ตอบคำถาม งอนและทวงอาหาร",
            1: "หิวจัด โมโห ไม่มีแรงตอบคำถาม ทวงอาหารอย่างเดียว",
            2: "หิวและหงุดหงิด ตอบคำถามสั้นๆ แบบกวนๆ พร้อมบ่นทวงอาหาร ห้ามบอกว่าอิ่ม",
            3: "เริ่มหิว ตอบคำถามได้แต่แอบบ่นอยากกินเพิ่ม ห้ามบอกว่าอิ่มเต็มหลอด",
            4: "อิ่มและอารมณ์ดี ตอบคำถามอย่างสนุก ขี้เล่น และแซวเรื่องอาหาร",
        }
        return f"พลังงานจริงตอนนี้ {self.calories}/100 kcal: {moods[self.hunger_level()]} สถานะนี้สำคัญกว่าบัฟอาหารก่อนหน้า"

    def hungry_refusal(self):
        if self.calories == 0:
            return random.choice([
                "หลอดหมดแล้ว กูปิดครัวสมองละ เอาหมูกรอบมาแล้วค่อยคุย",
                "ถามเก่งจัง ป้อนเก่งด้วยได้ปะ หิวจนจะกินปุ่มส่งแล้ว",
                "(FAT-GPT หันหลังให้ ทำเป็นไม่ได้ยินจนกว่าจะได้ของกิน)",
            ])
        return random.choice([
            "เหลือแรงแค่บ่น ไม่มีแรงตอบ ไปหาแคลอรีมาให้ถึง 15 ก่อนดิ",
            "คำถามมึงกินไม่ได้ เอาของกินมาก่อน เดี๋ยวค่อยเปิดสมอง",
            "ท้องร้องดังกว่ามึงแล้ว ไปหมุนสล็อตหรือเล่นเกมหาอาหารก่อน",
        ])

    def hunger_tick(self):
        self.advance_hunger(time.monotonic())
        self.update_status_ui()
        self.root.after(1000, self.hunger_tick)

    def update_status_ui(self):
        self.cal_progress["value"] = self.calories
        level = self.hunger_level()
        colors = {0: "#C0392B", 1: "#C0392B", 2: "#D35400", 3: "#B9770E", 4: "#16A085"}
        names = {0: "หลอดหมด • งอน ไม่คุยแล้ว!", 1: "หิวจัด • โมโห ไม่มีแรงตอบ", 2: "หิว • เริ่มเหวี่ยง", 3: "ท้องเริ่มร้อง", 4: "อิ่ม • อารมณ์ดี"}
        self.cal_val_label.config(text=f"{self.calories}/100 kcal", fg=colors[level])
        remaining = max(0, math.ceil(self.food_buff_until - time.monotonic()))
        self.effect_label.config(text=self.current_food_effect + (f" • เหลือ {remaining} วิ" if remaining else ""))
        self.mood_label.config(text=f"{names[level]}  |  พลังงานลด 1 ทุก {self.hunger_interval:g} วินาที • ตอบใช้ 15", fg=colors[level])
        if level < self.last_hunger_level:
            warnings = {
                3: "อิ่มได้แป๊บเดียวเอง ท้องเริ่มร้องละ มีของหวานปะ",
                2: "เริ่มหิวแล้วนะ ถ้าตอบเหวี่ยงอย่าโทษกู โทษตู้เย็นว่าง",
                1: "หิวจนสมองเหลือแต่รูปหมูกรอบแล้ว ไม่ตอบละ ป้อนก่อน",
                0: "หมดหลอด! กูงอนแล้ว ปิดรับคำถาม เปิดรับข้าวเท่านั้น",
            }
            self.append_chat("FAT-GPT", warnings[level], kind="status")
            play_snd("fail" if level <= 1 else "msg")
        self.last_hunger_level = level

    def append_chat(self, sender, message, kind=None):
        self.chat_display.config(state="normal")
        if kind == "food":
            self.chat_display.insert(tk.END, f"\n[{sender} • อาหาร]: {message}\n", "food")
        elif kind == "status":
            self.chat_display.insert(tk.END, f"\n[{sender} • สถานะ]: {message}\n", "system")
        elif sender == "FAT-GPT":
            self.chat_display.insert(tk.END, f"\nFAT-GPT:\n{message}\n", "fat_gpt")
        elif sender == "คุณ":
            self.chat_display.insert(tk.END, f"\nคุณ:\n{message}\n", "user")
        else:
            self.chat_display.insert(tk.END, f"\n[{sender}]: {message}\n", "system")

        self.chat_display.tag_config("fat_gpt", foreground="#C0392B", font=(self.main_font, 10))
        self.chat_display.tag_config("user", foreground="#2980B9", font=(self.main_font, 10))
        self.chat_display.tag_config("food", foreground="#217A28", font=(self.main_font, 9))
        self.chat_display.tag_config("system", foreground="#7842A0", font=(self.main_font, 9))
        self.chat_display.see(tk.END)
        self.chat_display.config(state="disabled")

    def send_message(self):
        if self.ai_busy:
            return
        user_text = self.msg_entry.get().strip()
        if not user_text:
            return

        self.msg_entry.delete(0, tk.END)
        self.append_chat("คุณ", user_text)

        self.advance_hunger(time.monotonic())
        self.update_status_ui()
        if self.calories < 15:
            play_snd("fail")
            refusal = self.hungry_refusal()
            self.append_chat("FAT-GPT", refusal)
            self.speak_reply(refusal)
            return

        self.calories -= 15
        self.update_status_ui()

        self.ai_busy = True
        self.send_btn.config(state="disabled")
        self.chat_history = self.chat_history[-10:]
        self.chat_history.append({"role": "user", "content": user_text})
        settings = (self.api_base_url.get().rstrip('/'), self.model_name.get(), self.api_key.get(), f"{self.active_effect_prompt}\n{self.hunger_prompt()}", [dict(message) for message in self.chat_history])
        threading.Thread(target=self.query_ai_thread, args=(user_text, settings), daemon=True).start()

    def query_ai_thread(self, user_text, settings):
        base_url, model, key, effect, history = settings
        full_system_prompt = f"{self.system_prompt_base}\n[สถานะอาหารปัจจุบัน]: {effect}"


        endpoint = f"{base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"

        payload = {
            "model": model,
            "messages": [{"role": "system", "content": full_system_prompt}] + history,
            "temperature": 0.85
        }

        try:
            req = urllib.request.Request(endpoint, data=json.dumps(payload).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req, timeout=120) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                ai_reply = res_data['choices'][0]['message']['content']
                if not isinstance(ai_reply, str) or not ai_reply.strip():
                    raise ValueError('โมเดลตอบกลับเป็นข้อความว่าง')
                success = True
                play_snd("msg")
        except Exception as e:
            play_snd("fail")
            success = False
            ai_reply = f"หิวจนเออเร่อว่ะ เช็คดูดิเปิด Ollama ในเครื่องยัง หรือลืมใส่โมเดล ({str(e)})"

        self.reply_queue.put((ai_reply, success))

    def poll_ai_replies(self):
        try:
            speech_error = self.speech.errors.get_nowait()
        except queue.Empty:
            pass
        else:
            self.voice_status.set("เสียงขัดข้อง: " + speech_error)
        try:
            reply, success = self.reply_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self.finish_ai_reply(reply, success)
        self.root.after(100, self.poll_ai_replies)

    def finish_ai_reply(self, reply, success=True):
        self.ai_busy = False
        if self.calories == 0:
            reply = self.hungry_refusal()
        if success:
            self.chat_history.append({"role": "assistant", "content": reply})
            self.chat_history = self.chat_history[-12:]
        elif self.chat_history and self.chat_history[-1]["role"] == "user":
            self.chat_history.pop()
        self.append_chat("FAT-GPT", reply)
        if success:
            self.speak_reply(reply)
        self.send_btn.config(state="normal")

    def update_voice_button(self):
        enabled = self.voice_enabled.get()
        self.voice_toggle_btn.config(text="เสียง AI: เปิด" if enabled else "เสียง AI: ปิด")

    def toggle_voice(self):
        self.voice_enabled.set(not self.voice_enabled.get())
        self.update_voice_button()
        if not self.voice_enabled.get():
            self.speech.stop()
            self.voice_status.set("ปิดเสียง AI แล้ว • แชทและเสียงมินิเกมยังทำงาน")
        else:
            self.voice_status.set("เปิดเสียง AI แล้ว • เสียงผู้ชาย Niwat ออนไลน์")

    def speak_reply(self, text):
        if not self.voice_enabled.get():
            return
        rate, pitch = {"ผู้ชายทุ้มกวนๆ": (5, -28), "ผู้ชายทุ้มจัด": (5, -45), "ผู้ชายปกติ": (0, 0)}[self.voice_style.get()]
        if self.voice_style.get() != "ผู้ชายปกติ":
            if self.food_buff == "coffee":
                rate += 25
            elif self.food_buff == "chili":
                rate += 10
        self.voice_status.set("เสียงผู้ชาย Niwat • " + self.voice_style.get())
        self.speech.speak(text, rate=rate, pitch=pitch)

    def preview_voice(self):
        if not self.voice_enabled.get():
            self.voice_status.set("กด เสียง AI: เปิด ด้านบนก่อนลองเสียง")
            return
        self.speak_reply("เออ ว่าไง หิวข้าวแล้ว มีหมูกรอบปะ อย่าถามเยอะ เดี๋ยวแรงเคี้ยวหมด")

    def close_app(self):
        self.speech.close()
        self.root.destroy()

    def build_game_tab(self):
        self.mc_label(self.game_tab, text=" FAT-GPT ARCADE • ครัวแตก แคลอรีกระจาย", font=(self.main_font, 13, "bold"), fg="#003399").pack(pady=8)
        kitchen = self.kitchen_tab = ttk.Frame(self.game_tab)
        kitchen.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.mc_label(kitchen, text="คลิกอาหาร • แอปเปิลทอง x3 • นาฬิกาเพิ่มเวลา • เกราะกัน TNT • คอมโบ 6–7 = SIX SEVEN!", wraplength=760, font=(self.main_font, 10)).pack(pady=5)
        self.arcade_status = self.mc_label(kitchen, text="30 วิ • 5 หัวใจ • เป้าหมาย: 100 คะแนน • หมูกรอบพร้อมบิน!", font=(self.main_font, 13, "bold"), fg="#D35400")
        self.arcade_status.pack(pady=4)
        self.arena = tk.Canvas(kitchen, bg="#245EDB", height=290, highlightthickness=0)
        self.arena.pack(fill=tk.BOTH, expand=True, padx=12, pady=5)
        self.arena.bind("<Button-1>", self.hit_food)
        self.arcade_taunt = self.mc_label(kitchen, text="FAT-GPT: ร้านนี้รับพนักงาน ไม่รับคนยืนดูเมนู", font=(self.main_font, 12, "bold"), wraplength=740, fg="#003399")
        self.arcade_taunt.pack(pady=6)
        controls = tk.Frame(kitchen)
        controls.pack(pady=(0,8))
        self.arcade_start = self.xp_button(controls, text="เปิดครัวเทอร์โบ! 30 วิ", font=(self.main_font, 12, "bold"), command=self.start_arcade)
        self.arcade_start.pack(side=tk.LEFT,padx=5)
        self.arcade_pause = self.xp_button(controls,text="พัก • Space",command=self.toggle_arcade_pause,state="disabled")
        self.arcade_pause.pack(side=tk.LEFT,padx=5)
        self.arcade_running = False
        self.arcade_round = 0
        self.food_targets = {}
        self.arcade_score = self.arcade_combo = self.arcade_best = 0
        self.meme_enabled = tk.BooleanVar(value=True)
        self.xp_button(controls,text="67: เปิด",command=self.toggle_memes).pack(side=tk.LEFT,padx=5)
        self.meme_button = controls.winfo_children()[-1]
        self.brainrot_enabled = tk.BooleanVar(value=True)
        self.meme_folder = SOUND_DIR / "memes"
        self.meme_folder.mkdir(exist_ok=True)
        self.meme_files = []
        self.meme_current = None
        self.meme_bad_files = set()
        self.meme_render_cache = {}
        self.meme_source_cache = {}
        self.meme_elapsed = 0.0
        self.meme_popup_remaining = 0.0
        self.meme_popups = []
        self.meme_serial = 0
        self.meme_next_delay = random.uniform(1.0,1.7)
        self.reload_memes()
        self.brainrot_last_frame = time.monotonic()
        self.brainrot_buttons = []
        backdrop_button = self.xp_button(controls,text="มีมสุ่ม: เปิด",command=self.toggle_brainrot)
        backdrop_button.pack(side=tk.LEFT,padx=5)
        self.brainrot_buttons.append(backdrop_button)
        self.arcade_heat = self.arcade_record = 0
        self.arcade_paused = False
        self.fever_bar = self.arena.create_rectangle(16,12,16,23,fill="#FFD166",outline="")
        self.arena.create_text(0,0,text="ครัวพิกเซล BRAINROT!\nกินสเต๊ก ไม่กิน TNT\n6… 7… SIX SEVEN!",fill="white",justify="center",tags="welcome")
        self.avatar_eyes = []
        self.avatar_blinking = False
        self.avatar_next_blink = time.monotonic()+random.uniform(2.0,4.0)
        self.arena.bind("<Configure>",self.resize_arena)
        self.arena.bind("<space>",self.toggle_arcade_pause)

        self.root.after(80,self.animate_brainrot)
        self.root.after(65,self.animate_avatar)

    def burst(self, canvas, x, y, text, color="#FFD166"):
        label = canvas.create_text(x, y, text=text, fill=color, font=(self.main_font, 16, "bold"))
        particles = []
        for _ in range(10):
            dot = canvas.create_oval(x-3, y-3, x+3, y+3, fill=random.choice([color, "#FF6B9D", "#67D5FF"]), outline="")
            particles.append((dot, random.uniform(-7, 7), random.uniform(-7, 2)))
        def animate(frame=0):
            canvas.move(label, 0, -2)
            for dot, vx, vy in particles:
                canvas.move(dot, vx, vy + frame * 0.35)
            if frame < 18:
                self.root.after(30, lambda: animate(frame + 1))
            else:
                canvas.delete(label)
                for dot, _, _ in particles:
                    canvas.delete(dot)
        animate()

    def reload_memes(self):
        roots = [SOUND_DIR, self.meme_folder]
        self.meme_files = sorted({path for folder in roots for path in folder.iterdir()
                                  if path.is_file() and path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif")
                                  and path not in self.meme_bad_files})
        for path in self.meme_files[:]:
            try:
                modified = path.stat().st_mtime_ns
                cached = self.meme_source_cache.get(path)
                if cached is None or cached[0] != modified:
                    with Image.open(path) as source:
                        picture = ImageOps.exif_transpose(source).convert("RGBA")
                        picture.thumbnail((260,200),Image.Resampling.LANCZOS)
                    self.meme_source_cache[path] = (modified,picture)
            except (OSError,ValueError):
                self.meme_bad_files.add(path)
                self.meme_files.remove(path)
        self.meme_source_cache = {path:picture for path,picture in self.meme_source_cache.items() if path in self.meme_files}
        if self.meme_current not in self.meme_files:
            self.meme_current = None

    def show_meme(self):
        if not self.brainrot_enabled.get() or self.meme_elapsed < .45 or len(self.meme_popups) >= 6:
            return
        self.reload_memes()
        if not self.meme_files:
            return
        self.meme_elapsed = 0
        self.meme_next_delay = random.uniform(1.0,1.7)
        self.choose_meme()

    def choose_meme(self):
        choices = [path for path in self.meme_files if path != self.meme_current] or self.meme_files
        if not choices:
            return
        amount = min(random.randint(2,3), len(choices), 6-len(self.meme_popups))
        for path in random.sample(choices,amount):
            self.meme_serial += 1
            self.meme_popups.append({"id":self.meme_serial,"path":path,"age":0.0,
                "duration":random.uniform(1.8,2.5),"x":random.uniform(.15,.85),
                "y":random.uniform(.25,.7),"angle":random.uniform(-12,12),
                "drift":random.uniform(-.06,.06),"phase":random.uniform(0,6),"base":{}})
            self.meme_current = path
        self.meme_popup_remaining = max((p["duration"]-p["age"] for p in self.meme_popups),default=0)
        self.draw_brainrot(self.arena,kitchen=True)

    def toggle_brainrot(self):
        self.brainrot_enabled.set(not self.brainrot_enabled.get())
        for button in self.brainrot_buttons:
            button.config(text="มีมสุ่ม: เปิด" if self.brainrot_enabled.get() else "มีมสุ่ม: ปิด")
        if not self.brainrot_enabled.get():
            self.meme_popups.clear()
            self.meme_render_cache.clear()
        self.arena.delete("brainrot_bg")

    def animate_brainrot(self):
        now = time.monotonic()
        elapsed = min(.2,max(0,now-self.brainrot_last_frame))
        self.brainrot_last_frame = now
        visible = self.notebook.select() == str(self.game_tab)
        active = self.arcade_running and not self.arcade_paused
        if visible and active and self.brainrot_enabled.get():
            self.meme_elapsed += elapsed
            for popup in self.meme_popups:
                popup["age"] += elapsed
            self.meme_popups = [p for p in self.meme_popups if p["age"] < p["duration"]]
            self.meme_popup_remaining = max((p["duration"]-p["age"] for p in self.meme_popups),default=0)
            if self.meme_elapsed >= self.meme_next_delay:
                self.show_meme()
                if not self.meme_files:
                    self.meme_elapsed = 0
            self.draw_brainrot(self.arena,kitchen=True)
        self.root.after(50,self.animate_brainrot)

    def meme_opacity(self, popup):
        # Quick arrival, then a smooth 0.8-second fade back to the game.
        entrance = min(1,popup["age"]/.12)
        exit_alpha = min(1,max(0,(popup["duration"]-popup["age"])/.8))
        return .88*entrance*exit_alpha

    def draw_brainrot(self, canvas, kitchen=False):
        tag = "brainrot_bg"
        canvas_key = str(canvas)
        if not self.brainrot_enabled.get() or not self.meme_popups or (kitchen and not self.arcade_running):
            canvas.delete(tag)
            self.meme_render_cache.pop(canvas_key,None)
            return
        w,h = max(1,canvas.winfo_width()),max(1,canvas.winfo_height())
        field = max(1,int(h*(.76 if kitchen else 1))-28)
        alive_tags = {f"meme_popup_{p['id']}" for p in self.meme_popups}
        for item in canvas.find_withtag(tag):
            if not alive_tags.intersection(canvas.gettags(item)):
                canvas.delete(item)
        photos = []
        for popup in self.meme_popups:
            try:
                key = (w,field)
                cached = popup["base"].get(canvas_key)
                if cached is None or cached["size"] != key:
                    # Decode once before playing; use small sources for each tilted card.
                    source = self.meme_source_cache[popup["path"]][1]
                    picture = source.copy()
                    picture.thumbnail((max(32,min(240,int(w*.37))),max(32,min(180,int(field*.72)))),Image.Resampling.LANCZOS)
                    picture = picture.rotate(popup["angle"],resample=Image.Resampling.BICUBIC,expand=True)
                    cached = {"size":key,"picture":picture,"level":None,"photo":None}
                    popup["base"][canvas_key] = cached
                picture = cached["picture"]
                level = round(self.meme_opacity(popup)*20)
                changed = level != cached["level"]
                if changed:
                    frame = picture.copy()
                    frame.putalpha(picture.getchannel("A").point([round(i*level/20) for i in range(256)]))
                    cached["photo"] = ImageTk.PhotoImage(frame,master=self.root)
                    cached["level"] = level
                photo = cached["photo"]
                photos.append(photo)
                age = popup["age"]
                x = w*(popup["x"]+popup["drift"]*age)
                y = 28+field*popup["y"]-12*age+math.sin(age*8+popup["phase"])*5
                x = max(picture.width/2,min(w-picture.width/2,x))
                y = max(28+picture.height/2,min(28+field-picture.height/2,y))
                popup_tag = f"meme_popup_{popup['id']}"
                if canvas.find_withtag(popup_tag):
                    canvas.coords(popup_tag,x,y)
                    if changed:
                        canvas.itemconfig(popup_tag,image=photo)
                else:
                    canvas.create_image(x,y,image=photo,tags=(tag,popup_tag))
            except Exception:
                self.meme_bad_files.add(popup["path"])
                popup["age"] = popup["duration"]
        self.meme_render_cache[canvas_key] = photos
        if kitchen:
            canvas.tag_raise(tag,"scenery")
        else:
            canvas.tag_lower(tag)

    def food_image(self, name, pixels):
        zoom = max(1,min(10,round(pixels/16)))
        key = (name,zoom)
        if key not in self.pixel_food_cache:
            self.pixel_food_cache[key] = self.pixel_foods[name].zoom(zoom)
        return self.pixel_food_cache[key]

    def toggle_memes(self):
        self.meme_enabled.set(not self.meme_enabled.get())
        self.meme_button.config(text="67: เปิด" if self.meme_enabled.get() else "67: ปิด")
        if not self.meme_enabled.get():
            self.arena.delete("meme67")

    def six_seven(self):
        if not self.meme_enabled.get() or not self.arcade_running or self.arcade_paused:
            return
        self.arena.delete("meme67")
        round_id = self.arcade_round
        title = self.arena.create_text(0,0,text="67",fill="#FFEB4B",font=(self.main_font,60,"bold"),tags="meme67")
        caption = self.arena.create_text(0,0,text="SIX SEVEN!",fill="white",font=(self.main_font,20,"bold"),tags="meme67")
        # Put the joke above the food so the effect never blocks a click target.
        self.arcade_taunt.config(text=random.choice([
            "SIX SEVEN! กูไม่รู้ว่ามันแปลว่าอะไร แต่หิว 67 เท่า",
            "ออร่า +67 • สเต๊กเข้าปาก • สมองออกจากเซิร์ฟเวอร์",
            "67 67 67! สตีฟมีเพชร กูมีไขมัน เป็นทรัพยากรเหมือนกัน",
            "SIX SEVEN! ใครเปิดเสียงในหัวกู ปิดที จะเคี้ยว",
        ]))
        play_snd("sixseven")
        def animate(frame=0):
            if round_id!=self.arcade_round or not self.arcade_running or not self.arena.type(title) or not self.meme_enabled.get():
                self.arena.delete(title,caption)
                return
            if self.arcade_paused:
                self.root.after(50,lambda:animate(frame))
                return
            w,h = self.arena.winfo_width(),self.arena.winfo_height()
            size = max(25,min(72,int(h*.10)))
            bounce = math.sin(frame*.55)*6
            self.arena.coords(title,w/2,48+bounce)
            self.arena.coords(caption,w/2,48+size*.6+17+bounce)
            self.arena.itemconfig(title,font=(self.main_font,size+int(5*math.sin(frame*.4)),"bold"))
            self.arena.itemconfig(caption,font=(self.main_font,max(12,size//3),"bold"))
            if frame<24:
                self.root.after(35,lambda:animate(frame+1))
            else:
                self.arena.delete(title,caption)
        animate()

    def arena_scale(self):
        return max(1, self.arena.winfo_width()) / 1000, max(1, self.arena.winfo_height()) / 600

    def draw_pixel_avatar(self):
        sx, sy = self.arena_scale()
        pixel = max(2, round(8*min(sx,sy)))
        left = round(500*sx)-12*pixel
        top = round(526*sy)-9*pixel
        def block(x,y,width,height,color):
            return self.arena.create_rectangle(
                left+x*pixel,top+y*pixel,left+(x+width)*pixel,top+(y+height)*pixel,
                fill=color,outline="",tags=("scenery","pixel_avatar"))
        # Stepped outline, blocky hair, chunky cheeks and an XP-blue shirt.
        for x,y,width,height,color in (
            (4,0,16,1,"#342A28"),(2,1,20,2,"#342A28"),
            (1,3,22,11,"#342A28"),(2,14,20,2,"#342A28"),(4,16,16,2,"#342A28"),
            (2,4,20,10,"#E9A46F"),(3,3,18,10,"#FFD4A2"),(3,13,18,2,"#E9A46F"),
            (2,2,20,2,"#583C2B"),(4,1,16,1,"#704A31"),
            (3,4,3,2,"#583C2B"),(17,4,4,1,"#583C2B"),
            (6,2,4,1,"#926442"),(13,2,3,1,"#926442"),
            (5,5,4,1,"#744A31"),(15,5,4,1,"#744A31"),
            (3,9,3,2,"#EF917D"),(18,9,3,2,"#EF917D"),
            (11,8,2,2,"#E9A46F"),(10,10,4,1,"#D08A59"),
            (8,11,8,5,"#AA4C50"),
            (4,16,16,2,"#245EDB"),(5,16,3,1,"#579BFF"),(16,16,3,1,"#174B9B"),
        ):
            block(x,y,width,height,color)
        self.mouth = block(9,12,6,3,"#702537")
        block(9,11,6,1,"#FFF4DF")
        block(10,14,4,1,"#DE466B")
        self.avatar_eyes = []
        for x in (7,16):
            eye = block(x,6,2,2,"#30251F")
            shine = block(x,6,1,1,"#FFF4DF")
            self.avatar_eyes.append((eye,shine,tuple(self.arena.coords(eye))))
        self.set_avatar_blink(self.avatar_blinking)

    def set_avatar_blink(self, closed):
        self.avatar_blinking = closed
        for eye,shine,(x1,y1,x2,y2) in self.avatar_eyes:
            self.arena.coords(eye,x1,(y1+y2)/2 if closed else y1,x2,y2)
            self.arena.itemconfig(shine,state="hidden" if closed else "normal")

    def animate_avatar(self):
        now = time.monotonic()
        visible = self.notebook.select() == str(self.game_tab)
        if visible and now >= self.avatar_next_blink:
            if self.avatar_blinking:
                self.set_avatar_blink(False)
                self.avatar_next_blink = now+random.uniform(2.0,4.0)
            else:
                self.set_avatar_blink(True)
                self.avatar_next_blink = now+.13
        # Only two small eye shapes change; no image generation per frame.
        self.root.after(65,self.animate_avatar)

    def resize_arena(self, event=None):
        sx, sy = self.arena_scale()
        w, h = self.arena.winfo_width(), self.arena.winfo_height()
        self.arena.delete("scenery")
        self.arena.create_rectangle(0, 0, w, h, fill="#174B9B", outline="", tags="scenery")
        for x in range(0, 1001, 100):
            self.arena.create_line(x*sx, 0, x*sx, h, fill="#2159AA", tags="scenery")
        for y in range(0, 601, 75):
            self.arena.create_line(0, y*sy, w, y*sy, fill="#2159AA", tags="scenery")
        self.arena.create_rectangle(0, 465*sy, w, h, fill="#C9A474", outline="#F5DCAC", width=3, tags="scenery")
        self.draw_pixel_avatar()
        self.arena.create_text(190*sx, 530*sy, text="FAT-GPT\nหลุมดำประจำครัว", fill="#342C24", font=(self.main_font, max(11, int(16*min(sx,sy))), "bold"), tags="scenery")
        self.arena.create_text(810*sx, 530*sy, text="คลิกป้อน • เว้นวรรคพัก\nอย่าป้อน TNT!", fill="#342C24", font=(self.main_font, max(10, int(14*min(sx,sy)))), tags="scenery")
        self.arena.tag_lower("scenery")
        self.draw_brainrot(self.arena,kitchen=True)
        for tag, target in self.food_targets.items():
            self.draw_target(tag, target)
        for tag in ["welcome", "result", "paused"]:
            for item in self.arena.find_withtag(tag):
                self.arena.coords(item, w/2, h*0.35)
                self.arena.itemconfig(item, width=max(200,w-100), font=(self.main_font, max(16,int(24*min(sx,sy))),"bold"))
        self.arena.coords(self.fever_bar, 16, 12, 16 + max(0,w-32)*self.arcade_heat/10, 23)
        self.arena.tag_raise(self.fever_bar)

    def draw_target(self, tag, target):
        sx, sy = self.arena_scale()
        x, y = target["x"]*sx, target["y"]*sy
        r = max(24, 38*min(sx,sy))
        self.arena.coords(target["circle"],x-r,y-r,x+r,y+r)
        self.arena.coords(target["icon_item"],x,y)
        if target.get("sprite"):
            self.arena.itemconfig(target["icon_item"],image=self.food_image(target["sprite"],r*1.65))
        else:
            self.arena.itemconfig(target["icon_item"],font=(self.main_font,max(22,int(r*.85))))
        lifetime = max(0,(target["expires"]-time.monotonic())/target["lifetime"])
        self.arena.coords(target["ring"],x-r-4,y-r-4,x+r+4,y+r+4)
        self.arena.itemconfig(target["ring"],extent=360*min(1,lifetime))

    def spawn_food(self, kind=None):
        now = time.monotonic()
        fever = now < self.fever_until
        kind = kind or random.choices(["food","gold","bomb","clock","shield"], [55,25,0,12,8] if fever else [57,15,18,5,5])[0]
        icon = kind
        self.target_serial += 1
        tag = f"food_{self.arcade_round}_{self.target_serial}"
        speed = 65 + min(150,self.arcade_score*1.1)
        lifetime = max(2.0,4.0-self.arcade_score*.01)
        target = {"kind":kind,"icon":icon,"x":random.uniform(65,935),"y":random.uniform(85,400),
                  "vx":random.choice([-1,1])*speed,"vy":random.uniform(-45,45),"expires":now+lifetime,"lifetime":lifetime}
        target["circle"] = self.arena.create_oval(0,0,1,1,fill={"food":"#ECF3FF","gold":"#FFDF65","bomb":"#E86B7E","clock":"#82E6ED","shield":"#A0E590"}[kind],outline="white",width=2,tags=tag)
        target["ring"] = self.arena.create_arc(0,0,1,1,start=90,extent=359,style=tk.ARC,outline="#FFD166",width=3,tags=tag)
        target["sprite"] = "tnt" if kind=="bomb" else "golden_apple" if kind=="gold" else random.choice(["steak","porkchop","bread","carrot","cookie"]) if kind=="food" else "clock" if kind=="clock" else "armor"
        if target["sprite"]:
            target["icon_item"] = self.arena.create_image(0,0,image=self.food_image(target["sprite"],50),tags=tag)
        else:
            target["icon_item"] = self.arena.create_text(0,0,text=icon,tags=tag)
        self.food_targets[tag] = target
        self.draw_target(tag,target)
        return tag

    def start_arcade(self):
        if self.arcade_running:
            return
        self.arcade_round += 1
        self.arcade_running = True
        self.arcade_paused = False
        self.arcade_score = self.arcade_combo = self.arcade_best = self.arcade_heat = 0
        self.arcade_lives = 5
        self.arcade_shields = 0
        self.fever_until = 0
        self.meme_next = time.monotonic()+6.7
        self.arcade_bonus_time = 0
        self.target_serial = 0
        self.food_targets.clear()
        self.arena.delete("all")
        self.fever_bar = self.arena.create_rectangle(16,12,16,23,fill="#FFD166",outline="")
        self.arcade_deadline = time.monotonic() + 30
        self.arcade_last_frame = time.monotonic()
        self.arcade_next_spawn = 0
        self.meme_elapsed = 0.0
        self.meme_popup_remaining = 0.0
        self.meme_popups.clear()
        self.meme_render_cache.clear()
        self.meme_next_delay = random.uniform(1.0,1.7)
        self.reload_memes()
        self.arcade_start.config(state="disabled",text="ครัวกำลังแตก!")
        self.arcade_pause.config(state="normal",text="พัก • Space")
        self.arcade_taunt.config(text="FAT-GPT: ยิงเข้าปากเลย! กดอาหารติดกัน 10 ชิ้นเปิดโหมดหมูกรอบคลั่ง")
        self.resize_arena()
        for _ in range(3):
            self.spawn_food("food")
        self.arena.focus_set()
        self.arcade_tick(self.arcade_round)

    def toggle_arcade_pause(self, event=None):
        if not self.arcade_running:
            return "break"
        self.arcade_paused = not self.arcade_paused
        self.arena.delete("paused")
        self.arcade_pause.config(text="เล่นต่อ • Space" if self.arcade_paused else "พัก • Space")
        if self.arcade_paused:
            self.arena.create_text(0,0,text="พักครัวชั่วคราว\nกด Space หรือ เล่นต่อ",fill="white",justify="center",tags="paused")
            self.resize_arena()
        self.arena.focus_set()
        return "break"

    def arcade_tick(self, round_id):
        if not self.arcade_running or round_id != self.arcade_round:
            return
        now = time.monotonic()
        elapsed = max(0,now-self.arcade_last_frame)
        self.arcade_last_frame = now
        if not self.arcade_paused and self.notebook.select()!=str(self.game_tab):
            self.toggle_arcade_pause()
        if self.arcade_paused:
            self.arcade_deadline += elapsed
            self.arcade_next_spawn += elapsed
            self.meme_next += elapsed
            if self.fever_until:
                self.fever_until += elapsed
            for target in self.food_targets.values():
                target["expires"] += elapsed
            self.root.after(33,lambda:self.arcade_tick(round_id))
            return
        remaining = max(0,self.arcade_deadline-now)
        if remaining <= 0 or self.arcade_lives <= 0:
            self.finish_arcade()
            return
        for tag,target in list(self.food_targets.items()):
            if now >= target["expires"]:
                self.arena.delete(tag)
                del self.food_targets[tag]
                if target["kind"] in ("food","gold"):
                    self.arcade_combo = self.arcade_heat = 0
                    self.arcade_lives -= 1
                    self.burst(self.arena,target["x"]*self.arena_scale()[0],target["y"]*self.arena_scale()[1],"หนีไปแล้ว! -1 ใจ","#FFB3C1")
                    self.arcade_taunt.config(text="FAT-GPT: หมูวิ่งหนีแล้ว! กูหิวจนจะกินจานแทน")
            else:
                dt = min(.08,elapsed)
                target["x"] += target["vx"]*dt
                target["y"] += target["vy"]*dt
                if target["x"] < 55 or target["x"] > 945:
                    target["vx"] *= -1
                    target["x"] = max(55,min(945,target["x"]))
                if target["y"] < 65 or target["y"] > 410:
                    target["vy"] *= -1
                    target["y"] = max(65,min(410,target["y"]))
                self.draw_target(tag,target)
        if self.arcade_lives <= 0:
            self.finish_arcade()
            return
        if now >= self.meme_next:
            self.meme_next = now+6.7
            if self.meme_enabled.get():
                self.six_seven()
                if len(self.food_targets)<8:
                    self.spawn_food("gold")
        fever = now < self.fever_until
        if now >= self.arcade_next_spawn and len(self.food_targets) < (8 if fever else 6):
            self.spawn_food()
            self.arcade_next_spawn = now + (.25 if fever else max(.38,.8-self.arcade_score*.003))
        self.arcade_status.config(text=f"เวลา {remaining:04.1f}s  |  หัวใจ {self.arcade_lives}  |  คะแนน {self.arcade_score}  |  x{1+min(4,self.arcade_combo//5)}  |  โล่ {self.arcade_shields}" + ("  |  FEVER x2!" if fever else ""))
        self.arena.itemconfig(self.fever_bar,fill="#FF7A35" if fever else "#FFD166")
        sx, sy = self.arena_scale()
        self.arena.coords(self.fever_bar,16,12,16+max(0,self.arena.winfo_width()-32)*(1 if fever else self.arcade_heat/10),23)
        self.root.after(33,lambda:self.arcade_tick(round_id))

    def fly_to_mouth(self, target):
        round_id = self.arcade_round
        item = self.arena.create_image(0,0,image=self.food_image(target["sprite"],48))
        def animate(frame=0):
            if round_id != self.arcade_round or not self.arcade_running:
                self.arena.delete(item)
                return
            progress = frame/12
            sx, sy = self.arena_scale()
            x = target["x"]+(500-target["x"])*progress
            y = target["y"]+(545-target["y"])*progress-100*math.sin(math.pi*progress)
            self.arena.coords(item,x*sx,y*sy)
            self.arena.itemconfig(item,image=self.food_image(target["sprite"],48*(1-progress*.6)*max(.8,min(sx,sy))))
            if frame < 12:
                self.root.after(20,lambda:animate(frame+1))
            else:
                self.arena.delete(item)
                self.arena.itemconfig(self.mouth,fill="#DE466B")
                self.root.after(100,lambda:self.arena.itemconfig(self.mouth,fill="#702537") if round_id==self.arcade_round and self.arcade_running else None)
        animate()

    def hit_food(self, event):
        self.arena.focus_set()
        if not self.arcade_running or self.arcade_paused:
            return
        if time.monotonic() >= self.arcade_deadline:
            self.finish_arcade()
            return
        tag = None
        for item in reversed(self.arena.find_overlapping(event.x-2,event.y-2,event.x+2,event.y+2)):
            tag = next((t for t in self.arena.gettags(item) if t in self.food_targets),None)
            if tag:
                break
        if not tag:
            self.arcade_combo = self.arcade_heat = 0
            self.burst(self.arena,event.x,event.y,"วืด!","#BDE8FF")
            return
        target = self.food_targets.pop(tag)
        self.arena.delete(tag)
        if time.monotonic() >= target["expires"]:
            if target["kind"] in ("food","gold"):
                self.arcade_lives -= 1
            self.arcade_combo = self.arcade_heat = 0
            return
        kind = target["kind"]
        if kind == "bomb":
            if self.arcade_shields:
                self.arcade_shields -= 1
                self.burst(self.arena,event.x,event.y,"โล่กัน TNT ไว้!","#A0E590")
            else:
                self.arcade_lives -= 1
                self.arcade_score = max(0,self.arcade_score-5)
                self.arcade_combo = self.arcade_heat = 0
                self.burst(self.arena,event.x,event.y,"บึ้ม! -5","#FF98A6")
                self.arcade_taunt.config(text=random.choice(["FAT-GPT: ขอหมูกรอบ ไม่ใช่ระเบิดกรอบ!", "FAT-GPT: เมนูวันนี้ หน้ากูผัดดินปืน", "FAT-GPT: ร้านนี้มีดาว ดาวที่เห็นหลังโดนระเบิด"]))
            play_snd("minecraft_tnt")
            self.show_meme()
        elif kind == "clock":
            bonus = min(3,9-self.arcade_bonus_time)
            self.arcade_bonus_time += bonus
            self.arcade_deadline += bonus
            self.burst(self.arena,event.x,event.y,f"เวลา +{bonus} วิ" if bonus else "เวลาบวกเต็มแล้ว!","#82E6ED")
            play_snd("win")
        elif kind == "shield":
            self.arcade_shields = min(3,self.arcade_shields+1)
            self.burst(self.arena,event.x,event.y,"โล่กัน TNT!","#A0E590")
            play_snd("minecraft_armor")
        else:
            self.arcade_combo += 1
            self.arcade_best = max(self.arcade_best,self.arcade_combo)
            if self.arcade_combo in (6,7) or self.arcade_combo % 67 == 0:
                self.six_seven()
                self.show_meme()
            fever = time.monotonic() < self.fever_until
            points = (3 if kind=="gold" else 1)*(1+min(4,self.arcade_combo//5))*(2 if fever else 1)
            self.arcade_score += points
            self.fly_to_mouth(target)
            self.burst(self.arena,event.x,event.y,f"งั่ม! +{points}")
            play_snd("minecraft_eat")
            if not fever:
                self.arcade_heat += 1
                if self.arcade_heat >= 10:
                    self.arcade_heat = 0
                    self.fever_until = time.monotonic()+6
                    # Turn existing bombs into gold so fever is a genuine reward.
                    for other in self.food_targets.values():
                        if other["kind"]=="bomb":
                            other["kind"],other["icon"] = "gold",""
                            self.arena.itemconfig(other["circle"],fill="#FFDF65")
                            other["sprite"] = "golden_apple"
                            tag = self.arena.gettags(other["icon_item"])[0]
                            self.arena.delete(other["icon_item"])
                            other["icon_item"] = self.arena.create_image(0,0,image=self.food_image("golden_apple",50),tags=tag)
                            self.draw_target(tag,other)
                    self.arcade_taunt.config(text="หมูกรอบคลั่ง 6 วิ! คะแนน x2 • ระเบิดกลายเป็นทอง • กินให้ยับ!")
                    self.burst(self.arena,self.arena.winfo_width()/2,70,"FEVER! หมูกรอบคลั่ง","#FFDD55")
                    play_snd("win")
            if self.arcade_combo%5==0 and not fever and not time.monotonic()<self.fever_until:
                self.arcade_taunt.config(text=random.choice(["FAT-GPT: ออร่า +67 แต่ตังค์ซื้อข้าว -100", "FAT-GPT: สตีฟขุดเพชร กูขุดตู้เย็น", "FAT-GPT: สมองโหลด chunk ไม่ทัน แต่ปาก 120 FPS", "FAT-GPT: คอมโบขึ้น แต่เกรดกูลง", "FAT-GPT: ยืนเฉยๆ ก็หิว นี่กูใช้ RTX เคี้ยวข้าวเหรอ"]))
        if self.arcade_lives <= 0:
            self.finish_arcade()

    def finish_arcade(self):
        if not self.arcade_running:
            return
        self.arcade_running = False
        self.arcade_paused = False
        self.arena.delete("all")
        self.food_targets.clear()
        self.arcade_record = max(self.arcade_record,self.arcade_score)
        reward = min(75,self.arcade_score)
        self.calories = min(100,self.calories+reward)
        self.update_status_ui()
        title = "จักรพรรดิหมูกรอบ!" if self.arcade_score>=100 else "เชฟกระทะเทอร์โบ!" if self.arcade_score>=40 else "เด็กฝึกงานครัวระเบิด"
        self.arena.create_text(0,0,text=f"{title}\nคะแนน {self.arcade_score} • คอมโบสูงสุด {self.arcade_best}\nสถิติรอบนี้ {self.arcade_record} • รับ +{reward} kcal",fill="#FFFFFF",justify="center",tags="result")
        self.fever_bar = self.arena.create_rectangle(16,12,16,23,fill="#FFD166",outline="")
        self.arcade_heat = 0
        self.resize_arena()
        self.arcade_status.config(text="ครัวแตก!" if self.arcade_lives<=0 else "หมดเวลา! อิ่มจนเก้าอี้ร้องขอชีวิต")
        self.arcade_taunt.config(text="แก้มือเลย! ทำคอมโบ 10 ชิ้นเปิด FEVER • เวลาบวกได้สูงสุด 9 วิ")
        self.arcade_start.config(state="normal",text="แก้มือ • เปิดครัวใหม่!")
        self.arcade_pause.config(state="disabled",text="พัก • Space")
        play_snd("win" if reward else "fail")
        self.append_chat("ระบบ",f"ครัวเทอร์โบ! คะแนน {self.arcade_score} คอมโบ {self.arcade_best} (+{reward} kcal)")

    def build_settings_tab(self):
        self.mc_label(self.settings_tab, text=" ตั้งค่าการเชื่อมต่อ AI Model", font=(self.main_font, 14, "bold")).pack(pady=10)

        mode_frame = tk.LabelFrame(self.settings_tab, text="โหมดการทำงาน", font=(self.main_font, 10, "bold"))
        mode_frame.pack(fill=tk.X, padx=15, pady=5)

        rb_local = tk.Radiobutton(mode_frame, text="Local Model (ผ่าน Ollama ในเครื่อง)", variable=self.ai_mode, value="local", command=self.on_mode_change)
        rb_local.pack(anchor="w", padx=10, pady=5)

        rb_api = tk.Radiobutton(mode_frame, text="Cloud API (OpenAI / DeepSeek / Custom API)", variable=self.ai_mode, value="api", command=self.on_mode_change)
        rb_api.pack(anchor="w", padx=10, pady=5)

        cfg_frame = tk.LabelFrame(self.settings_tab, text="พารามิเตอร์การเชื่อมต่อ (OpenAI Compatible API)", font=(self.main_font, 10, "bold"))
        cfg_frame.pack(fill=tk.X, padx=15, pady=10)

        self.mc_label(cfg_frame, text="API Base URL:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        entry_url = tk.Entry(cfg_frame, textvariable=self.api_base_url, width=45)
        entry_url.grid(row=0, column=1, padx=5, pady=5)

        self.mc_label(cfg_frame, text="Model Name:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        entry_model = tk.Entry(cfg_frame, textvariable=self.model_name, width=45)
        entry_model.grid(row=1, column=1, padx=5, pady=5)

        self.mc_label(cfg_frame, text="API Key (ถ้ามี):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        entry_key = tk.Entry(cfg_frame, textvariable=self.api_key, show="*", width=45)
        entry_key.grid(row=2, column=1, padx=5, pady=5)

        preset_frame = tk.Frame(self.settings_tab)
        preset_frame.pack(pady=10)

        self.xp_button(preset_frame, text="เซ็ตเป็น Ollama (qwen2.5:14b)", command=self.set_preset_ollama_14b).pack(side=tk.LEFT, padx=5)
        self.xp_button(preset_frame, text="เซ็ตเป็น OpenAI GPT-4o-mini", command=self.set_preset_openai).pack(side=tk.LEFT, padx=5)

        voice_frame = tk.LabelFrame(self.settings_tab, text="เสียงพูด FAT-GPT", fg="#003399")
        voice_frame.pack(fill=tk.X, padx=15, pady=8)
        self.mc_label(voice_frame, text="บุคลิกเสียง:").grid(row=0, column=0, padx=8, pady=8)
        ttk.Combobox(voice_frame, textvariable=self.voice_style, values=["ผู้ชายทุ้มกวนๆ", "ผู้ชายทุ้มจัด", "ผู้ชายปกติ"], state="readonly", width=16).grid(row=0, column=1, padx=5)
        self.xp_button(voice_frame, text="ลองฟัง", command=self.preview_voice).grid(row=0, column=2, padx=8)
        self.mc_label(voice_frame, textvariable=self.voice_status, wraplength=700, anchor="w", font=(self.main_font, 9)).grid(row=1, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 8))
        self.mc_label(voice_frame, text="เสียงออนไลน์ • ส่งเฉพาะข้อความคำตอบไปสร้างเสียงที่ Microsoft • ไม่ลดความเร็วเสียง", font=(self.main_font, 9), fg="#003399").grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 8))

    def on_mode_change(self):
        if self.ai_mode.get() == "local":
            self.set_preset_ollama_14b()
        else:
            self.set_preset_openai()

    def set_preset_ollama_14b(self):
        self.ai_mode.set("local")
        self.api_base_url.set("http://localhost:11434/v1")
        self.model_name.set("qwen2.5:14b")
        self.api_key.set("")

    def set_preset_openai(self):
        self.ai_mode.set("api")
        self.api_base_url.set("https://api.openai.com/v1")
        self.model_name.set("gpt-4o-mini")

if __name__ == "__main__":
    root = tk.Tk()
    app = FatGPTApp(root)
    root.mainloop()
