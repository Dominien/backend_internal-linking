from flask import Flask

def create_app():
    app = Flask(__name__)

    # Import and register the blueprint from keyword_list.py
    from .keyword_list import bp as keyword_list_bp
    app.register_blueprint(keyword_list_bp)

    return app
