import requests, urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')
from app import GoogleFormFiller

url = 'https://docs.google.com/forms/d/e/1FAIpQLSdYE0py_z9Dk0_1R0z3V28JuTjYxpUlLGo5Y7vVkDc2NyReTg/viewform?usp=embed_facebook'
html = urllib.request.urlopen(url).read().decode('utf-8')

res = requests.post('http://127.0.0.1:5000/api/analyze-form', json={'htmlSource': html}).json()

formConfig = res['formConfig']
# Force branch "Không"
formConfig['entry.95443666']['weights'] = [0, 1]

filler = GoogleFormFiller(
    form_url=url, 
    submit_url=res['submitUrl'], 
    emails=['test@gmail.com'], 
    hidden_fields=res['hiddenFields'], 
    form_routing=res['formRouting'], 
    form_config=formConfig
)

response_data = filler.generate_response_data(formConfig)
success = filler.submit_form(response_data)
print("Success?", success)
