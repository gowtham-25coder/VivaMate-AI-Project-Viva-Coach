import os
from flask import Flask
from config import Config
from models import db
from routes.main import main_bp
from routes.practice import practice_bp
from routes.reports import reports_bp
from routes.progress import progress_bp
from routes.code_review import code_review_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure instance and uploads directories exist
    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(practice_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(code_review_bp)

    # Create Database Tables if they don't exist
    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    print("==================================================")
    print("  Starting VivaMate - AI Project Viva Coach")
    print("  Server running on http://127.0.0.1:5000")
    print("==================================================")
    app.run(host='127.0.0.1', port=5000, debug=True)
