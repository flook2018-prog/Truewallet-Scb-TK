# โครงสร้างไฟล์และตำแหน่งต่างๆบนเว็บ TrueWallet-TK

## 📂 โครงสร้างไฟล์ทั้งหมด

```
Truewallet-Scb-TK/
├── app.py                      # Backend Flask Application (หลัก)
├── models.py                   # Database Models
├── scb_sms_api.py             # SCB SMS API Integration
├── requirements.txt            # Python Dependencies
├── runtime.txt                # Python Version
├── Procfile                   # Production Server Config
├── railway.toml               # Railway Deployment Config
├── nixpacks.toml              # Nixpacks Config
├── README.md                  # Project Documentation
├── DEPLOYMENT.md              # Deployment Guide
├── STRUCTURE.md               # This file
├── .venv/                     # Python Virtual Environment
├── .git/                      # Git Repository
├── instance/                  # Flask Instance Folder
├── __pycache__/               # Python Cache
├── uploads/                   # File Upload Storage
├── Photo/                     # Photo Albums by Date
│   ├── 1-7-68/ ... 31-7-68/  # Date folders
│   ├── โปรฝากทำเทิร์น/
│   ├── โปรโมชั่น/
│   ├── ฝาก 10-99 บาท/
│   ├── ฝาก 5 - 99 บาท/
│   └── ยิงแอด/
├── SEO-TK-SK/                # SEO Assets
├── TK-SEO/                   # SEO Assets
├── static/                   # Static Files
│   ├── style.css             # Main CSS Styles
│   ├── icons8-lion-head-64.png      # Favicon
│   ├── kbiz.png              # KBIZ Logo
│   ├── logo wallet.png       # Wallet Logo
│   ├── scb-logo.png          # SCB Logo
│   ├── ngox-header.png.png   # Header Image
│   └── 5e9e7571-ef8d-4e7c-9e51-6b50221aceec.png # Other Images
└── templates/                # HTML Templates
    ├── index.html            # Main Dashboard (หลัก)
    ├── login.html            # Login Page
    ├── account_settings.html # Account Settings
    ├── balance_marquee.html  # Balance Scrolling Display
    └── scb_sms.html          # SCB SMS Notifications
```

## 🌐 API Endpoints ทั้งหมด

### 🔓 Public Endpoints (ไม่ต้อง Login)
```
GET  /health              - Health Check (แบบง่าย)
GET  /health/db          - Health Check with Database Test
GET  /login              - Login Page
POST /login              - Login Form Submit
GET  /logout             - Logout
```

### 🔐 Protected Endpoints (ต้อง Login)
```
GET  /                   - Main Dashboard (index.html)
```

### 💰 Wallet & Transaction Endpoints
```
GET  /get_transactions           - ดึงรายการธุรกรรมทั้งหมด (new, approved, cancelled)
POST /approve                    - อนุมัติธุรกรรม
POST /cancel                     - ยกเลิกธุรกรรม
POST /restore                    - คืนสถานะธุรกรรมไปเป็น "new"
POST /reset_approved             - รีเซ็ตรายการอนุมัติ (require confirmation)
POST /reset_cancelled            - รีเซ็ตรายการยกเลิก (require confirmation)
POST /upload_slip/<txid>         - Upload ใบสลิปสำหรับธุรกรรม
GET  /slip/<filename>            - ดึงไฟล์ใบสลิป
```

### 📱 SMS Data Endpoints
```
GET  /api/sms?tag=<tag>&sender=<sender>    - ดึงข้อมูล SMS ล่าสุด 7 รายการ
POST /api/sms                              - เพิ่มข้อมูล SMS ใหม่
```

### 🏦 Webhook Endpoints
```
POST /webhook                    - TrueWallet Webhook (Generic)
POST /truewallet/webhook         - TrueWallet Webhook (Specific)
```

### 💳 Wallet Deposit Endpoints
```
POST /api/deposit_wallet         - เพิ่มข้อมูลฝากวอเลท
GET  /api/deposit_wallet         - ดึงรายการฝากวอเลท
GET  /api/wallet_deposit_data    - ดึงข้อมูลจาก External API + Decode JWT
GET  /api/truewallet_external_data - ดึงข้อมูล TrueWallet จาก External API
```

### 📝 Notes System Endpoints
```
GET    /api/notes                      - ดึงโน้ตทั้งหมด (มี pagination)
POST   /api/notes                      - สร้างโน้ตใหม่
PUT    /api/notes/<int:note_id>        - แก้ไขโน้ต
DELETE /api/notes/<int:note_id>        - ลบโน้ต
GET    /api/notes/export               - Export โน้ตเป็น CSV
POST   /api/notes/import               - Import โน้ตจาก CSV
```

### 🪙 Gold Price Endpoint
```
GET    /api/gold-price                 - ดึงราคาทองจาก Web Scraping
```

### 📢 KBIZ Notifications Endpoint
```
GET    /api/kbiz_notifications         - ดึงแจ้งเตือน Kbiz ล่าสุด 10 รายการ
POST   /api/kbiz_notifications         - เพิ่มแจ้งเตือน Kbiz ใหม่
```

## 📍 ตำแหน่งต่างๆบนเว็บ UI (index.html)

### 🎯 ส่วนหัว (Header)
```html
#header-logos              - โลโก้หัวเว็บ (THKBot168 + SKBot)
h1                         - หัวข้อ "Dashboard(Realtime)"
#toggle-mode              - ปุ่มเปลี่ยน Light/Dark Mode
```

### 👤 ปุ่มควบคุม (Controls)
```html
.account-settings-btn      - ปุ่ม ⚙️ ตั้งค่าระบบบัญชี
.logout-btn                - ปุ่มออกจากระบบ
```

### 📊 ส่วนบน (Top Summary Cards)
```html
#top-bar                   - ส่วนแสดงสรุปข้อมูล
.summary-card              - การ์ดข้อมูล 5 ใบดังนี้:
  
  1. Truewallet TK
     ID: #tw-tk-status-light    - ไฟสถานะ
         #tw-tk-status-text     - ข้อความสถานะ
         #tw-balance            - ยอดเงิน
         #tw-mobile             - เบอร์มือถือ
         #tw-updated            - เวลาอัปเดต
  
  2. SCB สุมิธร์
     ID: #account-balance-box
         #scb-status-light      - ไฟสถานะ
         #scb-status-text       - ข้อความสถานะ
         #account-balance-info  - ยอดเงิน
  
  3. SCB พลอยไพริน
     ID: #account-balance-box2
         #scb2-status-light     - ไฟสถานะ
         #scb2-status-text      - ข้อความสถานะ
         #account-balance-info2 - ยอดเงิน
  
  4. Truewallet BB ENJ
     ID: #tw-bb-box
         #tw-bb-status-light    - ไฟสถานะ
         #tw-bb-status-text     - ข้อความสถานะ
         #tw-bb-balance         - ยอดเงิน
  
  5. Truewallet BP
     ID: #tw-bp-box
         #tw-bp-status-light    - ไฟสถานะ
         #tw-bp-status-text     - ข้อความสถานะ
         #tw-bp-balance         - ยอดเงิน
```

### 💱 ส่วนอัตราแลกเปลี่ยน
```html
#exchange-rates-box        - กล่องอัตราแลกเปลี่ยนทอง
#gold-price                - ราคาทองคำแท่ง
#exchange-update-time      - เวลาอัปเดต
```

### 🏦 ส่วน SCB SMS Accounts

#### SCB ที่ 1 (สุมิธร์)
```html
#scb1-sms-table            - ตารางข้อมูล SMS
  - วันที่/เวลา
  - รายละเอียด
  - ยอดคงเหลือ
#scb1-connect-btn          - ปุ่มเชื่อมต่อ
```

#### SCB ที่ 2 (พลอยไพริน)
```html
#scb2-sms-table            - ตารางข้อมูล SMS
  - วันที่/เวลา
  - รายละเอียด
  - ยอดคงเหลือ
#scb2-connect-btn          - ปุ่มเชื่อมต่อ
```

#### SCB ที่ 3 (กฤษฏา)
```html
#scb3-sms-table            - ตารางข้อมูล SMS OTP (4 คอลัมน์)
  - วันที่/เวลา
  - Ref Code (แดง)
  - รายละเอียด
  - OTP (เขียว)
```

### 💳 ส่วน Wallet Deposit
```html
#wallet-deposit-section    - กล่องรายการฝากวอเลท
.deposit-item              - แต่ละรายการฝาก:
  - ธุรกรรมID
  - ชื่อผู้ส่ง
  - จำนวนเงิน
  - ธนาคาร
  - เวลา
  - สถานะ (new/approved/cancelled)
```

### ✅ ส่วน Approved Orders
```html
#approved-section          - กล่องรายการอนุมัติ
#approved-orders           - ตารางรายการอนุมัติ
#show-approved             - ปุ่มแสดงรายการอนุมัติ
```

### ❌ ส่วน Cancelled Orders
```html
#cancelled-section         - กล่องรายการยกเลิก
#cancelled-orders          - ตารางรายการยกเลิก
#show-cancelled            - ปุ่มแสดงรายการยกเลิก
```

### 🧮 เครื่องคิดเลข
```html
#calculator-overlay        - Overlay ของเครื่องคิดเลข
.calculator                - โครงสร้างเครื่องคิดเลข
#calc-display              - ที่แสดงผล
.calc-btn                  - ปุ่มตัวเลข
.calc-btn.operator         - ปุ่มการคำนวณ
```

## 🔄 Data Flow

```
┌─────────────────────────────────────────────┐
│           Frontend (index.html)             │
│  - Displays Summary Cards                   │
│  - Shows SMS Data in Tables                 │
│  - Shows Exchange Rates                     │
│  - Calculator                               │
└─────────────────────────────────────────────┘
         ↓                            ↓
┌─────────────────────┐    ┌─────────────────────┐
│  SMart API Calls    │    │ External Services   │
│  - /api/sms         │    │ - TrueWallet API    │
│  - /get_transactions│    │ - Gold Price Web    │
└─────────────────────┘    └─────────────────────┘
         ↓                            ↓
┌─────────────────────────────────────────────┐
│      Backend (app.py - Flask)               │
│  - Route Handlers                           │
│  - Database Operations                      │
│  - External API Integration                 │
│  - Web Scraping                             │
└─────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│      Database (PostgreSQL/SQLite)           │
│  - Notes Table                              │
│  - Transactions                             │
│  - User Sessions                            │
└─────────────────────────────────────────────┘
```

## 🗄️ Database Models

### Note Model
```python
id              - Primary Key (Integer)
datetime        - Date/Time (String)
amount          - Amount (String)
author          - Author Name (String)
details         - Details (Text)
created_at      - Creation Timestamp (DateTime)
updated_at      - Update Timestamp (DateTime)
```

## 📱 Tags สำหรับ SMS Data

- `sumitkimphiranon`    - SCB สุมิธร์
- `ploypairinnamkhot`   - SCB พลอยไพริน
- `168`                 - SCB กฤษฏา (จาก external API)

## 🔐 Authentication

```
- Username: admin
- Password: 1234
- Session Storage: Flask session (cookie-based)
```

## 🎨 Color Scheme

- ✅ Green (#28a745)    - Connected/Success
- ⚪ Gray (#ccc)        - Disconnected/Default
- 🔵 Blue (#007bff)    - Buttons
- 🟠 Orange (#ff9800)   - Balance Amount
- 🔴 Red (#e74c3c)     - Ref Code, Alerts
- 🟣 Purple (#6c3483)   - Account Number

## 📊 Session Management

```
session.logged_in       - Boolean (Login Status)
session.username        - Username (String)
ip_approver_map         - Maps IP to Approver Name
```

## 🔄 Real-time Updates

- Status Lights:  Updated every 5 seconds
- SMS Data:       Updated automatically when new data arrives
- Exchange Rate:  Updated every 60 seconds
- Gold Price:     Updated with refresh button or automatic interval

## 📋 Key Features

✅ Real-time Transaction Management
✅ Multi-Account SMS Monitoring
✅ Exchange Rate Display
✅ Gold Price Scraping
✅ File Upload & Download
✅ Notes System
✅ KBIZ Notifications
✅ Wallet Deposit Tracking
✅ Calculator Tool
✅ Dark/Light Mode Toggle
✅ Mobile Responsive
