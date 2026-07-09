import sys, requests
sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "wanted-user-agent": "wanted-web",
    "Accept": "application/json",
}

# 1) 기업 검색 API 테스트
resp = requests.get("https://www.wanted.co.kr/api/v4/companies", params={"query": "아모레퍼시픽"}, headers=HEADERS, timeout=8)
print(f"기업검색 status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"keys: {list(data.keys())}")
    items = data.get("data", [])
    print(f"items count: {len(items)}")
    if items:
        print(f"first item keys: {list(items[0].keys())}")
        print(f"first item: {items[0]}")
else:
    print(resp.text[:300])

# 2) 공고 검색 API 직접 테스트 (keyword)
print("\n--- 공고 키워드 검색 ---")
resp2 = requests.get("https://www.wanted.co.kr/api/v4/jobs", params={"query": "아모레퍼시픽", "country": "kr", "limit": 5}, headers=HEADERS, timeout=8)
print(f"공고검색 status: {resp2.status_code}")
if resp2.status_code == 200:
    data2 = resp2.json()
    print(f"keys: {list(data2.keys())}")
    items2 = data2.get("data", [])
    print(f"items: {len(items2)}")
    if items2:
        print(f"sample: {items2[0].get('position')} / {items2[0].get('company', {}).get('name')}")
