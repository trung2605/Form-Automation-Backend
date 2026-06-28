from flask import Blueprint, jsonify
from app.models.tool import Tool

tool_bp = Blueprint('tool', __name__)

@tool_bp.route('/', methods=['GET'])
def get_tools():
    try:
        tools = Tool.objects.all()
        return jsonify([tool.to_dict() for tool in tools]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
