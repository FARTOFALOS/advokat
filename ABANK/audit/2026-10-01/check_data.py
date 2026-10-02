from pathlib import Path
from decimal import Decimal as D
from datetime import date, timedelta
from collections import Counter, defaultdict
import csv, json, re
import pypdfium2 as pdfium
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
items=json.loads((HERE/'inventory.json').read_text(encoding='utf-8'))
byid={r['id']:r for r in items}
def source(i): return ROOT/byid[i]['path']
def readcsv(i):
    with source(i).open(encoding='utf-8-sig',newline='') as f:
        return [r for r in csv.reader(f) if r]
tx=readcsv('007'); ledger=readcsv('015'); th,*tr=tx; lh,*lr=ledger
rows=[]
for r in lr:
    rows.append([date.fromisoformat(r[0])]+[D(v) for v in r[1:]])
stats={
    'transaction_rows':len(tr),'ledger_rows':len(lr),
    'transaction_columns':th,'ledger_columns':lh,
    'tx_credits':str(sum((D(r[4]) for r in tr if D(r[4])>0),D(0))),
    'tx_debits':str(sum((D(r[4]) for r in tr if D(r[4])<0),D(0))),
    'tx_fees':str(sum((D(r[8]) for r in tr),D(0))),
    'tx_interest':str(sum((D(r[4]) for r in tr if 'Списання відсотків' in r[2]),D(0))),
    'ledger_payments':str(sum((r[11] for r in rows),D(0))),
    'ledger_accrual_column':str(sum((r[7] for r in rows),D(0))),
    'last_ledger':lr[-1],
}
cat=defaultdict(lambda: {'count':0,'fees':D(0),'flow':D(0)})
for r in tr:
    key=' '.join(r[2].split())
    if D(r[8]):
        if 'Розстрочка' in key: key='Розстрочка'
        elif 'Переказ' in key or 'переказ' in key: key='Перекази'
        elif 'готів' in key or 'банкомат' in key: key='Готівка'
        else: key=key[:90]
        cat[key]['count']+=1;cat[key]['fees']+=D(r[8]);cat[key]['flow']+=D(r[4])
stats['commission_categories']={k:{x:str(y) for x,y in v.items()} for k,v in cat.items()}
stats['positive_nonpayment_descriptions']=[r for r in tr if D(r[4])>0 and not any(s in r[2].lower() for s in ['поповнен','внесенн','погашенн'])]
stats['feb2021_transactions']=[r for r in tr if r[0].startswith(('2021-02','2021-03-01'))]
stats['feb2021_ledger']=[r for r in lr if r[0].startswith(('2021-01','2021-02','2021-03'))]
# Daily reconstruction: previous row's closing principal applies to days until next row.
# This is a diagnostic, not a certified counter-calculation; grace and within-day rules remain unknown.
pred=defaultdict(lambda:[D(0),D(0)])
for prev,cur in zip(rows,rows[1:]):
    d=prev[0]+timedelta(days=1)
    while d<=cur[0]:
        key=d.strftime('%Y-%m')
        base=-(prev[2]+prev[4])
        pred[key][0]+=base*prev[5]/D(36500)
        pred[key][1]+=(-prev[2]*prev[5]-prev[4]*prev[6])/D(36500)
        d+=timedelta(days=1)
actual=defaultdict(lambda:D(0))
for r in rows: actual[r[0].strftime('%Y-%m')]-=r[7]
stats['monthly_model']=[{'month':k,'actual_accrual_column':str(actual[k]),'base_model':str(round(v[0],2)),'double_on_overdue_model':str(round(v[1],2)),'difference_base':str(round(actual[k]-v[0],2))} for k,v in sorted(pred.items())]
stats['may2026_example']={'principal':'131434.82','rate':'40.8','days':31,'model':str(round(D('131434.82')*D('.408')*D(31)/D(365),2)),'bank':'4554.54'}
stats['june_reclassification']=str(rows[-2][9]-rows[-3][9])
(HERE/'numeric_checks.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
pagesdir=HERE/'pages';pagesdir.mkdir(exist_ok=True)
imgs=HERE/'images';imgs.mkdir(exist_ok=True)
for id_ in ['016','017','023']:
    text=(HERE/byid[id_]['extracted']).read_text(encoding='utf-8')
    pages=re.split(r'=== PAGE \d+ ===\n',text)[1:]
    for n,t in enumerate(pages,1): (pagesdir/f'{id_}-{n:03}.txt').write_text(t,encoding='utf-8')
    if id_=='023':
        print('PRIMARY PDF PAGE INDEX')
        for n,t in enumerate(pages,1):print(n,len(t),' '.join(t.split())[:120])
with pdfium.PdfDocument(source('023')) as pdf:
    needed=[15,17,18,75,79,81,82,89]
    thumbs=[]
    for n in needed:
        page=pdf[n-1];im=page.render(scale=1.7).to_pil();im.save(imgs/f'bank-{n:03}.png')
        small=im.copy();small.thumbnail((640,900))
        tile=Image.new('RGB',(660,940),'#ddd');tile.paste(small,((660-small.width)//2,30));ImageDraw.Draw(tile).text((15,8),f'PDF PAGE {n}',fill='black');thumbs.append(tile)
    sheet=Image.new('RGB',(2640,1880),'white')
    for i,im in enumerate(thumbs):sheet.paste(im,((i%4)*660,(i//4)*940))
    sheet.save(imgs/'bank-scans-contact.png')
with pdfium.PdfDocument(source('036')) as pdf:
    for n,page in enumerate(pdf,1):page.render(scale=1.7).to_pil().save(imgs/f'motion-receipt-{n}.png')
compact={k:v for k,v in stats.items() if k not in ['monthly_model','feb2021_transactions','feb2021_ledger','positive_nonpayment_descriptions','transaction_columns','ledger_columns']}
print(json.dumps(compact,ensure_ascii=False,indent=2))
print('RECENT MONTHS',json.dumps(stats['monthly_model'][-7:],ensure_ascii=False))
