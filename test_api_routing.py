import requests, urllib.request, json

url = 'https://docs.google.com/forms/d/e/1FAIpQLSdYE0py_z9Dk0_1R0z3V28JuTjYxpUlLGo5Y7vVkDc2NyReTg/viewform?usp=embed_facebook'
html = urllib.request.urlopen(url).read().decode('utf-8')

print("Analyzing form...")
res = requests.post('http://127.0.0.1:5000/api/analyze-form', json={'htmlSource': html}).json()
print("Analyze complete. Submit URL:", res['submitUrl'])

formConfig = res['formConfig']
# Force branch "Không"
formConfig['entry.95443666']['weights'] = [0, 1]

print("Filling form via backend routing engine...")
fill_res = requests.post('http://127.0.0.1:5000/api/fill-form', json={
    'formUrl': url,
    'submitUrl': res['submitUrl'],
    'emails': ['test@gmail.com'],
    'count': 1,
    'maxDelay': 0,
    'formConfig': formConfig,
    'hiddenFields': res['hiddenFields'],
    'formRouting': res['formRouting']
})

print(fill_res.json())
