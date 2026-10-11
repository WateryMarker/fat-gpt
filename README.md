# FAT-GPT

แอปแชทภาษาไทยธีม Windows XP พร้อมตัวละครกวนๆ ที่ต้องป้อนอาหารให้มีพลังงานก่อนคุย
พลังงานลดตามเวลา อาหารมีบัฟ และมินิเกมช่วยเพิ่มแคลอรี

## ฟีเจอร์

- แชทกับ Ollama ในเครื่อง หรือ API ที่รองรับรูปแบบ OpenAI
- ธีม Windows XP และฟอนต์ Tahoma
- มินิเกมครัวเทอร์โบ: อาหาร Minecraft, TNT, เกราะ, คอมโบ และโหมด Fever
- ตัวละครพิกเซลกระพริบตา พร้อมเอฟเฟกต์ตอนกิน
- รูปมีมสุ่มเด้งหลายรูปและ fade ออก ใช้แคชภาพเพื่อลดงานวาด
- เสียงพูดผู้ชายภาษาไทยบน macOS พร้อมปุ่มเปิด/ปิด

## ติดตั้งและรันบน macOS

ต้องมี Python ที่ใช้งาน Tkinter ได้ ทดสอบด้วย `python3 -m tkinter`

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python fat_gpt_mac_app.py
```

## ติดตั้งและรันบน Windows

1. ติดตั้ง Python 3.14 จาก [python.org](https://www.python.org/downloads/windows/)
   ถ้าใช้ Python Install Manager ให้เปิด PowerShell แล้วสั่ง `py install 3.14`
2. ดาวน์โหลดโปรเจกต์จาก GitHub ด้วย **Code → Download ZIP** แล้วแตก ZIP
3. เปิดโฟลเดอร์ที่มี `fat_gpt_app.py` ใน File Explorer คลิกแถบที่อยู่ พิมพ์ `powershell` แล้วกด Enter
4. รันคำสั่งต่อไปนี้ใน PowerShell:

```powershell
py -3.14 -m tkinter
```

ถ้ามีหน้าต่างทดสอบ Tkinter เปิดขึ้น ให้ปิดหน้าต่างนั้น แล้วติดตั้งและเปิดแอป:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe fat_gpt_app.py
```

ครั้งต่อไปเปิด PowerShell ในโฟลเดอร์โปรเจกต์ แล้วรันแค่:

```powershell
.\.venv\Scripts\python.exe fat_gpt_app.py
```

ไม่ต้อง activate virtual environment หรือเปลี่ยน Execution Policy ของ PowerShell
ถ้า `py` ไม่พบ ให้ตรวจว่าติดตั้ง Python แล้วและเปิด PowerShell ใหม่
ถ้า `tkinter` ไม่พบ ให้ติดตั้ง Python ที่มี Tcl/Tk จาก python.org
ถ้าเจอ `No module named PIL` ให้รันคำสั่งติดตั้ง `requirements.txt` ด้านบนอีกครั้ง

เสียงพูด AI ปัจจุบันยังรองรับเฉพาะ macOS บน Windows ให้กด **เสียง AI: ปิด**
แชทและมินิเกมใช้ entry point `fat_gpt_app.py`; เสียงเอฟเฟกต์ WAV มีโค้ดเล่นผ่าน `winsound`
คู่มือนี้ตรวจจากโค้ดและเอกสาร Python ยังไม่ได้ทดสอบบนเครื่อง Windows จริง

อ้างอิง: [Python on Windows](https://docs.python.org/3/using/windows.html) และ
[virtual environments](https://docs.python.org/3/library/venv.html)

## ตั้งค่า AI (ทั้ง macOS และ Windows)

เปิดแท็บตั้งค่า AI เพื่อเลือก Base URL, Model และ API Key
ค่าเริ่มต้นคือ Ollama ที่ `http://localhost:11434/v1` โมเดล `qwen2.5:14b`
ต้องเปิด Ollama และมีโมเดลนี้ในเครื่อง หรือเปลี่ยนเป็นชื่อโมเดลที่คุณติดตั้งไว้
API Key กรอกในแอปและไม่ได้บันทึกลงไฟล์

## เพิ่มมีม

วางไฟล์ PNG, JPG, JPEG, WEBP หรือ GIF ในโฟลเดอร์ `memes/`
หรือโฟลเดอร์เดียวกับ `fat_gpt_app.py` ได้เลย GIF แสดงเฟรมแรก
มีมถูกอ่านจากเครื่อง ไม่มีการส่งรูปไปบริการภายนอก

## เสียงและไฟล์ภาพ

ดู [VOICE_SETUP.md](VOICE_SETUP.md) สำหรับเสียงพูด
การสร้างเสียงต้องใช้อินเทอร์เน็ต และส่งข้อความคำตอบไปยังบริการเสียง Microsoft
เสียงพูด AI ปัจจุบันรองรับเฉพาะ macOS ส่วนเสียงเอฟเฟกต์ WAV มีตัวเล่นสำหรับ macOS และ Windows
ไฟล์เสียงเอฟเฟกต์ `snd_*.wav` ถูกสร้างเมื่อเปิดแอป ไม่ต้องเก็บใน Git

ภาพและเสียง Minecraft เป็นของ Mojang / Microsoft โปรเจกต์นี้เป็นแฟนโปรเจกต์ที่ไม่เป็นทางการ
แหล่งที่มาของ assets อยู่ใน `assets/minecraft/README.md` และไฟล์ `sources.json`
รูปมีมใน `memes/` เป็นไฟล์ที่ผู้ใช้เพิ่มเอง
