import requests, urllib.request, json
url = 'https://docs.google.com/forms/d/e/1FAIpQLSdYE0py_z9Dk0_1R0z3V28JuTjYxpUlLGo5Y7vVkDc2NyReTg/viewform?usp=embed_facebook'
html = urllib.request.urlopen(url).read().decode('utf-8')
res = requests.post('http://127.0.0.1:5000/api/analyze-form', json={'htmlSource': html}).json()
with open('config.json', 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
