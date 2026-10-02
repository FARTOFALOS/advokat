from pathlib import Path
from hashlib import sha256
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
from zipfile import ZipFile,ZIP_DEFLATED
import json,re
R=Path(__file__).resolve().parent;AB=R.parent
m=json.loads((R/'manifest.json').read_text(encoding='utf-8'))
for record in m['source_records']:
    assert sha256((R/record['copy']).read_bytes()).hexdigest()==record['sha256'],record['id']
for record in m['drafts']:
    for f in record['files'].values():assert sha256((R/f['path']).read_bytes()).hexdigest()==f['sha256']
md=(R/'ДОСЬЕ_СТРАТЕГИЯ_И_ДЕРЕВО_СОБЫТИЙ.md').read_text(encoding='utf-8')
branches=re.findall(r'^### (B\d{2})\b',md,re.M)
claims=re.findall(r'^### (C\d{2})\b',md,re.M)
assert branches==[f'B{i:02}' for i in range(1,36)]
assert claims==[f'C{i:02}' for i in range(1,13)]
assert not re.search(r'<!-- (BRANCHES|ENDGAME)_INSERT -->',md)
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=[]
    def handle_starttag(self,t,a):
        d=dict(a)
        if 'href' in d:self.links.append(d['href'])
        if 'id' in d:self.ids.append(d['id'])
missing=[]
for page in [R/'ДОСЬЕ.html',R/'КАТАЛОГ_ИСТОЧНИКОВ.html',R/'drafts/roadmap.html',AB.parent/'НАЧАТЬ_ЗДЕСЬ.html']:
    p=Links();p.feed(page.read_text(encoding='utf-8'))
    assert len(p.ids)==len(set(p.ids)),('duplicate anchors',str(page))
    for link in p.links:
        if link.startswith('#'):
            if unquote(link[1:]) not in p.ids:missing.append((str(page),link))
        elif not urlparse(link).scheme:
            path=unquote(link.split('#')[0])
            # The output archive is created below; all other links must already resolve.
            if path.endswith('АДВОКАТСКИЙ_АУДИТ_2026-10-02.zip'):continue
            if not (page.parent/path).exists():missing.append((str(page),link))
assert not missing,missing
allowed_root=['ДОСЬЕ.html','ДОСЬЕ_СТРАТЕГИЯ_И_ДЕРЕВО_СОБЫТИЙ.md','КАТАЛОГ_ИСТОЧНИКОВ.html','КАТАЛОГ_ИСТОЧНИКОВ.md','manifest.json','README.md']
files=[R/name for name in allowed_root]
for directory in ['sources','texts','drafts','checks']:files.extend(p for p in (R/directory).rglob('*') if p.is_file())
for p in files:assert p.suffix.lower() not in ['.pfx','.p12','.key','.pem'],p
archive=AB/'АДВОКАТСКИЙ_АУДИТ_2026-10-02.zip'
with ZipFile(archive,'w',compression=ZIP_DEFLATED) as z:
    for p in files:z.write(p,Path(R.name)/p.relative_to(R))
with ZipFile(archive) as z:assert z.testzip() is None
out={'date':'2026-10-02','sections':len(re.findall(r'^## \d+ ',md,re.M)),'words':len(md.split()),'branches':len(branches),'claims':len(claims),'source_records':len(m['source_records']),'unique_sources':m['unique_source_files'],'drafts':len(m['drafts']),'source_hashes_verified':True,'draft_hashes_verified':True,'local_links_valid':True,'archive_crc_valid':True,'archive_file_count':len(files),'archive_size':archive.stat().st_size,'private_keys_excluded':True,'pdfs_reparsed_this_phase':False,'independent_lawyer_review_completed':False,'external_submission_performed':False}
(R/'bundle_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
