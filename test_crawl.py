import sys
sys.stdout.reconfigure(encoding='utf-8')

print("[사람인 테스트]")
try:
    import crawlers.saramin as saramin
    jobs = saramin.crawl(['아모레퍼시픽', '에이피알'])
    print(f"수집: {len(jobs)}건")
    for j in jobs[:3]:
        print(f"  - {j['회사명']} | {j['포지션명']}")
except Exception as e:
    import traceback
    print(f"오류: {e}")
    traceback.print_exc()

print("\n[원티드 테스트]")
try:
    import crawlers.wanted as wanted
    jobs2 = wanted.crawl(['아모레퍼시픽'])
    print(f"수집: {len(jobs2)}건")
    for j in jobs2[:3]:
        print(f"  - {j['회사명']} | {j['포지션명']}")
except Exception as e:
    import traceback
    print(f"오류: {e}")
    traceback.print_exc()
