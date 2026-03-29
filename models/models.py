from datetime import datetime
from flask_login import UserMixin
from . import db

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    location = db.Column(db.String(120))
    items_donated_count = db.Column(db.Integer, default=0)
    people_helped_count = db.Column(db.Integer, default=0)
    reputation_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    donations = db.relationship('Item', backref='donor', lazy='dynamic')
    requests_sent = db.relationship('Request', foreign_keys='Request.requester_id', backref='requester', lazy='dynamic')
    messages_sent = db.relationship('Message', backref='sender', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    wishlist = db.relationship('Wishlist', backref='user', lazy='dynamic')

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    category = db.Column(db.String(64), nullable=False) # clothes, books, electronics, furniture, others
    description = db.Column(db.Text, nullable=False)
    condition = db.Column(db.String(64), nullable=False)
    image_url = db.Column(db.String(256))
    pickup_location = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(64), default='available') # available, pending, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    requests = db.relationship('Request', backref='item', lazy='dynamic')

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(64), default='pending') # pending, accepted, rejected
    pickup_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    messages = db.relationship('Message', backref='request', lazy='dynamic')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'))
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(256), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    link = db.Column(db.String(256)) # to redirect to item or chat
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
