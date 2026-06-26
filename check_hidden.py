import urllib.request, re
url = 'https://docs.google.com/forms/d/e/1FAIpQLSdYE0py_z9Dk0_1R0z3V28JuTjYxpUlLGo5Y7vVkDc2NyReTg/viewform?usp=embed_facebook'
html = urllib.request.urlopen(url).read().decode('utf-8')
inputs = re.findall(r'<input[^>]*type="hidden"[^>]*>', html)
for i in inputs:
    print(i)
