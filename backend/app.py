from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from database.connection import db
import logging

# Import routes
from routes.auth_routes import auth_routes
from routes.wallet_routes import wallet_routes
from routes.nft_routes import nft_routes
from routes.rental_routes import rental_routes
from routes.game_routes import game_routes
from routes.character_routes import character_routes
from routes.item_routes import item_routes
from routes.admin_routes import admin_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Test database
try:
    db.command('ping')
    logger.info("✅ Kết nối database thành công")
except Exception as e:
    logger.error(f"❌ Kết nối database thất bại: {e}")

@app.route('/')
def home():
    return jsonify({
        'message': 'NFT Rental API',
        'version': '2.0.0',
        'status': 'running'
    })

@app.route('/api/health')
def health():
    try:
        db.command('ping')
        return jsonify({'status': 'ok', 'database': 'connected'})
    except:
        return jsonify({'status': 'error', 'database': 'disconnected'}), 500

# Register routes
auth_routes(app)
wallet_routes(app)
nft_routes(app)
rental_routes(app)
game_routes(app)
character_routes(app)
item_routes(app)
admin_routes(app)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)