from flask import Blueprint, request, jsonify
import requests
import random
import time
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.services.ai_parser import parse_form_config
from app.services.form_filler import GoogleFormFiller
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
    
    if not html_source and not form_url:
        return jsonify({"error": "Missing HTML source or Form URL"}), 400

    if not html_source and form_url:
        try:
            view_url = form_url
            if 'formResponse' in view_url:
                view_url = view_url.replace('formResponse', 'viewform')
            
            r = requests.get(view_url, timeout=10)
            if r.status_code != 200:
                return jsonify({"error": f"Failed to fetch form URL. Status: {r.status_code}"}), 400
            html_source = r.text
        except Exception as e:
            return jsonify({"error": f"Error fetching form URL: {e}"}), 400

    gemini_key = data.get('geminiKey')
    openai_key = data.get('openaiKey')
    hf_key = data.get('hfKey')

    try:
        parsed_data = parse_form_config(html_source, gemini_key=gemini_key, openai_key=openai_key, hf_key=hf_key)
        return jsonify(parsed_data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to parse form: {e}"}), 500


@forms_bp.route('/fill-form', methods=['OPTIONS', 'POST', 'GET'])
@jwt_required(optional=True) # Making it optional for now, but you might want to enforce it
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

    if not form_url or not submit_url or not form_config:
        return jsonify({"error": "Missing required parameters"}), 400

    # 1. Check Balance if user is logged in
    wallet = None
    cost_per_submission = 1
    total_cost = count * cost_per_submission

    if user_id:
        wallet = Wallet.objects(user_id=user_id).first()
        if not wallet or wallet.balance < total_cost:
            return jsonify({"error": f"Số dư không đủ. Bạn cần {total_cost} credits để gửi {count} forms."}), 402
    else:
        return jsonify({"error": "Vui lòng đăng nhập để sử dụng tính năng này."}), 401

    # Sanitize submit_url
    if not submit_url.startswith('http'):
        if submit_url.startswith('/'):
            submit_url = f"https://docs.google.com{submit_url}"
        elif 'formResponse' in submit_url:
             if 'viewform' in form_url:
                 base_url = form_url.split('viewform')[0]
                 submit_url = base_url + submit_url
             else:
                 submit_url = form_url.replace(form_url.split('/')[-1], submit_url)
    
    if "/u/" in submit_url:
        import re
        submit_url = re.sub(r'/u/\d+', '', submit_url)

    if "docs.google.com/forms" in submit_url and not submit_url.endswith("formResponse"):
        if "?" in submit_url:
            submit_url = submit_url.split("?")[0]
        if not submit_url.endswith("formResponse"):
             submit_url = submit_url.rstrip('/') + "/formResponse"

    filler = GoogleFormFiller(form_url, submit_url, emails=emails, hidden_fields=hidden_fields, form_routing=form_routing, form_config=form_config)
    
    success_count = 0
    for i in range(count):
        response_data = filler.generate_response_data(form_config)
        if filler.submit_form(response_data):
            success_count += 1
        
        if i < count - 1:
            delay = random.uniform(0, max_delay)
            time.sleep(delay)

    # 2. Deduct from wallet if there were successes
    if success_count > 0 and wallet:
        cost = success_count * cost_per_submission
        wallet.balance -= cost
        tx = Transaction(
            user_id=user_id,
            amount=-cost,
            transaction_type='form_submission',
            description=f'Gửi {success_count} Google Forms'
        )
        tx.save()
        wallet.save()

    return jsonify({
        "message": f"Completed! {success_count}/{count} forms submitted successfully.",
        "successes": success_count,
        "remaining_balance": wallet.balance if wallet else 0
    }), 200
