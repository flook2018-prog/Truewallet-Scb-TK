from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.String, primary_key=True)
    event = db.Column(db.String)
    amount = db.Column(db.Integer)
    name = db.Column(db.String)
    bank = db.Column(db.String)
    status = db.Column(db.String, default="new")
    time = db.Column(db.String)           # เวลาเข้ารายการ
    time_str = db.Column(db.String)
    approved_time = db.Column(db.String, nullable=True)
    approved_time_str = db.Column(db.String, nullable=True)
    approver_name = db.Column(db.String, nullable=True)
    canceler_name = db.Column(db.String, nullable=True)
    cancelled_time = db.Column(db.String, nullable=True)
    cancelled_time_str = db.Column(db.String, nullable=True)
    customer_user = db.Column(db.String, nullable=True)
    slip_filename = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
