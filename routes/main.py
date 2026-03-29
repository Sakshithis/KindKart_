from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models.models import Item, Request

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Fetch recent items for the landing page
    recent_items = Item.query.filter_by(status='available').order_by(Item.created_at.desc()).limit(3).all()
    # Stats for impact tracker
    items_donated = Item.query.count()
    return render_template('index.html', recent_items=recent_items, items_donated=items_donated)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    donations = current_user.donations.all()
    requests_sent = current_user.requests_sent.all()
    
    # Identify requests received (requests for items the current user donated)
    requests_received = []
    for item in donations:
        for req in item.requests:
            requests_received.append(req)
            
    return render_template('dashboard/index.html', 
                           donations=donations, 
                           requests_sent=requests_sent,
                           requests_received=requests_received)

@main_bp.route('/profile')
@login_required
def profile():
    return render_template('dashboard/profile.html', user=current_user)

@main_bp.route('/notification/<int:notif_id>')
@login_required
def read_notification(notif_id):
    from models import db
    from models.models import Notification
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()
        if notif.link:
            return redirect(notif.link)
    return redirect(url_for('main.dashboard'))
