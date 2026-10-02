from pathlib import Path
from hashlib import sha256
from html.parser import HTMLParser
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import json
import pypdfium2 as pdfium
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
TEXT = OUT / 'extracted'
TEXT.mkdir(exist_ok=True)

class HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.skip+=1
        if tag in ('p','div','tr','li','h1','h2','h3','h4','br','section','details','summary'): self.parts.append('\n')
        if tag in ('td','th'): self.parts.append(' | ')
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
        if tag in ('p','div','tr','li','h1','h2','h3','h4','section','details','summary'): self.parts.append('\n')
    def handle_data(self,data):
        if not self.skip: self.parts.append(data)

def decode(data):
    if data.startswith((b'\xff\xfe',b'\xfe\xff')): return data.decode('utf-16')
    for enc in ('utf-8-sig','cp1251'):
        try: return data.decode(enc)
        except UnicodeError: pass
    return data.decode('utf-8',errors='replace')

manifest=[]; hashes={}
paths=sorted(p for p in ROOT.rglob('*') if p.is_file() and 'audit' not in p.relative_to(ROOT).parts and '.git' not in p.relative_to(ROOT).parts)
for i,p in enumerate(paths,1):
    rec={'id':f'{i:03}', 'path':str(p.relative_to(ROOT)), 'bytes':p.stat().st_size}
    if p.suffix.lower() == '.pfx':
        rec['status']='credential file: content not accessed'
        manifest.append(rec); continue
    data=p.read_bytes(); digest=sha256(data).hexdigest(); rec['sha256']=digest
    if digest in hashes: rec['byte_duplicate_of']=hashes[digest]
    else: hashes[digest]=rec['id']
    ext=p.suffix.lower(); txt=''
    try:
        prior=next((x for x in manifest if x['id']==rec.get('byte_duplicate_of') and 'extracted' in x),None)
        if prior:
            txt=(OUT/prior['extracted']).read_text(encoding='utf-8')
            for key in ('pages','page_chars'): 
                if key in prior: rec[key]=prior[key]
        elif ext=='.pdf' or data.startswith(b'%PDF-'):
            with pdfium.PdfDocument(p) as doc:
                texts=[]
                for page in doc:
                    textpage=page.get_textpage()
                    texts.append(textpage.get_text_range())
                    textpage.close(); page.close()
            rec['pages']=len(texts); rec['page_chars']=[len(t) for t in texts]
            txt='\n\n'.join(f'=== PAGE {j} ===\n{t}' for j,t in enumerate(texts,1))
        elif ext=='.docx':
            with ZipFile(p) as z:
                members=[n for n in z.namelist() if n=='word/document.xml' or n.startswith(('word/header','word/footer','word/comments','word/footnotes','word/endnotes')) and n.endswith('.xml')]
                chunks=[]
                for n in members:
                    root=ET.fromstring(z.read(n)); ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    lines=[''.join(el.text or '' for el in par.iter() if el.tag in ('{'+ns['w']+'}t','{'+ns['w']+'}delText')) for par in root.findall('.//w:p',ns)]
                    chunks.append(f'=== {n} ===\n'+'\n'.join(lines))
                txt='\n'.join(chunks)
        elif ext in ('.html','.htm'):
            parser=HTMLText(); parser.feed(decode(data)); txt='\n'.join(line.strip() for line in ''.join(parser.parts).splitlines() if line.strip())
        elif ext in ('.md','.txt','.csv','.tsv','.gitignore') or p.name=='.gitignore': txt=decode(data)
        elif ext=='.p7s': rec['status']='detached signature inventoried; cryptographic verification not performed'
        else: rec['status']='auxiliary binary or lock file inventoried'
        if txt:
            dest=TEXT/(rec['id']+'.txt'); dest.write_text(txt,encoding='utf-8')
            rec.update(extracted=str(dest.relative_to(OUT)),chars=len(txt),text_sha256=sha256(txt.encode()).hexdigest(),status='text extracted')
    except Exception as e: rec['status']='ERROR: '+repr(e)
    manifest.append(rec)
(OUT/'inventory.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
for r in manifest:
    print(f"{r['id']} | {r['path']} | {r.get('pages','')} pages | {r.get('chars','')} chars | duplicate {r.get('byte_duplicate_of','')} | {r['status']}")
print('FILES',len(manifest))
