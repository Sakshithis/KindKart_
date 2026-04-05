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

@main_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    from flask import request, flash, redirect, url_for
    from models import db
    from models.models import User
    
    if request.method == 'POST':
        username = request.form.get('username')
        location = request.form.get('location')
        
        # Check username uniqueness
        existing = User.query.filter_by(username=username).first()
        if existing and existing.id != current_user.id:
            flash('Username is already taken by someone else.', 'danger')
            return redirect(url_for('main.edit_profile'))
            
        current_user.username = username
        current_user.location = location
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.profile'))
        
    return render_template('dashboard/edit_profile.html')

@main_bp.route('/user/<username>')
def user_profile(username):
    from models.models import User, Review
    user = User.query.filter_by(username=username).first_or_404()
    items = Item.query.filter_by(donor_id=user.id, status='available').order_by(Item.created_at.desc()).all()
    reviews = user.reviews_received.order_by(Review.created_at.desc()).all()
    avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else 0
    return render_template('dashboard/public_profile.html', user=user, items=items, reviews=reviews, avg_rating=round(avg_rating, 1))

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

@main_bp.route('/needs')
def needs_board():
    from models.models import Wishlist
    needs = Wishlist.query.order_by(Wishlist.created_at.desc()).all()
    return render_template('needs.html', needs=needs)

@main_bp.route('/needs/add', methods=['POST'])
@login_required
def add_need():
    from models import db
    from models.models import Wishlist
    from flask import request, flash
    description = request.form.get('description')
    if description and len(description.strip()) > 0:
        new_need = Wishlist(description=description.strip(), user_id=current_user.id)
        db.session.add(new_need)
        db.session.commit()
        from flask import flash
        flash('Your need has been posted to the board!', 'success')
    return redirect(url_for('main.needs_board'))

@main_bp.route('/needs/delete/<int:need_id>', methods=['POST'])
@login_required
def delete_need(need_id):
    from models import db
    from models.models import Wishlist
    need = Wishlist.query.get_or_404(need_id)
    if need.user_id == current_user.id:
        db.session.delete(need)
        db.session.commit()
        from flask import flash
        flash('Need deleted.', 'info')
    return redirect(url_for('main.needs_board'))

@main_bp.route('/needs/fulfill/<int:need_id>', methods=['GET', 'POST'])
@login_required
def fulfill_need(need_id):
    from flask import request, flash, current_app
    from models import db
    from models.models import Wishlist, Item, Request, Notification
    from werkzeug.utils import secure_filename
    import os, uuid
    from PIL import Image
    from app import socketio

    need = Wishlist.query.get_or_404(need_id)
    if need.user_id == current_user.id:
        flash("You cannot fulfill your own need.", "warning")
        return redirect(url_for('main.needs_board'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        condition = request.form.get('condition')
        file = request.files.get('image')

        image_filename = None
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1]
            image_filename = f"fulfill_{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
            filepath = os.path.join(current_app.root_path, 'static/images/uploads', image_filename)
            try:
                img = Image.open(file)
                img.thumbnail((800, 800))
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img.save(filepath, optimize=True, quality=85)
            except Exception as e:
                flash(f"Image error: {str(e)}", "danger")
                return redirect(request.url)

        # 1. Create dummy item bypassing exact browse rules
        new_item = Item(
            title=title, category="Others", description=description,
            condition=condition, pickup_location=current_user.location,
            image_url=image_filename, donor_id=current_user.id, status='pending'
        )
        db.session.add(new_item)
        db.session.flush()

        # 2. Auto-accept a request from the person who needed it
        new_request = Request(item_id=new_item.id, requester_id=need.user_id, status='accepted')
        db.session.add(new_request)
        db.session.flush()

        # 3. Inform them via real-time WebSockets
        notif = Notification(
            user_id=need.user_id,
            content=f"{current_user.username} is fulfilling your need! Check chat.",
            link=url_for('chat.room', request_id=new_request.id)
        )
        db.session.add(notif)
        
        # Add 20 Reputation Points for fulfilling a need
        current_user.reputation_score += 20
        current_user.items_donated_count += 1
        
        # 4. Remove from Needs Board
        db.session.delete(need)
        db.session.commit()

        socketio.emit('new_notification', {'message': notif.content, 'link': notif.link}, room=f"user_{need.user_id}")
        
        flash("Awesome! The item is requested. You've been automatically placed in a chat room.", "success")
        return redirect(url_for('chat.room', request_id=new_request.id))

    return render_template('needs_fulfill.html', need=need)

@main_bp.route('/review/<int:item_id>', methods=['GET', 'POST'])
@login_required
def leave_review(item_id):
    from models import db
    from models.models import Item, Request, Review
    from flask import request, flash
    item = Item.query.get_or_404(item_id)
    req = Request.query.filter_by(item_id=item.id, requester_id=current_user.id).first()
    
    if not req or item.status != 'completed':
        flash('You can only review items you successfully received.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    existing = Review.query.filter_by(item_id=item.id, reviewer_id=current_user.id).first()
    if existing:
        flash('You have already reviewed this donation.', 'info')
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '')
        if rating and 1 <= rating <= 5:
            review = Review(rating=rating, comment=comment[:500], reviewer_id=current_user.id, reviewed_id=item.donor_id, item_id=item.id)
            db.session.add(review)
            db.session.commit()
            flash('Thank you! Your trust review was submitted.', 'success')
            return redirect(url_for('main.dashboard'))
            
    return render_template('dashboard/review.html', item=item)

@main_bp.route('/leaderboard')
def leaderboard():
    from models.models import User
    top_users = User.query.order_by(User.reputation_score.desc()).limit(10).all()
    return render_template('dashboard/leaderboard.html', top_users=top_users)

@main_bp.route('/certificate')
@login_required
def certificate():
    from flask import flash, redirect, url_for
    from models.models import User
    top_user = User.query.order_by(User.reputation_score.desc()).first()
    if not top_user or current_user.id != top_user.id:
        flash('Certificates are only awarded to the #1 Philanthropist.', 'warning')
        return redirect(url_for('main.leaderboard'))
    return render_template('dashboard/certificate.html', user=top_user)
@main_bp.route('/analytics')
def analytics():
    from models.models import Item, User, Request
    clothes = Item.query.filter_by(category='Clothes').count()
    books = Item.query.filter_by(category='Books').count()
    electronics = Item.query.filter_by(category='Electronics').count()
    furniture = Item.query.filter_by(category='Furniture').count()
    others = Item.query.filter_by(category='Others').count()
    
    total_users = User.query.count()
    total_items = Item.query.count()
    total_requests = Request.query.count()
    completed_requests = Request.query.filter_by(status='accepted').count()
    
    return render_template('dashboard/analytics.html', 
        cat_data=[clothes, books, electronics, furniture, others],
        sys_data=[total_users, total_items, total_requests, completed_requests]
    )
