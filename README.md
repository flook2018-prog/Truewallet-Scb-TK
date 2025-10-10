# Truewallet SCB TK - Financial Dashboard

เว็บแดชบอร์ดสำหรับจัดการข้อมูลการเงิน พร้อมระบบโน้ต เครื่องคิดเลข และการเชื่อมต่อ SMS

## ✨ คุณสมบัติหลัก

### 📋 ระบบโน้ต (Notes System)
- ✅ เพิ่ม/แก้ไข/ลบโน้ต
- ✅ เก็บข้อมูล: วันที่เวลา, ยอดเงิน, ผู้เขียน, รายละเอียด
- ✅ ส่งออก CSV สำหรับ Google Sheets
- ✅ นำเข้า CSV จาก Google Sheets
- ✅ แบ่งหน้า (Pagination) 10 รายการ/หน้า
- ✅ อัปเดต Real-time ไม่ต้องรีเฟรช

### 📊 ระบบการเงิน
- ✅ แดชบอร์ด SCB SMS แบบเรียลไทม์
- ✅ ติดตาม OTP การตัดบัตร
- ✅ ระบบ Kbiz Notifications
- ✅ เชื่อมต่อ API ภายนอก

### 🧮 เครื่องคิดเลข
- ✅ ดีไซน์ Windows 11 style
- ✅ ป๊อบอัพแบบ overlay
- ✅ รองรับคีย์บอร์ด shortcuts
- ✅ การคำนวณครบครัน

### 🗄️ ฐานข้อมูล
- ✅ PostgreSQL สำหรับ production (Railway)
- ✅ SQLite สำหรับ local development
- ✅ Auto-migration และ table creation

## 🚀 การติดตั้งและใช้งาน

### สำหรับการพัฒนา (Development)
```bash
# Clone repository
git clone https://github.com/flook2018-prog/Truewallet-Scb-TK.git
cd Truewallet-Scb-TK

# ติดตั้ง dependencies
pip install -r requirements.txt

# รันเซิร์ฟเวอร์
python app.py
```

### สำหรับการใช้งานจริง (Production)
```bash
# ติดตั้ง dependencies
pip install -r requirements.txt

# ตั้งค่า environment variables
export RAILWAY_ENVIRONMENT=production
export PORT=8080

# รันเซิร์ฟเวอร์
python app.py
```

## 📁 โครงสร้างโปรเจค
```
├── app.py                    # Flask server หลัก
├── models.py                 # Database models
├── requirements.txt          # Python dependencies
├── Procfile                  # Railway deployment config
├── runtime.txt              # Python version
├── templates/
│   ├── index.html           # หน้าหลักของแดชบอร์ด
│   ├── login.html           # หน้า login
│   └── account_settings.html
├── static/                  # Static files (CSS, JS, images)
│   ├── style.css
│   └── [image files]
└── README.md               # ไฟล์นี้
```

## 🔧 เทคโนโลยีที่ใช้
- **Backend**: Python Flask, SQLAlchemy
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Styling**: Windows 11 design system
- **Export/Import**: CSV format สำหรับ Google Sheets

## 🌐 การ Deploy บน Railway

### Automatic Deployment
1. เชื่อมต่อ GitHub repository กับ Railway
2. ตั้งค่า Environment Variables:
   - `RAILWAY_ENVIRONMENT=production`
3. Railway จะ deploy อัตโนมัติ

### Environment Variables
```bash
RAILWAY_ENVIRONMENT=production    # สำหรับใช้ PostgreSQL
PORT=8080                        # พอร์ตสำหรับ Railway
```

## 🎯 การใช้งาน

### ระบบโน้ต
1. คลิกปุ่ม 📝 ด้านล่างขวา
2. กรอกข้อมูล: วันที่เวลา, ยอดเงิน, ผู้เขียน, รายละเอียด
3. คลิก "เพิ่มโน้ต"
4. ใช้ปุ่ม ◀ ▶ สำหรับเปลี่ยนหน้า

### Export/Import CSV
1. **Export**: คลิก "📊 ส่งออก CSV" → ไฟล์จะดาวน์โหลด
2. **Google Sheets**: File → Import → Upload ไฟล์ CSV
3. **Import**: แก้ไขใน Sheets → Download CSV → คลิก "📥 นำเข้า CSV"

### เครื่องคิดเลข
1. คลิกปุ่ม 🔢 ด้านล่างขวา
2. ใช้เมาส์หรือคีย์บอร์ด
3. กด Escape เพื่อปิด

## 🔗 API Endpoints

### Notes System
- `GET /api/notes?page=1&per_page=10` - ดึงโน้ตแบบ pagination
- `POST /api/notes` - เพิ่มโน้ตใหม่
- `PUT /api/notes/<id>` - แก้ไขโน้ต
- `DELETE /api/notes/<id>` - ลบโน้ต
- `GET /api/notes/export` - ส่งออก CSV
- `POST /api/notes/import` - นำเข้า CSV

### SMS/Financial Data
- `GET /api/sms?tag=<tag>&sender=<sender>` - ดึงข้อมูล SMS
- `GET /api/kbiz_notifications` - ดึงข้อมูล Kbiz

## 📞 ติดต่อ
- Repository: https://github.com/flook2018-prog/Truewallet-Scb-TK
- Issues: https://github.com/flook2018-prog/Truewallet-Scb-TK/issues
- jQuery & Slick Carousel
- Node.js & Express.js (สำหรับ deployment)
- Responsive Design

## ลิขสิทธิ์
© 2024 THEKING888 - สงวนสิทธิ์ทุกประการ
>>>>>>> 4a369651b9ee0ff0919fa9153650f1a1d41be14c
