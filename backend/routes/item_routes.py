from flask import request, jsonify
from models.vatpham_model import VatPham
from models.game_model import Game
from models.nhanvat_model import NhanVat
from models.nft_model import NFT

def item_routes(app):
    
    @app.route('/api/items', methods=['POST'])
    def create_item():
        data = request.get_json()
        required = ['ten_vat_pham', 'gia_thue', 'ma_game']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'message': f'Thiếu {field}'}), 400
        
        if not Game.find_by_ma(data['ma_game']):
            return jsonify({'success': False, 'message': 'Game không tồn tại'}), 404
        
        if data.get('duoc_dung_cho'):
            if not NhanVat.find_by_ma(data['duoc_dung_cho']):
                return jsonify({'success': False, 'message': 'Nhân vật không tồn tại'}), 404
        
        item = VatPham(
            data['ten_vat_pham'],  # 1. ten_vat_pham
            data.get('mo_ta', ''),  # 2. mo_ta
            data['gia_thue'],  # 3. gia_thue
            data.get('don_vi_thue', 'ngày'),  # 4. don_vi_thue
            data.get('thoi_gian_thue_toi_da', 30),  # 5. thoi_gian_thue_toi_da
            data.get('tien_dat_coc', data['gia_thue'] * 0.2),  # 6. tien_dat_coc
            data.get('do_hiem', 'thường'),  # 7. do_hiem
            data['ma_game'],  # 8. ma_game
            duoc_dung_cho=data.get('duoc_dung_cho'),
            ma_danh_muc=data.get('ma_danh_muc'),
            loai=data.get('loai', 'vật phẩm'),
        )
        item.save()
        
        return jsonify({'success': True, 'item': item.to_dict()}), 201
    
    @app.route('/api/items/available', methods=['GET'])
    def get_available_items():
        items = VatPham.find_available()
        return jsonify({'success': True, 'items': items}), 200
    
    @app.route('/api/items/<ma_vat_pham>', methods=['GET'])
    def get_item(ma_vat_pham):
        item = VatPham.find_by_ma(ma_vat_pham)
        if not item:
            return jsonify({'success': False, 'message': 'Vật phẩm không tồn tại'}), 404
        
        nfts = NFT.find_by_vat_pham(ma_vat_pham)
        item['has_nft'] = len(nfts) > 0
        if nfts:
            item['nft'] = nfts[0]
        
        return jsonify({'success': True, 'item': item}), 200