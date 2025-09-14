from flask import Flask, request, jsonify
import os, json, threading
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

sms_data_file = "sms_data.json"
sms_data_lock = threading.Lock()

def load_sms_data():
    try:
        with open(sms_data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
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
    if sender and sms_content:
        import re
        date_time = None
        detail = None
        balance = None
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
        else:
            sms_dict[tag].append({"sender": sender, "sms": sms_content})
        save_sms_data(sms_dict)
    sms_list = sms_dict.get(tag, [])
    status = "disconnected"
    now = datetime.now()
    for sms in sms_list[::-1]:
        dt_str = sms.get("date_time")
        try:
            if dt_str and "/" in dt_str and "@" in dt_str:
                day, rest = dt_str.split("/")
                month, timepart = rest.split("@")
                hour, minute = timepart.split(":")
                sms_dt = now.replace(day=int(day), month=int(month), hour=int(hour), minute=int(minute), second=0, microsecond=0)
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
