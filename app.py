
# -------------------- Logout --------------------

# -------------------- Logout --------------------
# (Moved to after app = Flask(__name__))

from flask import Flask, request, jsonify, render_template, send_from_directory, send_file, redirect, url_for, session
import re
import os, json, jwt, random
from datetime import datetime, timedelta
import requests
import threading
from collections import defaultdict
from werkzeug.utils import secure_filename
import pytz
from models import DepositWallet
from flask_sqlalchemy import SQLAlchemy
import urllib.parse

# -------------------- Config --------------------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'your_secret_key_here'  # เปลี่ยนเป็นคีย์ลับจริงใน production

# -------------------- Database Configuration (เฉพาะระบบโน้ต) --------------------
# ใช้ PostgreSQL เฉพาะสำหรับระบบโน้ต
import os

# PostgreSQL สำหรับระบบโน้ต
if os.environ.get('RAILWAY_ENVIRONMENT'):
    # Production - Railway internal URL
    NOTES_DB_URL = "postgresql://postgres:MRPyUVazXbkBoMNBDIVArmCMCkQksKCj@postgres.railway.internal:5432/railway"
else:
    # Local development - ใช้ SQLite แทน (หรือใส่ External URL จาก Railway Dashboard)
    # หากต้องการใช้ PostgreSQL จริง ให้ไปที่ Railway Dashboard > Database > Connect
    # และคัดลอก External URL มาใส่ที่นี่
    NOTES_DB_URL = "sqlite:///notes.db"

# ตั้งค่าฐานข้อมูลเฉพาะโน้ต
app.config['SQLALCHEMY_DATABASE_URI'] = NOTES_DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# -------------------- Note Model --------------------
class Note(db.Model):
    __tablename__ = 'notes'
    
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.String(100))
    author = db.Column(db.String(100), default='ไม่ระบุ')
    details = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow())
    updated_at = db.Column(db.DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())
    
    def to_dict(self):
        return {
            'id': self.id,
            'datetime': self.datetime,
            'amount': self.amount,
            'author': self.author,
            'details': self.details,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }

# -------------------- Kbiz Withdraw Notification (เฟซใหม่) --------------------
from threading import Lock
kbiz_notifications = []
kbiz_lock = Lock()

# --- ฟังก์ชันแยกข้อความแจ้งเตือน Kbiz ---
def parse_kbiz_message(msg):
    # ตัวอย่างข้อความ: "ทำรายการสำเร็จ โอนเงินให้ นายณัฐวุฒิ สงวนทรัพย์ บช x-9702x จำนวน 100.00 บาท"
    import urllib.parse
    amount = None
    time = None
    desc = None
    # 0. Clean msg: decode %20, remove trailing timestamp (ถ้ามี)
    msg = urllib.parse.unquote(msg)
    # Remove trailing numbers (timestamp) after "บาท" (เช่น ...บาท1758027469330)
    msg = re.sub(r'(บาท)\d{10,}$', r'\1', msg)
    # 1. พยายามดึงยอดเงิน ("จำนวน ... บาท" หรือ "จำนวน...บาท")
    m = re.search(r'จำนวน\s*([\d,]+\.\d{2})\s*บาท', msg)
    if m:
        amount = m.group(1).replace(',', '')
        desc = msg[:m.start()].strip()
    else:
        # 2. ถ้าไม่มี 'จำนวน ... บาท' ให้หาเลขยอดเงินในข้อความ (เช่น 100.00)
        m2 = re.search(r'([\d,]+\.\d{2})', msg)
        if m2:
            amount = m2.group(1).replace(',', '')
            # ลบเลขยอดเงินออกจาก desc
            desc = msg.replace(m2.group(0), '').replace('จำนวน', '').replace('บาท', '').strip()
        else:
            # 3. ไม่เจอเลขเลย amount=None, desc=เต็มข้อความ
            amount = None
            desc = msg.strip()

    # 4. ดึงเวลา (dd/mm/yyyy hh:mm:ss หรือ hh:mm)
    t = re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})', msg)
    if t:
        time = t.group(1)
    else:
        t2 = re.search(r'(\d{2}:\d{2})', msg)
        if t2:
            time = t2.group(1)
        else:
            time = None

    # 5. ถ้า desc ยาวเกิน 60 ตัวอักษร ให้ตัด ...
    if desc and len(desc) > 60:
        desc = desc[:57] + '...'

    # 6. ถ้า amount ไม่ใช่ตัวเลข ให้ None
    try:
        if amount is not None:
            float(amount)
    except Exception:
        amount = None

    # 7. ถ้า desc เป็นค่าว่าง ให้ desc = "-"
    if not desc:
        desc = "-"

    # 8. รองรับ field ใหม่: ถ้ามีข้อมูลอื่นที่ไม่ใช่ amount/desc/time ให้เพิ่มใน dict
    result = {
        'amount': amount,
        'desc': desc,
        'time': time
    }
    # ถ้าเจอ field อื่นในข้อความ (เช่น "wallet_type" หรืออื่นๆ ในอนาคต) สามารถเพิ่ม logic ตรงนี้ได้
    return result

# POST: รับแจ้งเตือนใหม่, GET: ดึงรายการแจ้งเตือนล่าสุด (max 10)


# --- API รับแจ้งเตือน Kbiz (รองรับข้อความรวม) ---
@app.route('/api/kbiz_notifications', methods=['GET', 'POST'])
def kbiz_notifications_api():
    global kbiz_notifications
    if request.method == 'POST':
        data = request.get_json(force=True)
        # ถ้ามี field 'raw_message' ให้แยกส่วน
        if 'raw_message' in data:
            parsed = parse_kbiz_message(data['raw_message'])
            # ถ้า field 'time' ไม่ถูกส่งมาด้วย ให้ใช้เวลาจาก parsed หรือเวลาปัจจุบัน
            if not data.get('time'):
                if parsed.get('time'):
                    data['time'] = parsed['time']
                else:
                    # fallback: เวลาปัจจุบัน (Asia/Bangkok)
                    data['time'] = datetime.now(pytz.timezone('Asia/Bangkok')).strftime('%d/%m/%Y %H:%M:%S')
            data.update(parsed)
        else:
            # ถ้าไม่มี raw_message แต่มี time ใน data ให้ใช้เลย, ถ้าไม่มีให้ fallback
            if not data.get('time'):
                data['time'] = datetime.now(pytz.timezone('Asia/Bangkok')).strftime('%d/%m/%Y %H:%M:%S')
        with kbiz_lock:
            kbiz_notifications.insert(0, data)
            kbiz_notifications = kbiz_notifications[:10]
        return jsonify({"status": "ok"})
    elif request.method == 'GET' and 'raw_message' in request.args:
        # รับข้อความรวมผ่าน GET
        msg = request.args.get('raw_message')
        parsed = parse_kbiz_message(msg)
        # ถ้าไม่มี time ใน parsed ให้ fallback เป็นเวลาปัจจุบัน
        if not parsed.get('time'):
            parsed['time'] = datetime.now(pytz.timezone('Asia/Bangkok')).strftime('%d/%m/%Y %H:%M:%S')
        with kbiz_lock:
            kbiz_notifications.insert(0, parsed)
            kbiz_notifications = kbiz_notifications[:10]
        return jsonify({"status": "ok", "via": "GET"})
    elif request.method == 'GET' and any(k in request.args for k in ['amount','desc','time','image']):
        # รับแจ้งเตือนแบบแยก field เดิม
        data = {
            'amount': request.args.get('amount'),
            'desc': request.args.get('desc'),
            'time': request.args.get('time'),
            'image': request.args.get('image')
        }
        data = {k: v for k, v in data.items() if v is not None}

        def is_invalid(val):
            return (not val) or (isinstance(val, str) and val.strip() in ('-', 'None', 'null', 'undefined'))

        all_fields = [data.get('amount'), data.get('desc'), data.get('time')]
        # ถ้า amount, desc, time เป็นข้อความเดียวกันหมด หรือว่างหมด หรือ amount ไม่ใช่ตัวเลข
        if (len(set([v for v in all_fields if v])) == 1 and all_fields[0]) or all(is_invalid(v) for v in all_fields) or ('amount' in data and (not data['amount'] or not data['amount'].replace(",", "").replace(".", "").isdigit())):
            # ลอง parse ข้อความจาก amount ก่อน ถ้าไม่มีลอง desc
            msg = data.get('amount') or data.get('desc') or ''
            parsed = parse_kbiz_message(msg)
            for k in ['amount', 'desc', 'time']:
                if parsed.get(k):
                    data[k] = parsed[k]
        # ถ้าไม่มี time ใน data ให้ fallback เป็นเวลาปัจจุบัน
        if not data.get('time'):
            data['time'] = datetime.now(pytz.timezone('Asia/Bangkok')).strftime('%d/%m/%Y %H:%M:%S')
        with kbiz_lock:
            kbiz_notifications.insert(0, data)
            kbiz_notifications = kbiz_notifications[:10]
        return jsonify({"status": "ok", "via": "GET"})
    else:
        with kbiz_lock:
            return jsonify({"notifications": kbiz_notifications[:10]})

# -------------------- Logout --------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



# Proxy endpoint สำหรับ wallet deposit (GET ข้อมูลจาก API กลาง + decode JWT)
@app.route('/api/wallet_deposit_data')
def wallet_deposit_data():
    try:
        url = 'https://xinonshow789-production.up.railway.app/truewallet/webhook'
        headers = {'Authorization': 'Bearer defbe102c9f4e9eaad1e16de7f8efe13'}
        resp = requests.get(url, headers=headers, timeout=10)
        try:
            data = resp.json()
        except Exception as json_err:
            print("WALLET DEPOSIT ERROR: JSON decode", json_err)
            print("RESPONSE TEXT:", resp.text)
            return jsonify({'error': f'JSON decode error: {json_err}', 'resp_text': resp.text}), 500
        # ถ้า data เป็น list (อนาคต), return ได้เลย
        if isinstance(data, list):
            return jsonify({"new_orders": data})
        # ถ้า data เป็น dict ที่มี message (JWT หรือ error string)
        if "message" in data:
            token = data["message"]
            # ถ้า message ไม่ใช่ JWT (เช่น Application not found) ให้ fallback ไปอ่านไฟล์ local
            if not isinstance(token, str) or token.count('.') != 2:
                print("WALLET DEPOSIT: message is not JWT, got:", token)
                # fallback: อ่าน new_orders จากไฟล์ local
                try:
                    with open(DATA_FILE, "r", encoding="utf-8") as f:
                        local_data = json.load(f)
                        new_orders = local_data.get("new", [])
                        return jsonify({"new_orders": new_orders})
                except Exception as e:
                    print("WALLET DEPOSIT: fallback local error", e)
                    return jsonify({"new_orders": []})
            import jwt
            try:
                decoded = jwt.decode(token, "defbe102c9f4e9eaad1e16de7f8efe13", algorithms=["HS256"], options={"verify_iat": False})
                tx = {
                    "id": decoded.get("transaction_id", ""),
                    "event": decoded.get("event_type", ""),
                    "amount": decoded.get("amount", 0),
                    "amount_str": f"{decoded.get('amount',0)/100:,.2f}",
                    "name": f"{decoded.get('sender_name','-')} / {decoded.get('sender_mobile','-')}",
                    "bank": decoded.get("channel", "-"),
                    "status": "new",
                    "time": decoded.get("received_time", ""),
                    "slip_filename": None
                }
                return jsonify({"new_orders": [tx]})
            except Exception as e:
                print("WALLET DEPOSIT ERROR: JWT decode", e)
                print("RAW MESSAGE:", token)
                # fallback: อ่าน new_orders จากไฟล์ local
                try:
                    with open(DATA_FILE, "r", encoding="utf-8") as f:
                        local_data = json.load(f)
                        new_orders = local_data.get("new", [])
                        return jsonify({"new_orders": new_orders})
                except Exception as e2:
                    print("WALLET DEPOSIT: fallback local error", e2)
                    return jsonify({"new_orders": []})
        print("WALLET DEPOSIT ERROR: No data", data)
        # fallback: อ่าน new_orders จากไฟล์ local
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                local_data = json.load(f)
                new_orders = local_data.get("new", [])
                return jsonify({"new_orders": new_orders})
        except Exception as e:
            print("WALLET DEPOSIT: fallback local error", e)
            return jsonify({"new_orders": []})
    except Exception as e:
        print("WALLET DEPOSIT ERROR: Outer", e)
        return jsonify({'error': str(e)}), 500

accounts_file = "accounts.json"
accounts_lock = threading.Lock()

transactions = {"new": [], "approved": [], "cancelled": []}
daily_summary_history = defaultdict(float)
ip_approver_map = {}

DATA_FILE = "transactions_data.json"
LOG_FILE = "transactions.log"

# --- ฟังก์ชันโหลด/บันทึกธุรกรรม ---
def load_transactions():
    global transactions
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k in ["new", "approved", "cancelled"]:
                    transactions[k] = data.get(k, [])
        except Exception as e:
            print("Error loading transactions:", e)

def save_transactions():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(transactions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving transactions:", e)

# โหลดธุรกรรมจากไฟล์เมื่อเริ่มต้น
load_transactions()

deposit_wallets = []  # รายการฝากวอเลทใหม่


# API สำหรับฝากวอเลทใหม่ (ไม่กระทบระบบเก่า)
@app.route("/api/deposit_wallet", methods=["POST"])
def api_deposit_wallet():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"status":"error","message":"No JSON received"}), 400
        txid = data.get("transaction_id") or f"TX{len(deposit_wallets)+1}"
        if any(tx.id == txid for tx in deposit_wallets):
            return jsonify({"status":"success","message":"Transaction exists"}), 200
        amount = int(data.get("amount",0))
        sender_name = data.get("sender_name","-")
        sender_mobile = data.get("sender_mobile","-")
        name = f"{sender_name} / {sender_mobile}" if sender_mobile and sender_mobile != "-" else sender_name
        event_type = data.get("event_type","ฝาก").upper()
        bank_code = (data.get("channel") or "").upper()
        if event_type=="P2P" or bank_code in ["TRUEWALLET","WALLET"]:
            bank_name_th="ทรูวอเลท"
        elif bank_code in BANK_MAP_TH:
            bank_name_th=BANK_MAP_TH[bank_code]
        elif bank_code:
            bank_name_th=bank_code
        else:
            bank_name_th="-"
        time_str = data.get("received_time") or datetime.utcnow().isoformat()
        try:
            tx_time_utc = datetime.fromisoformat(time_str)
        except:
            tx_time_utc = datetime.utcnow()
        tx = DepositWallet(
            id=txid,
            event=event_type,
            amount=amount,
            amount_str=f"{amount/100:,.2f}",
            name=name,
            bank=bank_name_th,
            status="new",
            time=tx_time_utc.isoformat(),
            slip_filename=None
        )
        deposit_wallets.append(tx)
        return jsonify({"status":"success"}), 200
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

# API สำหรับดึงรายการฝากวอเลทใหม่
@app.route("/api/deposit_wallet", methods=["GET"])
def get_deposit_wallets():
    return jsonify([tx.to_dict() for tx in deposit_wallets])
SECRET_KEY = "defbe102c9f4e9eaad1e16de7f8efe13"

# กำหนด timezone
TZ = pytz.timezone("Asia/Bangkok")

BANK_MAP_TH = {
    "BBL": "กรุงเทพ",
    "KBANK": "กสิกรไทย",
    "SCB": "ไทยพาณิชย์",
    "KTB": "กรุงไทย",
    "BAY": "กรุงศรีอยุธยา",
    "TMB": "ทหารไทย",
    "TRUEWALLET": "ทรูวอเลท",
    "7-ELEVEN": "7-Eleven",
}

# -------------------- Webhook TrueWallet (สำหรับ endpoint /webhook) --------------------
@app.route("/webhook", methods=["POST"])
def generic_truewallet_webhook():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            log_with_time("[WEBHOOK ERROR] No JSON received (generic /webhook)")
            return jsonify({"status":"error","message":"No JSON received"}), 400

        message_jwt = data.get("message")
        decoded = None
        if message_jwt:
            try:
                decoded = jwt.decode(message_jwt, SECRET_KEY, algorithms=["HS256"])
            except Exception as e:
                log_with_time("[JWT ERROR] /webhook", str(e))
                # ถ้า decode ไม่ผ่าน ให้ใช้ payload ดิบแทน
                decoded = data
        else:
            decoded = data

        txid = decoded.get("transaction_id") or f"TX{len(transactions['new'])+len(transactions['approved'])+len(transactions['cancelled'])+1}"

        if any(tx["id"] == txid for lst in transactions.values() for tx in lst):
            return jsonify({"status":"success","message":"Transaction exists"}), 200

        amount = int(decoded.get("amount",0))
        sender_name = decoded.get("sender_name","-")
        sender_mobile = decoded.get("sender_mobile","-")
        name = f"{sender_name} / {sender_mobile}" if sender_mobile and sender_mobile != "-" else sender_name

        event_type = decoded.get("event_type","d").upper()
        bank_code = (decoded.get("channel") or "").upper()

        if event_type=="P2P" or bank_code in ["TRUEWALLET","WALLET"]:
            bank_name_th="ทรูวอเลท"
        elif bank_code in BANK_MAP_TH:
            bank_name_th=BANK_MAP_TH[bank_code]
        elif bank_code:
            bank_name_th=bank_code
        else:
            bank_name_th="-"

        time_str = decoded.get("received_time") or datetime.utcnow().isoformat()
        try:
            tx_time_utc = datetime.fromisoformat(time_str)
        except:
            tx_time_utc = datetime.utcnow()

        tx = {
            "id": txid,
            "event": event_type,
            "amount": amount,
            "amount_str": f"{amount/100:,.2f}",
            "name": name,
            "bank": bank_name_th,
            "status": "new",
            "time": tx_time_utc.isoformat(),
            "slip_filename": None
        }

        transactions["new"].append(tx)
        save_transactions()
        log_with_time("[WEBHOOK RECEIVED] /webhook", tx)
        return jsonify({"status":"success"}), 200

    except Exception as e:
        log_with_time("[WEBHOOK EXCEPTION] /webhook", str(e))
        return jsonify({"status":"error","message":str(e)}), 500

# -------------------- Helpers --------------------
def save_transactions():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(transactions, f, ensure_ascii=False, indent=2)

def log_with_time(*args):
    ts = datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
    msg = f"[{ts}] " + " ".join(str(a) for a in args)
    print(msg, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def random_english_name():
    names = ["Alice","Bob","Charlie","David","Eve","Frank","Grace","Hannah","Ian","Jack","Kathy","Leo","Mia","Nina","Oscar"]
    return random.choice(names)

def fmt_time_local(t):
    if isinstance(t, str):
        try:
            dt = datetime.fromisoformat(t)
        except:
            return t
    elif isinstance(t, datetime):
        dt = t
    else:
        return str(t)
    return dt.astimezone(TZ).strftime("%Y-%m-%d %H:%M:%S")

def fmt_amount(a):
    return f"{a/100:,.2f}" if isinstance(a,(int,float)) else str(a)

# -------------------- Flask Endpoints --------------------

# -------------------- Login --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # ตัวอย่าง: username=admin, password=1234 (ควรเปลี่ยนเป็นระบบจริง)
        if username == 'admin' and password == '1234':
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            error = 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'
    return render_template('login.html', error=error)

@app.route("/")
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    user_ip = request.remote_addr or "unknown"
    return render_template("index.html", user_ip=user_ip)

@app.route("/get_transactions")
def get_transactions():
    # เรียงรายการใหม่, อนุมัติ, ยกเลิก
    new_orders = transactions["new"][-20:][::-1]
    approved_orders = transactions["approved"][-20:][::-1]
    cancelled_orders = transactions["cancelled"][-20:][::-1]

    wallet_daily_total = sum(tx["amount"] for tx in approved_orders)
    wallet_daily_total_str = fmt_amount(wallet_daily_total)

    # ฟอร์แมตเวลาเป็น Asia/Bangkok
    for tx in new_orders:
        tx["time_str"] = fmt_time_local(tx.get("time"))
    for tx in approved_orders:
        tx["time_str"] = fmt_time_local(tx.get("time"))
        tx["approved_time_str"] = fmt_time_local(tx.get("approved_time"))
    for tx in cancelled_orders:
        tx["time_str"] = fmt_time_local(tx.get("time"))
        tx["cancelled_time_str"] = fmt_time_local(tx.get("cancelled_time"))

    # ส่งค่า customer_user กลับไปด้วยเสมอ
    for lst in [new_orders, approved_orders, cancelled_orders]:
        for tx in lst:
            if "customer_user" not in tx:
                tx["customer_user"] = ""

    # สร้างข้อมูลกราฟยอดรายวัน
    daily_user_summary = defaultdict(lambda: defaultdict(int))
    for tx in approved_orders:
        user = tx.get("customer_user")
        if user and user.startswith("thk") and user[3:].isdigit():
            day = tx["time"][:10] if isinstance(tx["time"], str) else tx["time"].strftime("%Y-%m-%d")
            daily_user_summary[day][user] += tx["amount"]

    return jsonify({
        "new_orders": new_orders,
        "approved_orders": approved_orders,
        "cancelled_orders": cancelled_orders,
        "wallet_daily_total": wallet_daily_total_str,
        "daily_summary": [{"date": d, "total": fmt_amount(v)} for d,v in sorted(daily_summary_history.items())],
        "daily_user_summary": daily_user_summary
    })



# -------------------- API สำหรับ SMS (จริง) --------------------
import threading
sms_data_file = "sms_data.json"
sms_data_lock = threading.Lock()

def load_sms_data():
    try:
        with open(sms_data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            # กรณีเก่าเป็น list ให้แปลงเป็น dict
            return {"default": data}
    except Exception:
        return {}

def save_sms_data(sms_dict):
    with sms_data_lock:
        with open(sms_data_file, "w", encoding="utf-8") as f:
            json.dump(sms_dict, f, ensure_ascii=False, indent=2)


@app.route("/api/sms", methods=["GET"])
def api_sms_get():
    tag = request.args.get("tag", "default")
    sender = request.args.get("sender")
    sms_content = request.args.get("sms") or request.args.get("body")
    sms_dict = load_sms_data()
    if tag not in sms_dict:
        sms_dict[tag] = []
    # รับ sender และ sms_content จาก GET แล้วบันทึกลง tag ที่ถูกต้อง (แปลงเป็น date_time, detail, balance ถ้า pattern ตรง)
    if sender and sms_content:
        import re
        date_time = None
        detail = None
        balance = None
        print(f"[DEBUG] /api/sms GET: tag={tag}, sender={sender}, sms_content={sms_content}")
        m = re.match(r"(\d{2}/\d{2}@\d{2}:\d{2}) (.+) (จาก.+|ถอน/.+|โอนเงิน.+) ใช้ได้([\d,]+\.?\d*)บ", sms_content)
        if m:
            date_time = m.group(1)
            detail = m.group(2) + ' ' + m.group(3)
            balance = m.group(4) + 'บ'
        else:
            parts = sms_content.split()
            if len(parts) >= 3:
                date_time = parts[0]
                detail = ' '.join(parts[1:-1])
                balance = parts[-1]
        if date_time and detail and balance:
            sms_dict[tag].append({"date_time": date_time, "detail": detail, "balance": balance})
            print(f"[DEBUG] Saved parsed SMS: tag={tag}, date_time={date_time}, detail={detail}, balance={balance}")
        else:
            sms_dict[tag].append({"sender": sender, "sms": sms_content})
            print(f"[DEBUG] Saved raw SMS: tag={tag}, sender={sender}, sms={sms_content}")
        save_sms_data(sms_dict)
    # รองรับการดึงข้อมูลล่าสุด 7 รายการของ tag นั้น
    sms_list = sms_dict.get(tag, [])
    # Determine connection status: connected if any SMS in last 24h
    status = "disconnected"
    now = datetime.now(TZ)
    for sms in sms_list[::-1]:
        dt_str = sms.get("date_time")
        try:
            # Try to parse date_time in format 'DD/MM@HH:MM'
            if dt_str and "/" in dt_str and "@" in dt_str:
                day, rest = dt_str.split("/")
                month, timepart = rest.split("@")
                hour, minute = timepart.split(":")
                sms_dt = now.replace(day=int(day), month=int(month), hour=int(hour), minute=int(minute), second=0, microsecond=0)
                # If SMS is within last 24 hours, consider connected
                if (now - sms_dt).total_seconds() < 86400:
                    status = "connected"
                    break
        except Exception:
            continue
    resp = jsonify({
        "sms": sms_list[-7:][::-1],
        "status": status
    })
    resp.headers.add('Access-Control-Allow-Origin', '*')
    return resp

@app.route("/api/sms", methods=["POST"])
def api_sms_post():
    tag = request.args.get("tag") or request.json.get("tag") or "default"
    data = request.get_json(force=True, silent=True) or {}
    date_time = data.get("date_time") or request.args.get("date_time")
    detail = data.get("detail") or request.args.get("detail")
    balance = data.get("balance") or request.args.get("balance")
    body = data.get("body") or request.args.get("body")
    if body and not (date_time and detail and balance):
        import re
        m = re.match(r"(\d{2}/\d{2}@\d{2}:\d{2}) (.+) (จาก.+|ถอน/.+|โอนเงิน.+) ใช้ได้([\d,]+\.?\d*)บ", body)
        if m:
            date_time = m.group(1)
            detail = m.group(2) + ' ' + m.group(3)
            balance = m.group(4) + 'บ'
        else:
            parts = body.split()
            if len(parts) >= 3:
                date_time = parts[0]
                detail = ' '.join(parts[1:-1])
                balance = parts[-1]
    if not (date_time and detail and balance):
        resp = jsonify({"status":"error","message":"ข้อมูลไม่ครบ"})
        resp.headers.add('Access-Control-Allow-Origin', '*')
        return resp, 400
    sms_dict = load_sms_data()
    if tag not in sms_dict:
        sms_dict[tag] = []
    sms_dict[tag].append({"date_time": date_time, "detail": detail, "balance": balance})
    save_sms_data(sms_dict)
    resp = jsonify({"status":"success"})
    resp.headers.add('Access-Control-Allow-Origin', '*')
    return resp, 200
@app.route("/approve", methods=["POST"])
def approve():
    txid = request.json.get("id")
    customer_user = request.json.get("customer_user")
    user_ip = request.remote_addr or "unknown"
    if user_ip not in ip_approver_map:
        ip_approver_map[user_ip] = random_english_name()
    approver_name = ip_approver_map[user_ip]

    for tx in transactions["new"]:
        if tx["id"] == txid:
            tx["status"] = "approved"
            tx["approver_name"] = approver_name
            tx["approved_time"] = datetime.utcnow().isoformat()
            # รองรับค่าว่าง ไม่บังคับใส่ customer_user
            if customer_user is not None:
                tx["customer_user"] = customer_user
            transactions["approved"].append(tx)
            transactions["new"].remove(tx)
            day = tx["time"][:10] if isinstance(tx["time"], str) else tx["time"].strftime("%Y-%m-%d")
            daily_summary_history[day] += tx["amount"]
            log_with_time(f"[APPROVED] {txid} by {approver_name} ({user_ip}) for customer {customer_user}")
            break
    save_transactions()
    return jsonify({"status": "success"}), 200

@app.route("/cancel", methods=["POST"])
def cancel():
    txid = request.json.get("id")
    user_ip = request.remote_addr or "unknown"
    if user_ip not in ip_approver_map:
        ip_approver_map[user_ip] = random_english_name()
    canceler_name = ip_approver_map[user_ip]

    for tx in transactions["new"]:
        if tx["id"] == txid:
            tx["status"] = "cancelled"
            tx["cancelled_time"] = datetime.utcnow().isoformat()
            tx["canceler_name"] = canceler_name
            # ไม่บังคับต้องมี customer_user
            transactions["cancelled"].append(tx)
            transactions["new"].remove(tx)
            log_with_time(f"[CANCELLED] {txid} by {canceler_name} ({user_ip})")
            break
    save_transactions()
    return jsonify({"status": "success"}), 200

@app.route("/restore", methods=["POST"])
def restore():
    txid = request.json.get("id")
    for lst in [transactions["approved"], transactions["cancelled"]]:
        for tx in lst:
            if tx["id"] == txid:
                tx["status"] = "new"
                tx.pop("approver_name", None)
                tx.pop("approved_time", None)
                tx.pop("canceler_name", None)
                tx.pop("cancelled_time", None)
                tx.pop("customer_user", None)
                transactions["new"].append(tx)
                lst.remove(tx)
                log_with_time(f"[RESTORED] {txid}")
                break
    save_transactions()
    return jsonify({"status": "success"}), 200

# -------------------- Reset --------------------
@app.route("/reset_approved", methods=["POST"])
def reset_approved():
    if not request.json.get("confirm"):
        return jsonify({"status":"error","message":"No confirm"}), 400
    count = len(transactions["approved"])
    transactions["approved"].clear()
    save_transactions()
    log_with_time(f"[RESET APPROVED] Cleared {count} approved transactions")
    return jsonify({"status":"success","cleared":count})

@app.route("/reset_cancelled", methods=["POST"])
def reset_cancelled():
    if not request.json.get("confirm"):
        return jsonify({"status":"error","message":"No confirm"}), 400
    count = len(transactions["cancelled"])
    transactions["cancelled"].clear()
    save_transactions()
    log_with_time(f"[RESET CANCELLED] Cleared {count} cancelled transactions")
    return jsonify({"status":"success","cleared":count})

# -------------------- Webhook TrueWallet --------------------
@app.route("/truewallet/webhook", methods=["POST"])
def truewallet_webhook():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            log_with_time("[WEBHOOK ERROR] No JSON received")
            return jsonify({"status":"error","message":"No JSON received"}), 400

        message_jwt = data.get("message")
        decoded = None
        if message_jwt:
            try:
                decoded = jwt.decode(message_jwt, SECRET_KEY, algorithms=["HS256"])
            except Exception as e:
                log_with_time("[JWT ERROR]", str(e))
                # ถ้า decode ไม่ผ่าน ให้ใช้ payload ดิบแทน
                decoded = data
        else:
            decoded = data

        txid = decoded.get("transaction_id") or f"TX{len(transactions['new'])+len(transactions['approved'])+len(transactions['cancelled'])+1}"

        if any(tx["id"] == txid for lst in transactions.values() for tx in lst):
            return jsonify({"status":"success","message":"Transaction exists"}), 200

        amount = int(decoded.get("amount",0))
        sender_name = decoded.get("sender_name","-")
        sender_mobile = decoded.get("sender_mobile","-")
        name = f"{sender_name} / {sender_mobile}" if sender_mobile and sender_mobile != "-" else sender_name

        event_type = decoded.get("event_type","ฝาก").upper()
        bank_code = (decoded.get("channel") or "").upper()

        if event_type=="P2P" or bank_code in ["TRUEWALLET","WALLET"]:
            bank_name_th="ทรูวอเลท"
        elif bank_code in BANK_MAP_TH:
            bank_name_th=BANK_MAP_TH[bank_code]
        elif bank_code:
            bank_name_th=bank_code
        else:
            bank_name_th="-"

        time_str = decoded.get("received_time") or datetime.utcnow().isoformat()
        try:
            tx_time_utc = datetime.fromisoformat(time_str)
        except:
            tx_time_utc = datetime.utcnow()

        tx = {
            "id": txid,
            "event": event_type,
            "amount": amount,
            "amount_str": f"{amount/100:,.2f}",
            "name": name,
            "bank": bank_name_th,
            "status": "new",
            "time": tx_time_utc.isoformat(),
            "slip_filename": None
        }

        transactions["new"].append(tx)
        save_transactions()
        log_with_time("[WEBHOOK RECEIVED]", tx)
        return jsonify({"status":"success"}), 200

    except Exception as e:
        log_with_time("[WEBHOOK EXCEPTION]", str(e))
        return jsonify({"status":"error","message":str(e)}), 500

# -------------------- Upload Slip --------------------
@app.route("/upload_slip/<txid>", methods=["POST"])
def upload_slip(txid):
    if "file" not in request.files:
        return jsonify({"status":"error","message":"No file"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status":"error","message":"Empty filename"}), 400

    # ป้องกันไฟล์ซ้ำด้วย timestamp
    filename = datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)

    for lst in [transactions["new"], transactions["approved"], transactions["cancelled"]]:
        for tx in lst:
            if tx["id"] == txid:
                tx["slip_filename"] = filename
                save_transactions()
                log_with_time(f"[UPLOAD SLIP] {txid} saved as {filename}")
                return jsonify({"status":"success","filename": filename}), 200
    return jsonify({"status":"error","message":"TX not found"}), 404

@app.route("/slip/<filename>")
def get_slip(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# -------------------- Notes API --------------------
@app.route('/api/notes', methods=['GET'])
def get_notes():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        notes = Note.query.order_by(Note.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'status': 'success',
            'data': [note.to_dict() for note in notes.items],
            'pagination': {
                'total': notes.total,
                'pages': notes.pages,
                'current_page': notes.page,
                'per_page': notes.per_page,
                'has_next': notes.has_next,
                'has_prev': notes.has_prev
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/notes', methods=['POST'])
def create_note():
    try:
        data = request.get_json()
        
        new_note = Note(
            datetime=data.get('datetime'),
            amount=data.get('amount', ''),
            author=data.get('author', 'ไม่ระบุ'),
            details=data.get('details')
        )
        
        db.session.add(new_note)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'data': new_note.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    try:
        note = Note.query.get_or_404(note_id)
        data = request.get_json()
        
        note.datetime = data.get('datetime', note.datetime)
        note.amount = data.get('amount', note.amount)
        note.author = data.get('author', note.author)
        note.details = data.get('details', note.details)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'data': note.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    try:
        note = Note.query.get_or_404(note_id)
        db.session.delete(note)
        db.session.commit()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/notes/export', methods=['GET'])
def export_notes():
    try:
        # Export เป็น CSV สำหรับ Google Sheets เท่านั้น
        notes = Note.query.order_by(Note.created_at.desc()).all()
        
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['วันที่เวลา', 'ยอดเงิน', 'ผู้เขียน', 'รายละเอียด', 'วันที่สร้าง'])
        
        # Data
        for note in notes:
            writer.writerow([
                note.datetime,
                note.amount or '',
                note.author,
                note.details,
                note.created_at.strftime('%Y-%m-%d %H:%M:%S') if note.created_at else ''
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=notes_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/notes/import', methods=['POST'])
def import_notes():
    try:
        # รองรับเฉพาะไฟล์ CSV
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'ไม่มีไฟล์'}), 400
            
        file = request.files['file']
        if not file.filename:
            return jsonify({'status': 'error', 'message': 'ไม่มีไฟล์'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'status': 'error', 'message': 'รองรับเฉพาะไฟล์ .csv เท่านั้น'}), 400
        
        file_content = file.read().decode('utf-8')
        
        # Import CSV
        import csv
        import io
        
        csv_data = csv.reader(io.StringIO(file_content))
        headers = next(csv_data)  # ข้าม header
        
        imported_count = 0
        for row in csv_data:
            if len(row) >= 4:  # ต้องมีอย่างน้อย 4 คอลัมน์
                # ตรวจสอบว่ามี note ที่ซ้ำหรือไม่
                existing = Note.query.filter_by(
                    datetime=row[0],
                    details=row[3]
                ).first()
                
                if not existing:
                    new_note = Note(
                        datetime=row[0],
                        amount=row[1] if len(row) > 1 else '',
                        author=row[2] if len(row) > 2 else 'ไม่ระบุ',
                        details=row[3]
                    )
                    db.session.add(new_note)
                    imported_count += 1
        
        db.session.commit()
        return jsonify({
            'status': 'success',
            'imported_count': imported_count,
            'total_count': sum(1 for line in io.StringIO(file_content)) - 1  # ลบ header
        })
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# -------------------- Run --------------------
if __name__ == "__main__":
    # สร้างตารางฐานข้อมูล
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Error creating database tables: {e}")
    
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                transactions.update(json.load(f))
            except:
                pass
    
    # ใช้ PORT จาก environment variable สำหรับ Railway
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port, debug=False)









