# app/models.py
from app import db
from datetime import datetime
from enum import Enum

class StatusTypes(Enum):
    PENDING = 'pending'
    VERIFIED = 'verified'
    REJECTED = 'rejected'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    auth0_id = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    order_number = db.Column(db.String(50), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ServerOnboarding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_number = db.Column(db.String(50), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    hoster = db.Column(db.String(100), nullable=False)
    custom_hoster = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum(StatusTypes), default=StatusTypes.PENDING)
    
    user = db.relationship('User', backref=db.backref('server_onboarding', uselist=False))