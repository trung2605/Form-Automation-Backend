import requests

url = "https://docs.google.com/forms/d/e/1FAIpQLSc1NTZ6SAuOdbWtL5B9fwLdFGmrogS9V9LktK4VaDSKiVvyWQ/viewform"

print(f"Checking URL: {url}")
try:
    r = requests.get(url, allow_redirects=False)
    print(f"Status Code: {r.status_code}")
    if r.status_code == 302:
        print(f"Redirect Location: {r.headers.get('Location')}")
    elif r.status_code == 200:
        print("Page is accessible (200 OK)")
    else:
        print(f"Form returned status: {r.status_code}")
except Exception as e:
    print(f"Error: {e}")
