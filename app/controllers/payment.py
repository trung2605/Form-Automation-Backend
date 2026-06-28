from flask import Blueprint, request, jsonify
from app.services.payment_service import PaymentService
from flask_jwt_extended import jwt_required, get_jwt_identity

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/create-payment-link', methods=['POST'])
@jwt_required()
def create_payment_link():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    package_id = data.get('package_id')
    credits = data.get('credits', 0)
    
    result, status_code = PaymentService.create_payment_link(user_id, package_id, credits)
    return jsonify(result), status_code


@payment_bp.route('/payos-webhook', methods=['POST'])
def payos_webhook():
    webhook_data = request.get_json()
    result, status_code = PaymentService.process_webhook(webhook_data)
    return jsonify(result), status_code


@payment_bp.route('/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    user_id = get_jwt_identity()
    result, status_code = PaymentService.get_user_transactions(user_id)
    return jsonify(result), status_code

