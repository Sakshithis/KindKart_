import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import db
from models.models import Item, Request
import time
from datetime import datetime, timedelta

items_bp = Blueprint('items', __name__, url_prefix='/items')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@items_bp.route('/')
def browse():
    query = Item.query.filter_by(status='available')
    
    # Hide expired items
    query = query.filter((Item.expires_at == None) | (Item.expires_at > datetime.utcnow()))
    
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

    lat_str = request.args.get('lat')
    lng_str = request.args.get('lng')

    # Near Me Filter
    near_me = request.args.get('near_me')
    if near_me == 'true' and lat_str and lng_str:
        try:
            user_lat = float(lat_str)
            user_lng = float(lng_str)
            active_items = query.all()
            filtered_items = []
            
            import math
            def haversine(lat1, lon1, lat2, lon2):
                R = 6371  # Earth radius in km
                dlat = math.radians(lat2 - lat1)
                dlon = math.radians(lon2 - lon1)
                a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                return R * c

            for i in active_items:
                if i.lat is not None and i.lng is not None:
                    dist = haversine(user_lat, user_lng, i.lat, i.lng)
                    if dist <= 20: # 20km radius limit
                        filtered_items.append(i)
            
            page = request.args.get('page', 1, type=int)
            per_page = 12
            total = len(filtered_items)
            
            class DummyPagination:
                def __init__(self):
                    self.items = filtered_items[(page-1)*per_page : page*per_page]
                    self.page = page
                    self.pages = max(1, (total + per_page - 1) // per_page)
                    self.has_prev = page > 1
                    self.has_next = page < self.pages
                    self.prev_num = page - 1
                    self.next_num = page + 1
            
            pagination = DummyPagination()
            items = pagination.items
        except ValueError:
            page = request.args.get('page', 1, type=int)
            pagination = query.paginate(page=page, per_page=12, error_out=False)
            items = pagination.items

    elif near_me == 'true' and current_user.is_authenticated and current_user.location:
        from sqlalchemy import or_
        loc = current_user.location.strip()
        # Fallback string logic if browser location disabled
        parts = [p.strip() for p in loc.replace('-', ' ').split(',')]
        filters = [Item.pickup_location.ilike(f'%{p}%') for p in parts if len(p) > 2]
        if not filters and parts:
            filters = [Item.pickup_location.ilike(f'%{parts[0]}%')]
            
        if filters:
            query = query.filter(or_(*filters))
            
        page = request.args.get('page', 1, type=int)
        pagination = query.paginate(page=page, per_page=12, error_out=False)
        items = pagination.items
    else:
        page = request.args.get('page', 1, type=int)
        pagination = query.paginate(page=page, per_page=12, error_out=False)
        items = pagination.items
    
    return render_template('items/browse.html', items=items, pagination=pagination, search=search, category=category, sort=sort, near_me=near_me, backend_items=query.all(), utcnow=datetime.utcnow(), timedelta=timedelta)

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
            
            # Use Pillow to compress and resize image
            from PIL import Image
            img = Image.open(file)
            
            # Convert to RGB if it's RGBA (e.g. from PNG) before saving as JPEG
            if img.mode == 'RGBA':
                img = img.convert('RGB')
                
            # Resize keeping aspect ratio
            max_size = (800, 800)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized
            img.save(filepath, optimize=True, quality=85)

        expires_in_days_input = request.form.get('expires_in_days')
        expires_at = None
        if expires_in_days_input and expires_in_days_input.isdigit():
            expires_at = datetime.utcnow() + timedelta(days=int(expires_in_days_input))

        lat_str = request.form.get('lat')
        lng_str = request.form.get('lng')
        lat = float(lat_str) if lat_str and lat_str.strip() else None
        lng = float(lng_str) if lng_str and lng_str.strip() else None

        item = Item(
            title=title,
            category=category,
            description=description,
            condition=condition,
            pickup_location=pickup_location,
            image_url=filename,
            expires_at=expires_at,
            lat=lat,
            lng=lng,
            donor_id=current_user.id
        )
        db.session.add(item)
        
        # Impact tracking
        current_user.items_donated_count += 1
        current_user.reputation_score += 10
        
        db.session.commit()
        flash(f'Item listed successfully! Debug -> Form Lat: "{lat_str}", Lng: "{lng_str}"', 'success')
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
