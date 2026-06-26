import requests
import json
import urllib.request
import re

url = "https://docs.google.com/forms/d/e/1FAIpQLSdYE0py_z9Dk0_1R0z3V28JuTjYxpUlLGo5Y7vVkDc2NyReTg/viewform?usp=embed_facebook"
html = urllib.request.urlopen(url).read().decode('utf-8')

res = requests.post("http://127.0.0.1:5000/api/analyze-form", json={"htmlSource": html})
data = res.json()

formConfig = data['formConfig']

# Force 'Có'
formConfig['entry.95443666']['weights'] = [1.0, 0.0]

print("Page history from backend:", data.get('hiddenFields', {}).get('pageHistory'))

# Try to fill
fill_res = requests.post("http://127.0.0.1:5000/api/fill-form", json={
    "formUrl": url,
    "submitUrl": data['submitUrl'],
    "formConfig": formConfig,
    "hiddenFields": data['hiddenFields'],
    "emails": ["test@gmail.com"],
    "count": 1,
})

print("Fill result:", fill_res.json())
