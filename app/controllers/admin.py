from flask import Blueprint, request, jsonify
from app.services.admin_service import AdminService
from app.utils.decorators import admin_required
from flask_jwt_extended import get_jwt_identity

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users', methods=['GET'])
@admin_required()
def get_all_users():
    result, status_code = AdminService.get_all_users()
    return jsonify(result), status_code


@admin_bp.route('/users/<user_id>/add_credits', methods=['POST'])
@admin_required()
def add_credits(user_id):
    data = request.get_json()
    amount = data.get('amount', 0)
    admin_id = get_jwt_identity()
    
    result, status_code = AdminService.add_credits(user_id, amount, admin_id)
    return jsonify(result), status_code


@admin_bp.route('/users/<user_id>/deduct_credits', methods=['POST'])
@admin_required()
def deduct_credits(user_id):
    data = request.get_json()
    amount = data.get('amount', 0)
    admin_id = get_jwt_identity()
    
    result, status_code = AdminService.deduct_credits(user_id, amount, admin_id)
    return jsonify(result), status_code


@admin_bp.route('/users/<user_id>/toggle_ban', methods=['POST'])
@admin_required()
def toggle_ban(user_id):
    result, status_code = AdminService.toggle_ban(user_id)
    return jsonify(result), status_code


@admin_bp.route('/transactions', methods=['GET'])
@admin_required()
def get_all_transactions():
    result, status_code = AdminService.get_all_transactions()
    return jsonify(result), status_code


@admin_bp.route('/stats', methods=['GET'])
@admin_required()
def get_stats():
    result, status_code = AdminService.get_stats()
    return jsonify(result), status_code

