from app import db
from datetime import datetime

class ServerOnboarding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)
    hoster = db.Column(db.String(100), nullable=False)
    custom_hoster = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.String(100), nullable=False)