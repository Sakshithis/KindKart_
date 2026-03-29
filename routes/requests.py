from flask import Blueprint, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db
from models.models import Request, Item, Notification

requests_bp = Blueprint('requests', __name__, url_prefix='/requests')

@requests_bp.route('/create/<int:item_id>', methods=['POST'])
@login_required
def create_request(item_id):
    item = Item.query.get_or_404(item_id)
    
    if item.status != 'available':
        flash("This item is no longer available.", "warning")
        return redirect(url_for('items.detail', item_id=item.id))
        
    if item.donor_id == current_user.id:
        flash("You cannot request your own item.", "danger")
        return redirect(url_for('items.detail', item_id=item.id))
        
    # Check if already requested
    existing_req = Request.query.filter_by(item_id=item.id, requester_id=current_user.id).first()
    if existing_req:
        flash("You have already requested this item.", "info")
        return redirect(url_for('items.detail', item_id=item.id))
        
    new_req = Request(item_id=item.id, requester_id=current_user.id)
    db.session.add(new_req)
    
    # Notify donor
    notification = Notification(
        user_id=item.donor_id,
        content=f"{current_user.username} has requested your item: {item.title}.",
        link=url_for('main.dashboard')
    )
    db.session.add(notification)
    
    db.session.commit()
    flash("Request sent successfully! Wait for the donor to accept.", "success")
    return redirect(url_for('items.detail', item_id=item.id))

@requests_bp.route('/update/<int:request_id>', methods=['POST'])
@login_required
def update_request(request_id):
    req = Request.query.get_or_404(request_id)
    item = req.item
    
    if current_user.id != item.donor_id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('main.dashboard'))
        
    action = request.form.get('action') # 'accept' or 'reject'
    
    if action == 'accept':
        req.status = 'accepted'
        item.status = 'pending' # Item is now pending pickup
        
        # Reject all other requests for this item
        other_reqs = Request.query.filter(Request.item_id == item.id, Request.id != req.id).all()
        for orq in other_reqs:
            orq.status = 'rejected'
            notif = Notification(
                user_id=orq.requester_id,
                content=f"Your request for {item.title} has been declined.",
                link=url_for('items.detail', item_id=item.id)
            )
            db.session.add(notif)
            
        # Notify requester
        notif = Notification(
            user_id=req.requester_id,
            content=f"Your request for {item.title} has been APPROVED! You can now chat to arrange pickup.",
            link=url_for('chat.room', request_id=req.id)
        )
        db.session.add(notif)
        
        flash("Request accepted. You can now chat with the requester.", "success")
        
    elif action == 'reject':
        req.status = 'rejected'
        notif = Notification(
            user_id=req.requester_id,
            content=f"Your request for {item.title} was declined.",
            link=url_for('items.detail', item_id=item.id)
        )
        db.session.add(notif)
        flash("Request rejected.", "info")
        
    db.session.commit()
    return redirect(url_for('main.dashboard'))

@requests_bp.route('/complete/<int:request_id>', methods=['POST'])
@login_required
def complete_request(request_id):
    req = Request.query.get_or_404(request_id)
    item = req.item
    
    if current_user.id != item.donor_id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('main.dashboard'))
        
    if req.status == 'accepted':
        item.status = 'completed'
        current_user.people_helped_count += 1
        current_user.reputation_score += 20
        db.session.commit()
        flash("Donation complete! Thank you for sharing kindness.", "success")
        
    return redirect(url_for('main.dashboard'))
