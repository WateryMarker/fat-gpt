# เสียงผู้ชาย FAT-GPT

เสียงภาษาไทยผู้ชาย: Microsoft th-TH-NiwatNeural ผ่าน edge-tts
โทนทุ้มปรับด้วย pitch โดยไม่ชะลอเสียง; เปิดเล่นด้วย afplay ที่ความเร็วปกติ
ต้องต่ออินเทอร์เน็ต ข้อความที่จะอ่านถูกส่งไปบริการเสียง Microsoft

ติดตั้งในโปรเจกต์ (macOS):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python fat_gpt_mac_app.py
```

ไม่ต้องเปลี่ยน Python ที่ใช้เปิดแอป ตัวแอปเรียกเครื่องมือเสียงจาก .venv เอง
เลือกเสียง/ลองฟังได้ในหน้าตั้งค่า เปิดปิด/หยุดเสียงได้ด้านบน
หากบริการไม่พร้อม แชทยังทำงานและแสดงข้อผิดพลาดในหน้าตั้งค่าเสียง

แหล่งข้อมูล: https://github.com/rany2/edge-tts
