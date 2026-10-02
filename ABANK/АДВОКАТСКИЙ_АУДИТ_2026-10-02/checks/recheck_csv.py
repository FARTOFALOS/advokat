from pathlib import Path
from decimal import Decimal as D
import csv,json
R=Path(__file__).resolve().parents[1]
def rows(name):
    with (R/'sources'/name).open(encoding='utf-8-sig',newline='') as f:return [r for r in csv.reader(f) if r][1:]
tx=rows('E007.csv');ledger=rows('E015.csv')
fees=[r for r in tx if D(r[8])]
errors=[i for i,(new,old) in enumerate(zip(tx,tx[1:]),1) if D(new[10])-D(old[10])!=D(new[4])]
result={'transaction_rows':len(tx),'ledger_rows':len(ledger),'fee_count':len(fees),'fee_total':str(sum(D(r[8]) for r in fees)),'installment_fee_count':sum('Розстрочка' in r[2] for r in fees),'installment_fees':str(sum(D(r[8]) for r in fees if 'Розстрочка' in r[2])),'credit_total':str(sum(D(r[4]) for r in tx if D(r[4])>0)),'ledger_payments':str(sum(D(r[11]) for r in ledger)),'continuity_errors':errors,'pdfs_opened':False}
assert result['transaction_rows']==697 and result['ledger_rows']==349
assert result['fee_count']==96 and result['fee_total']=='7170.44'
assert not errors
print(json.dumps(result,ensure_ascii=False,indent=2))
