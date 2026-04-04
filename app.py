from flask import Flask
from config import Config
from models import db
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

socketio = SocketIO()
bcrypt = Bcrypt()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)
    bcrypt.init_app(app)

    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()
    csrf.init_app(app)

    # Register Blueprints later
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.items import items_bp
    from routes.requests import requests_bp
    from routes.chat import chat_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(chat_bp)

    @app.context_processor
    def inject_notifications():
        from models.models import Notification
        from flask_login import current_user
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
            return {'unread_notifications': unread_count, 'recent_notifications': notifications}
        return {'unread_notifications': 0, 'recent_notifications': []}

    with app.app_context():
        # Create tables
        from models import models
        db.create_all()
        try:
            from sqlalchemy import text
            db.session.execute(text('ALTER TABLE message ADD COLUMN attachment_url VARCHAR(255)'))
            db.session.commit()
        except:
            db.session.rollback()

    return app
