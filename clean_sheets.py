"""화이트리스트 외 기업 데이터 삭제"""
import json, sys, time
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\fourcompany\jd_crawler\company_lists.json', encoding='utf-8') as f:
    data = json.load(f)

# 화이트리스트: TOP90 + 홈페이지 리스트
whitelist = set()
for c in data['top90']:
    if c['회사명'] not in ('회사명', ''):
        whitelist.add(c['회사명'].strip())
for c in data['homepage']:
    if c['회사명'] not in ('포컴퍼니', '회사명', ''):
        whitelist.add(c['회사명'].strip())

print(f'화이트리스트: {len(whitelist)}개 기업')

from sheets_manager import get_sheet
sh = get_sheet()
ws = sh.worksheet('RAW_DATA')
all_vals = ws.get_all_values()
print(f'현재 데이터: {len(all_vals)-1}건')

# 삭제 대상 (화이트리스트에 없는 기업)
to_delete = []
for i, row in enumerate(all_vals[1:], start=2):
    if not row or not row[1]:
        continue
    company = row[1].strip()
    # 부분 매칭 (회사명이 완전히 일치하지 않아도 포함 체크)
    matched = any(
        w in company or company in w
        for w in whitelist
    )
    if not matched:
        to_delete.append((i, company))

excluded = list(set(c for _, c in to_delete))
print(f'삭제 대상: {len(to_delete)}건')
print('제외 기업 예시:', excluded[:10])

# 유지할 행만 추출
keep_rows = [
    row for i, row in enumerate(all_vals[1:], start=2)
    if (i, row[1].strip() if row and row[1] else '') not in {(i, c) for i, c in to_delete}
]

# 시트 전체 초기화 후 헤더 + 유지 데이터 한 번에 쓰기
header = all_vals[0]
ws.clear()
ws.append_row(header)
if keep_rows:
    ws.append_rows(keep_rows, value_input_option="USER_ENTERED")

print(f'정리 후 남은 데이터: {len(keep_rows)}건')
