from flask import Blueprint, request, jsonify
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.utils.decorators import admin_required
from flask_jwt_extended import get_jwt_identity

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users', methods=['GET'])
@admin_required()
def get_all_users():
    users = User.objects().all()
    user_list = []
    for u in users:
        wallet = u.wallet
        user_list.append({
            "id": str(u.id),
            "email": u.email,
            "role": u.role,
            "is_banned": u.is_banned,
            "created_at": u.created_at.isoformat(),
            "wallet_balance": wallet.balance if wallet else 0
        })
    return jsonify(user_list), 200


@admin_bp.route('/users/<user_id>/add_credits', methods=['POST'])
@admin_required()
def add_credits(user_id):
    data = request.get_json()
    amount = data.get('amount', 0)
    
    if amount <= 0:
        return jsonify({"error": "Số tiền cộng phải lớn hơn 0"}), 400

    user = User.objects(id=user_id).first()
    if not user:
        return jsonify({"error": "Người dùng không tồn tại"}), 404

    wallet = user.wallet
    if not wallet:
        return jsonify({"error": "Người dùng này chưa có ví"}), 400

    # Create transaction
    admin_id = get_jwt_identity()
    tx = Transaction(
        user_id=user_id,
        amount=amount,
        transaction_type='admin_bonus',
        description=f'Admin {admin_id} cộng {amount} credits thủ công'
    )
    tx.save()

    # Update balance
    wallet.balance += amount
    wallet.save()

    return jsonify({
        "message": f"Đã cộng {amount} credits cho user {user.email}",
        "new_balance": wallet.balance
    }), 200


@admin_bp.route('/users/<user_id>/deduct_credits', methods=['POST'])
@admin_required()
def deduct_credits(user_id):
    data = request.get_json()
    amount = data.get('amount', 0)
    
    if amount <= 0:
        return jsonify({"error": "Số tiền trừ phải lớn hơn 0"}), 400

    user = User.objects(id=user_id).first()
    if not user:
        return jsonify({"error": "Người dùng không tồn tại"}), 404

    wallet = user.wallet
    if not wallet:
        return jsonify({"error": "Người dùng này chưa có ví"}), 400

    if wallet.balance < amount:
        return jsonify({"error": f"Số dư của user chỉ còn {wallet.balance}, không đủ để trừ {amount}"}), 400

    admin_id = get_jwt_identity()
    tx = Transaction(
        user_id=user_id,
        amount=-amount,
        transaction_type='admin_penalty',
        description=f'Admin {admin_id} trừ {amount} credits thủ công'
    )
    tx.save()

    wallet.balance -= amount
    wallet.save()

    return jsonify({
        "message": f"Đã trừ {amount} credits của user {user.email}",
        "new_balance": wallet.balance
    }), 200


@admin_bp.route('/users/<user_id>/toggle_ban', methods=['POST'])
@admin_required()
def toggle_ban(user_id):
    user = User.objects(id=user_id).first()
    if not user:
        return jsonify({"error": "Người dùng không tồn tại"}), 404
    
    if user.role == 'admin':
        return jsonify({"error": "Không thể khóa tài khoản Admin"}), 400

    user.is_banned = not user.is_banned
    user.save()

    status = "Đã khóa" if user.is_banned else "Đã mở khóa"
    return jsonify({"message": f"{status} tài khoản {user.email}"}), 200


@admin_bp.route('/transactions', methods=['GET'])
@admin_required()
def get_all_transactions():
    txs = Transaction.objects().order_by('-created_at').limit(100)
    result = []
    for tx in txs:
        result.append({
            "id": str(tx.id),
            "user_id": tx.user_id,
            "amount": tx.amount,
            "type": tx.transaction_type,
            "status": tx.status,
            "description": tx.description,
            "created_at": tx.created_at.isoformat()
        })
    return jsonify(result), 200


@admin_bp.route('/stats', methods=['GET'])
@admin_required()
def get_stats():
    total_users = User.objects().count()
    
    # Calculate total forms submitted (count transactions of type form_submission)
    form_txs = Transaction.objects(transaction_type='form_submission')
    total_forms_submitted = abs(sum(tx.amount for tx in form_txs)) # Since each form costs 1 credit, total amount = total forms
    
    total_revenue = sum(tx.amount for tx in Transaction.objects(transaction_type='deposit'))

    return jsonify({
        "total_users": total_users,
        "total_forms_submitted": total_forms_submitted,
        "total_revenue_credits": total_revenue
    }), 200
