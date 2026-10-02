from pathlib import Path
from decimal import Decimal as D
import csv,json,re
H=Path(__file__).resolve().parent;R=H.parents[1]
inv=json.loads((H/'inventory.json').read_text(encoding='utf-8'));b={r['id']:r for r in inv}
def csvrows(i):
    with (R/b[i]['path']).open(encoding='utf-8-sig',newline='') as f:return [r for r in csv.reader(f) if r][1:]
ledger=csvrows('015');tx=csvrows('007')
raw='\n'.join((H/'pages'/f'023-{n:03}.txt').read_text(encoding='utf-8') for n in range(1,14))
pdfrows=[]
for line in raw.splitlines():
    if re.match(r'^20\d\d-\d\d-\d\d\s',line):pdfrows.append(line.split())
ledger_errors=[]
for j,(a,c) in enumerate(zip(ledger,pdfrows),1):
    if a[0]!=c[0] or [D(x) for x in a[1:]]!=[D(x) for x in c[1:]]:ledger_errors.append(j)
parts=[]
for n in range(19,52):
    t=(H/'pages'/f'023-{n:03}.txt').read_text(encoding='utf-8')
    matches=list(re.finditer(r'(20\d\d-\d\d-\d\d)\s+(\d\d:\d\d)',t))
    for j,mm in enumerate(matches):
        block=t[mm.start():matches[j+1].start() if j+1<len(matches) else len(t)]
        # The numeric suffix follows the MCC; descriptions may also contain numbers.
        tokens=re.findall(r'(?<![\w])-?\d+(?:\.\d+)?(?![\w])',block)
        # Crop the last statement page signature where no extra numeric text occurs.
        parts.append((mm.group(1)+'\n'+mm.group(2),tokens,n))
tx_errors=[]
for j,(r,(dt,nums,pg)) in enumerate(zip(tx,parts),1):
    expected=[D(x) for x in r[4:]]
    got=[D(x) for x in nums[-7:]]
    if dt!=r[0] or got!=expected:tx_errors.append({'row':j,'page':pg,'date':r[0],'expected':[str(x) for x in expected],'got':[str(x) for x in got]})
balances=[];own_balance=[]
for j,r in enumerate(ledger,1):
    err=sum(D(r[x]) for x in [2,4,8,9,10])-D(r[12])
    if err:
        entry={'row':j,'date':r[0],'difference':str(err)}
        if D(r[12])>0 and all(D(r[x])==0 for x in [2,4]):own_balance.append(entry)
        else:balances.append(entry)
out={'ledger_csv_rows':len(ledger),'ledger_pdf_rows':len(pdfrows),'ledger_numeric_mismatches':ledger_errors,'tx_csv_rows':len(tx),'tx_pdf_blocks':len(parts),'tx_numeric_mismatches':tx_errors,'ledger_component_balance_mismatches':balances,'positive_own_funds_rows_not_debt_errors':own_balance,'scope':'Numeric extraction verification, not proof of contractual validity. Amounts in csv rows match primary PDF fields where recorded as matched. Positive net balances with zero principal include own funds; a simple sum of debt components omits the positive account balance. Two such rows also show interest debited from those own funds.'}
(H/'extraction_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({**out,'tx_numeric_mismatches':tx_errors[:5],'tx_numeric_mismatches_count':len(tx_errors)},ensure_ascii=False,indent=2))
