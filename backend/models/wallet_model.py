import datetime

from blockchain.wallet import create_wallet as create_blockchain_wallet
from database.connection import (
    nguoidung_collection,
    vi_collection
)


class Wallet:
    def __init__(
        self,
        dia_chi,
        ten_nguoi_dung,
        so_du=0,
        private_key='',
        public_key=''
    ):
        self.dia_chi = dia_chi
        self.ten_nguoi_dung = ten_nguoi_dung
        self.so_du = so_du
        self.private_key = private_key
        self.public_key = public_key
        self.created_at = datetime.datetime.now(
            datetime.timezone.utc
        )

    def to_dict(self, include_private_key=False):
        """
        Dữ liệu an toàn để trả về API.
        Mặc định không trả private key.
        """
        data = {
            'dia_chi': self.dia_chi,
            'ten_nguoi_dung': self.ten_nguoi_dung,
            'so_du': self.so_du,
            'public_key': self.public_key,
            'created_at': self.created_at
        }

        if include_private_key:
            data['private_key'] = self.private_key

        return data

    def to_database_dict(self):
        """
        Dữ liệu đầy đủ để lưu trong MongoDB.
        """
        return {
            'dia_chi': self.dia_chi,
            'ten_nguoi_dung': self.ten_nguoi_dung,
            'so_du': self.so_du,
            'private_key': self.private_key,
            'public_key': self.public_key,
            'created_at': self.created_at
        }

    def save(self):
        vi_collection.insert_one(
            self.to_database_dict()
        )
        return self

    @staticmethod
    def create_wallet(
        ten_nguoi_dung,
        ma_nguoi_dung=None,
        initial_balance=0
    ):
        """
        Tạo ví blockchain và liên kết ví với người dùng.
        """

        if not ten_nguoi_dung:
            raise ValueError(
                'Tên người dùng không được để trống khi tạo ví'
            )

        # Không tạo ví thứ hai nếu người dùng đã có ví.
        existing_wallet = Wallet.find_by_username(
            ten_nguoi_dung
        )

        if existing_wallet:
            return existing_wallet

        # Gọi hàm tạo khóa trong backend/blockchain/wallet.py.
        key_data = create_blockchain_wallet()

        required_keys = [
            'address',
            'private_key',
            'public_key'
        ]

        for key in required_keys:
            if not key_data.get(key):
                raise ValueError(
                    f'Dữ liệu tạo ví thiếu trường {key}'
                )

        wallet = Wallet(
            dia_chi=key_data['address'],
            ten_nguoi_dung=ten_nguoi_dung,
            so_du=initial_balance,
            private_key=key_data['private_key'],
            public_key=key_data['public_key']
        )

        wallet.save()

        # Ưu tiên cập nhật bằng mã người dùng.
        if ma_nguoi_dung:
            user_filter = {
                'ma_nguoi_dung': ma_nguoi_dung
            }
        else:
            user_filter = {
                'ten_nguoi_dung': ten_nguoi_dung
            }

        update_result = nguoidung_collection.update_one(
            user_filter,
            {
                '$set': {
                    'dia_chi_vi': wallet.dia_chi
                }
            }
        )

        if update_result.matched_count == 0:
            # Nếu không cập nhật được user thì xóa ví vừa tạo,
            # tránh sinh document ví bị mồ côi.
            vi_collection.delete_one({
                'dia_chi': wallet.dia_chi
            })

            raise ValueError(
                'Không tìm thấy người dùng để liên kết ví'
            )

        return wallet.to_database_dict()

    @staticmethod
    def find_by_address(dia_chi):
        return vi_collection.find_one(
            {
                'dia_chi': dia_chi
            },
            {
                '_id': 0
            }
        )

    @staticmethod
    def find_by_username(ten_nguoi_dung):
        return vi_collection.find_one(
            {
                'ten_nguoi_dung': ten_nguoi_dung
            },
            {
                '_id': 0
            }
        )

    @staticmethod
    def update_balance(dia_chi, new_balance):
        return vi_collection.update_one(
            {
                'dia_chi': dia_chi
            },
            {
                '$set': {
                    'so_du': new_balance
                }
            }
        )