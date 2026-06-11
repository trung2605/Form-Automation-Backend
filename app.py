from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import random
import time
import json
from urllib.parse import urlencode
import os
from ai_parser import parse_form_config

app = Flask(__name__)
CORS(app, origins=["https://form-automation-frontend.vercel.app", "http://localhost:3000"])

class GoogleFormFiller:
    def __init__(self, form_url, submit_url, emails=None, hidden_fields=None):
        self.form_url = form_url
        self.submit_url = submit_url
        self.session = requests.Session()
        self.emails = emails or []
        self.hidden_fields = hidden_fields or {}

    @staticmethod
    def weighted_choice(options, weights):
        """
        Chọn ngẫu nhiên có trọng số, với cơ chế an toàn.
        """
        # 1. Kiểm tra danh sách rỗng
        if not options or not weights:
            return None

        # 2. Kiểm tra độ dài chênh lệch (để tránh lỗi logic)
        if len(options) != len(weights):
            # Nếu không khớp, ta lấy độ dài nhỏ nhất để tránh lỗi index
            min_len = min(len(options), len(weights))
            options = options[:min_len]
            weights = weights[:min_len]

        try:
            return random.choices(options, weights=weights, k=1)[0]
        except (IndexError, ValueError):
            # Fallback: nếu lỗi, chọn ngẫu nhiên đều (hoặc trả về None)
            return random.choice(options) if options else None

    def get_random_email(self):
        if not self.emails:
            return "example@gmail.com"
        return random.choice(self.emails)

    def generate_response_data(self, form_config):
        response_data = {}
        for field_id, config in form_config.items():
            if config['type'] in ['choice', 'text', 'textarea']:
                response_data[field_id] = self.weighted_choice(config.get('options', []), config.get('weights', []))
            elif config['type'] == 'checkbox':
                max_sel = config.get('max_selections', 1)
                num_choices = random.randint(1, max_sel)
                # Check safe sample size
                options = config.get('options', [])
                if not options:
                    continue
                k = min(len(options), num_choices)
                selections = random.sample(options, k)
                for s in selections:
                    response_data.setdefault(field_id, [])
                    response_data[field_id].append(s)
            elif config['type'] == 'email':
                response_data[field_id] = self.get_random_email()
            elif config['type'] == 'date':
                # Simple random date for now or current date
                import datetime
                response_data[field_id] = datetime.date.today().strftime("%Y-%m-%d")
            
        return response_data

    def submit_form(self, response_data):
        # Warm up session context if not already done (get cookies)
        if not self.session.cookies:
            try:
                # We need to visit the VIEW form URL (ending in viewform), not the submit return URL
                view_url = self.form_url
                if 'formResponse' in view_url:
                     view_url = view_url.replace('formResponse', 'viewform')
                
                print(f"🔄 Visiting form page to establish session: {view_url}")
                self.session.get(view_url, timeout=10)
            except Exception as e:
                print(f"⚠️ Failed to visit form page: {e}")

        print(f"📦 Hidden fields received: {self.hidden_fields}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': self.form_url # This must match the actual viewform URL
        }
        post_data = []
        
        # Add required hidden fields for typical Google Forms
        # Use defaults if not provided in hidden_fields
        if 'pageHistory' not in self.hidden_fields:
            post_data.append(('pageHistory', '0'))
        if 'fvv' not in self.hidden_fields:
            post_data.append(('fvv', '1'))
        if 'draftResponse' not in self.hidden_fields:
            post_data.append(('draftResponse', '[]'))
            
        # Add dynamic hidden fields extracted by Gemini (e.g., fbzx)
        for k, v in self.hidden_fields.items():
            if v:
                post_data.append((k, v))
        
        OTHER_SENTINEL = '__other_option__'
        for k, v in response_data.items():
            if v is None:
                continue
            if isinstance(v, list):
                for item in v:
                    if item in ('Khác', 'Other', 'other'):
                        post_data.append((k, OTHER_SENTINEL))
                        post_data.append((f'{k}.other_option_response', item))
                    else:
                        post_data.append((k, item))
            else:
                if v in ('Khác', 'Other', 'other'):
                    post_data.append((k, OTHER_SENTINEL))
                    post_data.append((f'{k}.other_option_response', v))
                else:
                    post_data.append((k, v))
        try:
            print(f"🚀 Submitting to URL: {self.submit_url}")
            print(f"📋 Post data: {post_data}")
            r = self.session.post(
                self.submit_url,
                data=urlencode(post_data),
                headers=headers,
                timeout=10
            )
            if r.status_code != 200:
                print(f"⚠️ Submission returned status {r.status_code}")
                print(f"Server response headers: {r.headers}")
                # Print first 500 chars of response to debug
                print(f"Server response: {r.text[:500]}")
            return r.status_code == 200
        except Exception as e:
            print(f"❌ Error submitting form: {e}")
            return False

@app.route('/api/analyze-form', methods=['OPTIONS', 'POST', 'GET'])
def analyze_form():
    """
    API mới để phân tích mã nguồn HTML và trả về cấu hình JSON.
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    if request.method == 'GET':
        return jsonify({
            "message": "This is the analyze-form API endpoint. Please send a POST request with 'htmlSource' to use it.",
            "status": "active"
        })
    
    data = request.json
    html_source = data.get('htmlSource')
    if not html_source:
        return jsonify({"error": "Missing HTML source"}), 400

    gemini_key = data.get('geminiKey') or None
    openai_key = data.get('openaiKey') or None
    hf_key     = data.get('hfKey')     or None

    try:
        parsed_data = parse_form_config(html_source, gemini_key=gemini_key, openai_key=openai_key, hf_key=hf_key)
        return jsonify(parsed_data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to parse form: {e}"}), 500

@app.route('/api/fill-form', methods=['OPTIONS', 'POST', 'GET'])
def fill_form():
    """
    API cũ để điền form, sử dụng cấu hình JSON đã có.
    """
    if request.method == 'OPTIONS':
        return '', 200

    if request.method == 'GET':
        return jsonify({
            "message": "This is the fill-form API endpoint. Please send a POST request with form details to use it.",
            "status": "active"
        })

    data = request.json
    form_url = data.get('formUrl')
    submit_url = data.get('submitUrl')
    emails = data.get('emails', [])
    form_config = data.get('formConfig', {})
    hidden_fields = data.get('hiddenFields', {})
    count = data.get('count', 1)
    # maxDelay is the maximum random delay in seconds between submissions
    # If not provided, default to 4 seconds
    try:
        max_delay = float(data.get('maxDelay', 4))
        if max_delay < 0:
            max_delay = 0
    except (TypeError, ValueError):
        max_delay = 4

    if not form_url or not submit_url or not form_config:
        return jsonify({"error": "Missing required parameters"}), 400

    # Sanitize submit_url
    if not submit_url.startswith('http'):
        if submit_url.startswith('/'):
            submit_url = f"https://docs.google.com{submit_url}"
        elif 'formResponse' in submit_url:
            # Handle relative paths like 'formResponse'
             if 'viewform' in form_url:
                 base_url = form_url.split('viewform')[0]
                 submit_url = base_url + submit_url
             else:
                 # Fallback
                 submit_url = form_url.replace(form_url.split('/')[-1], submit_url)
    
    # Remove user session specific index like /u/0/ which might break unauth requests
    if "/u/" in submit_url:
        import re
        submit_url = re.sub(r'/u/\d+', '', submit_url)

    # Ensure it ends with formResponse if it's a standard google form
    if "docs.google.com/forms" in submit_url and not submit_url.endswith("formResponse"):
        # Removing any query params first
        if "?" in submit_url:
            submit_url = submit_url.split("?")[0]
        if not submit_url.endswith("formResponse"):
             submit_url = submit_url.rstrip('/') + "/formResponse"

    filler = GoogleFormFiller(form_url, submit_url, emails=emails, hidden_fields=hidden_fields)
    
    success_count = 0
    for i in range(count):
        response_data = filler.generate_response_data(form_config)
        if filler.submit_form(response_data):
            success_count += 1
        # Between submissions, wait for a random duration up to max_delay seconds
        if i < count - 1:
            delay = random.uniform(0, max_delay)
            time.sleep(delay)

    return jsonify({
        "message": f"Completed! {success_count}/{count} forms submitted successfully.",
        "successes": success_count
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)