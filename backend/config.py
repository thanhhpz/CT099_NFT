import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    SECRET_KEY = os.getenv('SECRET_KEY', 'nft-rental-secret-key-2024')
    DATABASE_NAME = 'nft_rental'
    
    # Platform Fee
    PLATFORM_FEE_PERCENT = 5  # 5% phí dịch vụ
    PLATFORM_WALLET = 'system_wallet_address'  # Ví nhận phí dịch vụ
    
        # Ethereum Sepolia
    SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL")

    NFT_CONTRACT_ADDRESS = os.getenv(
        "NFT_CONTRACT_ADDRESS"
    )
    