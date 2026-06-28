from flask import Blueprint, request, jsonify
from app.services.form_service import FormService
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.decorators import check_banned

forms_bp = Blueprint('forms', __name__)

@forms_bp.route('/analyze-form', methods=['OPTIONS', 'POST', 'GET'])
def analyze_form():
    if request.method == 'OPTIONS':
        return '', 200
    
    if request.method == 'GET':
        return jsonify({"message": "Analyze Form Endpoint"}), 200
    
    data = request.json
    html_source = data.get('htmlSource')
    form_url = data.get('formUrl')
    gemini_key = data.get('geminiKey')
    openai_key = data.get('openaiKey')
    hf_key = data.get('hfKey')

    result, status_code = FormService.analyze_form_url(html_source, form_url, gemini_key, openai_key, hf_key)
    return jsonify(result), status_code


@forms_bp.route('/fill-form', methods=['OPTIONS', 'POST', 'GET'])
@jwt_required(optional=True)
@check_banned()
def fill_form():
    if request.method == 'OPTIONS':
        return '', 200

    if request.method == 'GET':
        return jsonify({"message": "Fill Form Endpoint"}), 200

    user_id = get_jwt_identity()
    data = request.json
    
    form_url = data.get('formUrl')
    submit_url = data.get('submitUrl')
    emails = data.get('emails', [])
    form_config = data.get('formConfig', {})
    hidden_fields = data.get('hiddenFields', {})
    form_routing = data.get('formRouting', [])
    count = int(data.get('count', 1))
    
    try:
        max_delay = float(data.get('maxDelay', 4))
        if max_delay < 0:
            max_delay = 0
    except (TypeError, ValueError):
        max_delay = 4

    result, status_code = FormService.process_form_submission(
        user_id, form_url, submit_url, emails, form_config, 
        hidden_fields, form_routing, count, max_delay
    )
    return jsonify(result), status_code

