from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import random
import time
import json
from urllib.parse import urlencode
from gemini_parser import parse_form_config

app = Flask(__name__)
CORS(app)

class GoogleFormFiller:
    def __init__(self, form_url, submit_url, emails=None):
        self.form_url = form_url
        self.submit_url = submit_url
        self.session = requests.Session()
        self.emails = emails or []

    @staticmethod
    def weighted_choice(options, weights):
        return random.choices(options, weights=weights, k=1)[0]

    def get_random_email(self):
        if not self.emails:
            return "example@gmail.com"
        return random.choice(self.emails)

    def generate_response_data(self, form_config):
        response_data = {}
        for field_id, config in form_config.items():
            if config['type'] in ['choice', 'text', 'textarea']:
                response_data[field_id] = self.weighted_choice(config['options'], config['weights'])
            elif config['type'] == 'checkbox':
                max_sel = config.get('max_selections', 1)
                num_choices = random.randint(1, max_sel)
                selections = random.sample(config['options'], num_choices)
                for s in selections:
                    response_data.setdefault(field_id, [])
                    response_data[field_id].append(s)
            elif config['type'] == 'email':
                response_data[field_id] = self.get_random_email()
        return response_data

    def submit_form(self, response_data):
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        post_data = []
        for k, v in response_data.items():
            if isinstance(v, list):
                for item in v:
                    post_data.append((k, item))
            else:
                post_data.append((k, v))
        try:
            r = self.session.post(
                self.submit_url,
                data=urlencode(post_data),
                headers=headers,
                timeout=10
            )
            return r.status_code == 200
        except Exception as e:
            print(f"❌ Error submitting form: {e}")
            return False

@app.route('/api/analyze-form', methods=['OPTIONS', 'POST'])
def analyze_form():
    """
    API mới để phân tích mã nguồn HTML và trả về cấu hình JSON.
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.json
    html_source = data.get('htmlSource')
    if not html_source:
        return jsonify({"error": "Missing HTML source"}), 400

    parsed_data = parse_form_config(html_source)
    if parsed_data:
        return jsonify(parsed_data)
    else:
        return jsonify({"error": "Failed to parse form configuration using Gemini"}), 500

@app.route('/api/fill-form', methods=['OPTIONS', 'POST'])
def fill_form():
    """
    API cũ để điền form, sử dụng cấu hình JSON đã có.
    """
    if request.method == 'OPTIONS':
        return '', 200

    data = request.json
    form_url = data.get('formUrl')
    submit_url = data.get('submitUrl')
    emails = data.get('emails', [])
    form_config = data.get('formConfig', {})
    count = data.get('count', 1)

    if not form_url or not submit_url or not form_config:
        return jsonify({"error": "Missing required parameters"}), 400

    filler = GoogleFormFiller(form_url, submit_url, emails=emails)
    
    success_count = 0
    for i in range(count):
        response_data = filler.generate_response_data(form_config)
        if filler.submit_form(response_data):
            success_count += 1
        if i < count - 1:
            delay = random.uniform(2, 4)
            time.sleep(delay)

    return jsonify({
        "message": f"Completed! {success_count}/{count} forms submitted successfully.",
        "successes": success_count
    })

if __name__ == '__main__':
    app.run(port=5000)