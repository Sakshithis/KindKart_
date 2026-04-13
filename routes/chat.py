from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from flask_login import current_user, login_required
from flask_socketio import join_room, leave_room, send, emit
from app import socketio
from models import db
from models.models import Request, Message, Notification

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

@chat_bp.route('/send/<int:request_id>', methods=['POST'])
@login_required
def send_message(request_id):
    from flask import request as flask_request, jsonify
    req = Request.query.get_or_404(request_id)
    if current_user.id not in [req.item.donor_id, req.requester_id]:
        return jsonify({'error': 'Unauthorized'}), 403

    content = flask_request.form.get('message', '').strip()
    if not content:
        return jsonify({'error': 'Empty message'}), 400

    msg = Message(request_id=req.id, sender_id=current_user.id, content=content)
    db.session.add(msg)

    receiver_id = req.item.donor_id if current_user.id == req.requester_id else req.requester_id
    notif = Notification(
        user_id=receiver_id,
        content=f"New message from {current_user.username}: {content[:30]}...",
        link=f"/chat/{req.id}"
    )
    db.session.add(notif)
    db.session.commit()

    # Emit to room so the other user gets it in real-time
    from app import socketio as sio
    sio.emit('message', {
        'msg': content,
        'username': current_user.username,
        'sender_id': str(current_user.id),
        'attachment_url': None,
        'is_read': False
    }, room=str(req.id))

    return jsonify({'success': True, 'msg': content, 'username': current_user.username})

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
    
    # Mark messages from the OTHER user as read when we open the chat
    unread_msgs = Message.query.filter_by(request_id=req.id).filter(Message.sender_id != current_user.id).filter_by(is_read=False).all()
    if unread_msgs:
        for m in unread_msgs:
            m.is_read = True
        db.session.commit()
        # notify the other user that their messages were just read
        from app import socketio as sio
        sio.emit('messages_read', {'reader_id': current_user.id}, room=str(req.id))
    
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
    room = str(data['room'])
    content = data['message']
    sender_id = int(data['sender_id'])
    username = data['username']
    
    # Save to db
    msg = Message(request_id=int(room), sender_id=sender_id, content=content)
    db.session.add(msg)
    
    # Notify other user - build link manually (url_for not available in socket context)
    req = Request.query.get(int(room))
    if req:
        receiver_id = req.item.donor_id if sender_id == req.requester_id else req.requester_id
        chat_link = f"/chat/{room}"
        notif = Notification(
            user_id=receiver_id,
            content=f"New message from {username}: {content[:30]}...",
            link=chat_link
        )
        db.session.add(notif)
        db.session.commit()
        emit('new_notification', {'message': notif.content, 'link': notif.link}, room=f"user_{receiver_id}")
        
    db.session.commit()
    
    emit('message', {
        'msg': content, 
        'username': username, 
        'sender_id': str(sender_id),
        'attachment_url': None,
        'is_read': False
    }, room=room)

@socketio.on('mark_read')
def handle_mark_read(data):
    room = str(data['room'])
    reader_id = int(data['user_id'])
    
    unread = Message.query.filter_by(request_id=int(room)).filter(Message.sender_id != reader_id, Message.is_read == False).all()
    if unread:
        for m in unread:
            m.is_read = True
        db.session.commit()
        emit('messages_read', {'reader_id': reader_id}, room=room)

@chat_bp.route('/upload_attachment/<int:request_id>', methods=['POST'])
@login_required
def upload_attachment(request_id):
    from flask import request, current_app, jsonify
    from werkzeug.utils import secure_filename
    import os, uuid
    from PIL import Image
    req = Request.query.get_or_404(request_id)
    if current_user.id not in [req.item.donor_id, req.requester_id]:
        return jsonify({'error': 'Unauthorized'}), 403

    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'error': 'No file part'}), 400

    image_filename = None
    try:
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1]
        image_filename = f"chat_{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
        filepath = os.path.join(current_app.root_path, 'static/images/uploads', image_filename)
        img = Image.open(file)
        img.thumbnail((800, 800))
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.save(filepath, optimize=True, quality=85)
        
        msg = Message(request_id=req.id, sender_id=current_user.id, content="Sent an attachment", attachment_url=image_filename)
        db.session.add(msg)
        
        receiver_id = req.item.donor_id if current_user.id == req.requester_id else req.requester_id
        from flask import url_for
        notif = Notification(
            user_id=receiver_id,
            content=f"{current_user.username} sent an attachment.",
            link=url_for('chat.room', request_id=req.id)
        )
        db.session.add(notif)
        db.session.commit()

        # Emit to everyone in the room!
        from app import socketio as sio
        att_url = url_for('static', filename='images/uploads/' + image_filename)
        sio.emit('message', {
            'msg': msg.content,
            'username': current_user.username,
            'sender_id': current_user.id,
            'attachment_url': att_url,
            'is_read': False
        }, room=str(req.id))
        sio.emit('new_notification', {'message': notif.content, 'link': notif.link}, room=f"user_{receiver_id}")

        return jsonify({'success': True, 'msg': msg.content, 'attachment_url': att_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
