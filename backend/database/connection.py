from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        try:
            self.client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'))
            self.client.admin.command('ping')
            self.db = self.client['nft_rental']
            self._create_collections()
            logger.info("✅ Kết nối MongoDB thành công!")
        except ConnectionFailure as e:
            logger.error(f"❌ Kết nối MongoDB thất bại: {e}")
            raise
    
    def _create_collections(self):
        collections = [
            'nguoidung',
            'game',
            'nhanvat',
            'danhmucvatpham',
            'vatpham',
            'nhanvat_vatpham',
            'hopdong',
            'giaodich',
            'nft',
            'vi'
        ]
        existing = self.db.list_collection_names()
        for coll in collections:
            if coll not in existing:
                self.db.create_collection(coll)
                logger.info(f"📁 Đã tạo collection: {coll}")

db_instance = Database()
db = db_instance.db

# Export collections
nguoidung_collection = db['nguoidung']
game_collection = db['game']
nhanvat_collection = db['nhanvat']
danhmucvatpham_collection = db['danhmucvatpham']
vatpham_collection = db['vatpham']
nhanvat_vatpham_collection = db['nhanvat_vatpham']
hopdong_collection = db['hopdong']
giaodich_collection = db['giaodich']
nft_collection = db['nft']
vi_collection = db['vi']