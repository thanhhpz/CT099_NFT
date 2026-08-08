from flask import request, jsonify
from blockchain.ethereum_contract import get_ethereum_rental_contract


def blockchain_routes(app):

    @app.route("/api/blockchain/status", methods=["GET"])
    def blockchain_status():
        try:
            ethereum = get_ethereum_rental_contract()

            return jsonify({
                "success": True,
                "connected": ethereum.is_connected(),
                "chain_id": ethereum.get_chain_id(),
                "latest_block": ethereum.get_latest_block_number(),
                "rental_counter": ethereum.get_rental_counter()
            })

        except Exception as e:
            return jsonify({
                "success": False,
                "message": str(e)
            }), 500

    @app.route("/api/blockchain/rental/<int:rental_id>", methods=["GET"])
    def blockchain_get_rental(rental_id):
        try:
            ethereum = get_ethereum_rental_contract()

            rental = ethereum.get_rental(rental_id)

            rental["is_active"] = ethereum.is_rental_active(
                rental_id
            )

            rental["is_expired"] = ethereum.is_rental_expired(
                rental_id
            )

            return jsonify({
                "success": True,
                "rental": rental
            })

        except Exception as e:
            return jsonify({
                "success": False,
                "message": str(e)
            }), 500
            
    @app.route("/api/blockchain/verify-rental", methods=["POST"])
    def blockchain_verify_rental():
        try:
            data = request.get_json(silent=True) or {}

            tx_hash = data.get("transaction_hash")

            if not tx_hash:
                return jsonify({
                    "success": False,
                    "message": "Thiếu transaction_hash"
                }), 400

            ethereum = get_ethereum_rental_contract()

            verified = ethereum.verify_rental_transaction(
                tx_hash
            )

            return jsonify({
                "success": True,
                "message": "Xác minh giao dịch blockchain thành công",
                "blockchain": verified
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "message": str(e)
            }), 400