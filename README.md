# FAT-GPT

แอปแชทภาษาไทยธีม Windows XP พร้อมไอ้กวนๆ ที่ต้องป้อนอาหารให้มีพลังงานก่อนคุย
พลังงานลดตามเวลา อาหารมีบัฟ และมินิเกมช่วยเพิ่มความอ้วน

มีมินิเกมป้อนอาหาร Minecraft พร้อม TNT คอมโบ และมีมสุ่ม ใส่รูปของตัวเองเพิ่มได้

## รันบน macOS

เปิด Terminal ในโฟลเดอร์โปรเจกต์ แล้วรัน:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python fat_gpt_mac_app.py
```

## รันบน Windows

ติดตั้ง Python 3.14 แล้วแตก ZIP ของโปรเจกต์ เปิด PowerShell ในโฟลเดอร์นั้น:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe fat_gpt_app.py
```

ครั้งต่อไปใช้แค่คำสั่งบรรทัดสุดท้าย ไม่ต้อง activate `.venv`
ถ้าขึ้น `No module named PIL` ให้รันบรรทัดติดตั้งแพ็กเกจอีกครั้ง
Python ต้องมี Tkinter ด้วย ทดสอบได้ด้วย `python3 -m tkinter` บน Mac หรือ `py -3.14 -m tkinter` บน Windows
ยังไม่ได้ทดสอบบนเครื่อง Windows จริง

## ตั้งค่าแชทและเสียง

ค่าเริ่มต้นใช้ Ollama ที่ `http://localhost:11434/v1` กับโมเดล `qwen2.5:14b`
ต้องเปิด Ollama และติดตั้งโมเดลก่อน หรือเปลี่ยนชื่อโมเดลในแท็บตั้งค่า
ใช้ API อื่นได้โดยกรอก Base URL, Model และ API Key ในแอป คีย์ไม่ได้บันทึกลงไฟล์

เสียงพูดใช้ [edge-tts](https://github.com/rany2/edge-tts) เสียงผู้ชายไทย Niwat และรองรับเฉพาะ macOS
เปิดปิดเสียงได้จากปุ่มด้านบน การสร้างเสียงต้องใช้อินเทอร์เน็ตและส่งข้อความคำตอบไปยังบริการ Microsoft

## เพิ่มมีม

วางรูปใน `memes/` หรือโฟลเดอร์เดียวกับแอป รองรับ PNG, JPG, JPEG, WEBP และ GIF เฟรมแรก

ภาพและเสียง Minecraft เป็นของ Mojang / Microsoft โปรเจกต์นี้เป็นแฟนโปรเจกต์ที่ไม่เป็นทางการ
ดูแหล่งที่มาใน [assets/minecraft](assets/minecraft/README.md) และไฟล์ `sources.json`
