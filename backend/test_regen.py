import requests

proxy_url = "http://localhost:8001/drafts/image/draft_48c5a01a_0.jpg"
print(f"Fetching from {proxy_url}...")
img_res = requests.get(proxy_url, allow_redirects=False)

print("HTTP Status Code:", img_res.status_code)
if img_res.status_code == 200:
    print("Proxy fetch SUCCESS! Size:", len(img_res.content), "bytes")
else:
    print("Proxy fetch FAILED:", img_res.text)
