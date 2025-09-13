from flask import Flask, request, jsonify, render_template, send_from_directory
import os, json, jwt, random
from datetime import datetime, timedelta
from collections import defaultdict
from werkzeug.utils import secure_filename
import pytz

# -------------------- Config --------------------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

transactions = {"new": [], "approved": [], "cancelled": []}
daily_summary_history = defaultdict(float)
ip_approver_map = {}

DATA_FILE = "transactions_data.json"
LOG_FILE = "transactions.log"
SECRET_KEY = "f557ff6589e6d075581d68df1d4f3af7"

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
@app.route("/")
def index():
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

    # ✅ ส่งค่า customer_user กลับไปด้วยเสมอ
    for lst in [new_orders, approved_orders, cancelled_orders]:
        for tx in lst:
            if "customer_user" not in tx:
                tx["customer_user"] = ""

    # สร้างข้อมูลกราฟยอดฝากรายวัน
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

# -------------------- Approve / Cancel / Restore --------------------
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
        decoded = {}
        if message_jwt:
            try:
                decoded = jwt.decode(message_jwt, SECRET_KEY, algorithms=["HS256"])
            except Exception as e:
                log_with_time("[JWT ERROR]", str(e))
                return jsonify({"status":"error","message":"Invalid JWT"}), 400
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

# -------------------- Run --------------------
if __name__ == "__main__":
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                transactions.update(json.load(f))
            except:
                pass
    app.run(host="0.0.0.0", port=8080, debug=True)
