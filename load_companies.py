import json, sys, openpyxl
sys.stdout.reconfigure(encoding='utf-8')

# 상위 90개
wb1 = openpyxl.load_workbook(r'C:\Users\fourcompany\Downloads\2025년 화장품 뷰티 기업 상위 90곳 경영실적, 레버리지비율.xlsx')
ws1 = wb1.active
top90 = []
for row in ws1.iter_rows(min_row=2, values_only=True):
    if row[0] and row[1]:
        name = str(row[1]).strip().rstrip('*')
        top90.append({'순위': row[0], '회사명': name})

# 홈페이지 리스트 (헤더 row2, B/C 컬럼)
wb2 = openpyxl.load_workbook(r'C:\Users\fourcompany\Downloads\타사 홈페이지 리스트.xlsx')
ws2 = wb2.active
homepage = []
for row in ws2.iter_rows(min_row=3, values_only=True):
    name = row[1] if len(row) > 1 else None
    url  = row[2] if len(row) > 2 else ''
    if name and str(name).strip() not in ('회사명', ''):
        cleaned_url = str(url).strip().split('?')[0] if url else ''
        homepage.append({'회사명': str(name).strip(), 'URL': cleaned_url})

print(f'TOP90: {len(top90)}개')
print(f'HOMEPAGE: {len(homepage)}개')

with open('company_lists.json', 'w', encoding='utf-8') as f:
    json.dump({'top90': top90, 'homepage': homepage}, f, ensure_ascii=False, indent=2)

print('저장 완료')
print('TOP90 첫 5개:', [c['회사명'] for c in top90[:5]])
print('홈페이지 첫 5개:', [h['회사명'] for h in homepage[:5]])
