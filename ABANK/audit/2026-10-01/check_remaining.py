from pathlib import Path
from decimal import Decimal as D
from collections import Counter
import json,csv,re,difflib
import pypdfium2 as pdfium
from PIL import Image,ImageDraw
H=Path(__file__).resolve().parent;R=H.parents[1]
m=json.loads((H/'inventory.json').read_text(encoding='utf-8'));b={x['id']:x for x in m}
def text(i):return (H/b[i]['extracted']).read_text(encoding='utf-8')
def norm(s):return re.sub(r'\s+','',s)
print('DOCX VERSIONS')
for a,c in [('026','027'),('027','029'),('058','059'),('058','055')]:
    aa=text(a).splitlines();cc=text(c).splitlines()
    print(a,c, ''.join(difflib.unified_diff(aa,cc,n=1))[:14500])
print('PDF 017/023 text-identical pages',sum(norm((H/'pages'/f'017-{n:03}.txt').read_text(encoding='utf-8'))==norm((H/'pages'/f'023-{n:03}.txt').read_text(encoding='utf-8')) for n in range(1,90)))
with (R/b['007']['path']).open(encoding='utf-8-sig',newline='') as f: tx=[r for r in csv.reader(f) if r][1:]
diffs=[]
for ix,(new,old) in enumerate(zip(tx,tx[1:]),2):
    err=D(new[10])-D(old[10])-D(new[4])
    if err:diffs.append({'csv_row':ix,'new':new,'old':old,'balance_delta_minus_flow':str(err)})
(H/'transaction_continuity.json').write_text(json.dumps(diffs,ensure_ascii=False,indent=2),encoding='utf-8')
print('BALANCE DIFFS',json.dumps(diffs,ensure_ascii=False))
print('OLD FIRST ROW',tx[-1])
print('FEES DATE RANGE',min(x[0] for x in tx if D(x[8])),max(x[0] for x in tx if D(x[8])))
# Remaining scans and blank backs are visually checked in one contact sheet.
with pdfium.PdfDocument(R/b['023']['path']) as pdf:
    nums=[16,52,54,56,58,76,80,83,84,85,86,87,88,91]
    tiles=[]
    for n in nums:
        im=pdf[n-1].render(scale=1.7).to_pil();im.save(H/'images'/f'bank-{n:03}.png')
        im.thumbnail((500,710));tile=Image.new('RGB',(520,745),'#ddd');tile.paste(im,((520-im.width)//2,25));ImageDraw.Draw(tile).text((8,7),f'PDF PAGE {n}',fill='black');tiles.append(tile)
    sheet=Image.new('RGB',(2080,2980),'white')
    for i,im in enumerate(tiles):sheet.paste(im,((i%4)*520,(i//4)*745))
    sheet.save(H/'images'/'remaining-scans.png')
    im=pdf[14].render(scale=4).to_pil();im.crop((0,int(im.height*.67),im.width,int(im.height*.86))).save(H/'images'/'application-date.png')
    for n in [13,49,60,70,73]:pdf[n-1].render(scale=2).to_pil().save(H/'images'/f'bank-detail-{n:03}.png')
