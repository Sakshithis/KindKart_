from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from flask_login import current_user, login_required
from flask_socketio import join_room, leave_room, send, emit
from app import socketio
from models import db
from models.models import Request, Message, Notification

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

@chat_bp.route('/')
@login_required
def chat_list():
    # Only show chats for accepted requests involving the user
    donations = Request.query.filter(Request.status == 'accepted', Request.item.has(donor_id=current_user.id)).all()
    requests = Request.query.filter_by(requester_id=current_user.id, status='accepted').all()
    
    active_chats = donations + requests
    return render_template('dashboard/chat_list.html', active_chats=active_chats)

@chat_bp.route('/<int:request_id>')
@login_required
def room(request_id):
    req = Request.query.get_or_404(request_id)
    
    if req.status != 'accepted':
        flash('Chat is only available for accepted requests.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    if current_user.id not in [req.item.donor_id, req.requester_id]:
        flash('You are not authorized to view this chat.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    messages = Message.query.filter_by(request_id=req.id).order_by(Message.created_at.asc()).all()
    
    other_user = req.item.donor if current_user.id == req.requester_id else req.requester
    
    return render_template('dashboard/chat.html', req=req, messages=messages, other_user=other_user)

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    content = data['message']
    sender_id = data['sender_id']
    username = data['username']
    
    # Save to db
    msg = Message(request_id=room, sender_id=sender_id, content=content)
    db.session.add(msg)
    
    # Notify other user
    req = Request.query.get(room)
    if req:
        receiver_id = req.item.donor_id if sender_id == req.requester_id else req.requester_id
        notif = Notification(
            user_id=receiver_id,
            content=f"New message from {username}: {content[:30]}...",
            link=url_for('chat.room', request_id=room)
        )
        db.session.add(notif)
        
    db.session.commit()
    
    emit('message', {'msg': content, 'username': username, 'sender_id': sender_id}, room=room)
