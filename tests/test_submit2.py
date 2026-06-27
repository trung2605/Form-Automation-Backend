import requests, urllib.request, json
import sys
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://docs.google.com/forms/d/e/1FAIpQLSdYE0py_z9Dk0_1R0z3V28JuTjYxpUlLGo5Y7vVkDc2NyReTg/viewform?usp=embed_facebook'
html = urllib.request.urlopen(url).read().decode('utf-8')

res = requests.post('http://127.0.0.1:5000/api/analyze-form', json={'htmlSource': html}).json()
from app import GoogleFormFiller

formConfig = res['formConfig']
formConfig['entry.95443666']['weights'] = [1.0, 0.0]

submitter = GoogleFormFiller(url, res['submitUrl'], emails=[], hidden_fields=res['hiddenFields'])
response_data = submitter.generate_response_data(formConfig)

print('Submit result:', submitter.submit_form(response_data))
