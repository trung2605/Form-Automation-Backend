from flask import Blueprint, request, jsonify
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from flask_jwt_extended import jwt_required, get_jwt_identity

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/deposit', methods=['POST'])
@jwt_required()
def deposit():
    """
    Fake deposit endpoint for testing. 
    In production, this would integrate with Stripe, VNPay, PayPal, etc.
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    amount = data.get('amount', 0)
    
    if amount <= 0:
        return jsonify({"error": "Số lượng nạp không hợp lệ"}), 400

    wallet = Wallet.objects(user_id=user_id).first()
    if not wallet:
        return jsonify({"error": "Ví không tồn tại"}), 404

    # Add transaction
    tx = Transaction(
        user_id=user_id,
        amount=amount,
        transaction_type='deposit',
        description=f'Nạp mô phỏng {amount} credits'
    )
    tx.save()
    
    # Update balance
    wallet.balance += amount
    wallet.save()

    return jsonify({
        "message": f"Đã nạp thành công {amount} credits vào ví",
        "new_balance": wallet.balance
    }), 200

@payment_bp.route('/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    user_id = get_jwt_identity()
    txs = Transaction.objects(user_id=user_id).order_by('-created_at').limit(50)
    
    result = []
    for tx in txs:
        result.append({
            "id": str(tx.id),
            "amount": tx.amount,
            "type": tx.transaction_type,
            "status": tx.status,
            "description": tx.description,
            "created_at": tx.created_at.isoformat()
        })
        
    return jsonify(result), 200
