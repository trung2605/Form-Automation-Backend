import requests
import random

class GoogleFormFiller:
    def __init__(self, form_url, submit_url, emails=None, hidden_fields=None, form_routing=None, form_config=None):
        self.form_url = form_url
        self.submit_url = submit_url
        self.emails = emails or []
        self.hidden_fields = hidden_fields or {}
        self.form_routing = form_routing or []
        self.form_config = form_config or {}
        self.session = requests.Session()

    @staticmethod
    def weighted_choice(options, weights):
        if not options or not weights:
            return None
        if len(options) != len(weights):
            min_len = min(len(options), len(weights))
            options = options[:min_len]
            weights = weights[:min_len]
        try:
            return random.choices(options, weights=weights, k=1)[0]
        except (IndexError, ValueError):
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
                import datetime
                response_data[field_id] = datetime.date.today().strftime("%Y-%m-%d")
        return response_data

    def submit_form(self, response_data):
        if not self.session.cookies:
            try:
                view_url = self.form_url
                if 'formResponse' in view_url:
                     view_url = view_url.replace('formResponse', 'viewform')
                print(f"🔄 Visiting form page to establish session: {view_url}")
                self.session.get(view_url, timeout=10)
            except Exception as e:
                print(f"⚠️ Failed to visit form page: {e}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': self.form_url
        }
        post_data = []
        
        # 1. Routing Simulation & Data Sanitization
        if self.form_routing and self.form_config:
            visited_pages = [0]
            current_page_idx = 0
            
            while current_page_idx < len(self.form_routing):
                page_data = self.form_routing[current_page_idx]
                next_target = None
                
                for entry_key in page_data.get('entries', []):
                    if entry_key in response_data and entry_key in self.form_config:
                        cfg = self.form_config[entry_key]
                        ans = response_data[entry_key]
                        targets = cfg.get('optionTargets', {})
                        if ans in targets:
                            target = targets[ans]
                            if target == '-2':
                                next_target = None 
                                break
                            elif target == '0' or target == '-1':
                                next_target = -1
                                break
                            else:
                                next_target = target
                                break
                                
                if next_target == -1:
                    break
                elif next_target is not None:
                    target_idx = None
                    for i, p in enumerate(self.form_routing):
                        if p.get('page_id') == next_target:
                            target_idx = i
                            break
                    if target_idx is not None:
                        current_page_idx = target_idx
                        if current_page_idx not in visited_pages:
                            visited_pages.append(current_page_idx)
                    else:
                        current_page_idx += 1
                        if current_page_idx < len(self.form_routing):
                            visited_pages.append(current_page_idx)
                else:
                    current_page_idx += 1
                    if current_page_idx < len(self.form_routing):
                        visited_pages.append(current_page_idx)
            
            valid_entries = set()
            for idx in visited_pages:
                if idx < len(self.form_routing):
                    valid_entries.update(self.form_routing[idx].get('entries', []))
                    
            response_data = {k: v for k, v in response_data.items() if k in valid_entries or not str(k).startswith("entry.")}
            
            self.hidden_fields['pageHistory'] = ",".join(str(x) for x in visited_pages)
        
        if 'pageHistory' not in self.hidden_fields:
            post_data.append(('pageHistory', '0'))
        if 'fvv' not in self.hidden_fields:
            post_data.append(('fvv', '1'))
        if 'draftResponse' not in self.hidden_fields:
            fbzx_val = self.hidden_fields.get('fbzx', '')
            post_data.append(('draftResponse', f'[null,null,"{fbzx_val}"]'))
            
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
