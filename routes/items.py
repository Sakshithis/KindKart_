import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import db
from models.models import Item, Request
import time

items_bp = Blueprint('items', __name__, url_prefix='/items')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@items_bp.route('/')
def browse():
    query = Item.query.filter_by(status='available')
    
    # Search
    search = request.args.get('search')
    if search:
        query = query.filter(Item.title.ilike(f'%{search}%') | Item.description.ilike(f'%{search}%'))
        
    # Filter by category
    category = request.args.get('category')
    if category:
        query = query.filter_by(category=category)
        
    # Sort
    sort = request.args.get('sort', 'newest')
    if sort == 'newest':
        query = query.order_by(Item.created_at.desc())
    elif sort == 'oldest':
        query = query.order_by(Item.created_at.asc())

    items = query.all()
    return render_template('items/browse.html', items=items, search=search, category=category, sort=sort)

@items_bp.route('/donate', methods=['GET', 'POST'])
@login_required
def donate():
    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        description = request.form.get('description')
        condition = request.form.get('condition')
        pickup_location = request.form.get('pickup_location', current_user.location)
        
        # Handle Image
        file = request.files.get('image')
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{int(time.time())}_{file.filename}")
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            # Ensure folder exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)

        item = Item(
            title=title,
            category=category,
            description=description,
            condition=condition,
            pickup_location=pickup_location,
            image_url=filename,
            donor_id=current_user.id
        )
        db.session.add(item)
        
        # Impact tracking
        current_user.items_donated_count += 1
        current_user.reputation_score += 10
        
        db.session.commit()
        flash('Item listed for donation successfully!', 'success')
        return redirect(url_for('items.detail', item_id=item.id))
        
    return render_template('items/donate.html')

@items_bp.route('/<int:item_id>')
def detail(item_id):
    item = Item.query.get_or_404(item_id)
    # Check if current user has already requested this item
    has_requested = False
    active_request = None
    if current_user.is_authenticated:
        active_request = Request.query.filter_by(item_id=item.id, requester_id=current_user.id).first()
        if active_request:
            has_requested = True
            
    return render_template('items/detail.html', item=item, has_requested=has_requested, request=active_request)
