from pathlib import Path
from hashlib import sha256
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import unquote,urlparse
import json

H=Path(__file__).resolve().parent;R=H.parents[1]
inv=json.loads((H/'inventory.json').read_text(encoding='utf-8'))
counts=Counter(r['status'] for r in inv)
rows=['# Реестр проверки материалов — 01.10.2026','',
      'Аудит исходной подборки: 86 файлов. Дополнительно пользователь передал PDF U01 в текущем разговоре. Нумерация относится к снимку до актуализации STATUS и роадмапа. Содержательные документы прочитаны; табличные поля проверены программно, нетекстовые страницы просмотрены. Подписи учтены без самостоятельной криптографической проверки. Ключ не читался.','',
      '| ID | Исходный файл | Проверка |','|---|---|---|']
for r in inv:
    note='Прочитан'
    if r.get('byte_duplicate_of'):note=f"Побайтовый дубликат {r['byte_duplicate_of']}; содержание учтено"
    elif r['path'].endswith('.pfx'):note='Только наличие файла; содержимое не читалось'
    elif r['path'].endswith('.p7s'):note='Контейнер подписи учтён; криптография не проверялась'
    elif r['path'].startswith('.~lock.'):note='Служебный файл блокировки; не доказательство'
    elif r['id'] in ['007','015']:note='Вся таблица прочитана программно, числовые поля сверены с PDF; результаты проверены лично'
    elif r['id']=='017':note='89 страниц; по извлечённому тексту совпадают с первыми 89 страницами 023'
    elif r['id']=='023':note='Основные приложения: текст, таблицы и сканы; 92 страницы'
    elif r['id']=='036':note='Обе страницы карточки движения просмотрены как изображения'
    elif r['id'] in ['026','027','029']:note='Прочитан и сопоставлен с другими версиями; различия дат сохранены'
    elif r['id']=='006':note='Содержит только placeholder'
    if r.get('pages') and r['id'] not in ['017','023','036']:note+=f"; {r['pages']} стр."
    label=r['path'].replace('|','\\|')
    target=(R/r['path']).as_posix()
    # The private key is deliberately not made into a clickable artifact link.
    display=f'`{label}`' if r['path'].endswith('.pfx') else f'[{label}](<{target}>)'
    rows.append(f"| {r['id']} | {display} | {note} |")
u=json.loads((H/'received'/'provenance.json').read_text(encoding='utf-8'))
up=H/'received'/Path(u['source_path']).name
rows.extend(['',f"**U01.** [Пояснения о сборе, ЕСІТС 29.07.2026](<{up.as_posix()}>) — 2 страницы, прочитаны и просмотрены. Получены от пользователя 01.10.2026; исходник сохранён без изменения. Совпадение с карточкой № 75447 требует подтверждения в кабинете; содержит только вопрос судебного сбора.",'',
             '## Фактические сообщения пользователя',
             '',
             '- 01.10.2026: заседание 29.07 не состоялось по техническим причинам; 5 октября будет первым фактическим заседанием.',
             '- 01.10.2026: ответ банка пользователь не получал; проживает в другом городе, по адресу регистрации не находится.',
             '- Эти сообщения зафиксированы как сообщения пользователя, а не как текст судебного определения.',
             '',
             '## Не получено',
             '',
             '- Ответ банка от 27.07.2026 № 74171/26-Вх, 6 листов, приложения и подтверждения направления/вручения.',
             '- Полная актуальная карточка дела, поступление и судебное разрешение встречного иска и ходатайства об истребовании.',
             '',
             '## Что менялось',
             '',
             '- Актуализированы только STATUS.md и рабочий HTML-роадмап. Их оригиналы сохранены в originals/.',
             '- Остальные исходные файлы не изменялись. Копия PDF пользователя сохранена в received/; служебные извлечения и проверки — внутри audit/2026-10-01/.',
             '- Существующие DOCX/PDF процессуальных документов не переписаны. Новых документов в суд не подано.',
             '',
             '## Воспроизводимая проверка',
             '',
             '- extraction_checks.json: соответствие 349 строк расчёта и 697 операций исходному PDF.',
             '- transaction_continuity.json: отсутствие разрывов между 696 последовательными переходами выписки.',
             '- numeric_checks.json: суммы комиссий, начислений, платежей, контрольная модель и её ограничения.',
             '- images/: визуальные проверки сканов и карточки движения; это производные изображения, не новые доказательства.',
             '- inventory.json / received/provenance.json: размер и SHA-256 исходных материалов; без содержимого ключа.',
             ''])
(H/'РЕЕСТР_ПРОВЕРКИ.md').write_text('\n'.join(rows),encoding='utf-8')

changed=[]
for r in inv:
    if 'sha256' not in r:continue
    if sha256((R/r['path']).read_bytes()).hexdigest()!=r['sha256']:changed.append(r['id'])
assert sorted(changed)==['005','035'],changed
for id_,name in [('005','STATUS-before.md'),('035','roadmap-2.0-before.html')]:
    r=next(x for x in inv if x['id']==id_)
    assert sha256((H/'originals'/name).read_bytes()).hexdigest()==r['sha256']
assert sha256(up.read_bytes()).hexdigest()==u['sha256']

class Links(HTMLParser):
    def __init__(self):super().__init__();self.hrefs=[];self.ids=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'href' in a:self.hrefs.append(a['href'])
        if 'id' in a:self.ids.append(a['id'])
road=R/'Дорожня карта 2.0 — дерево сценаріїв (А-Банк).html'
p=Links();p.feed(road.read_text(encoding='utf-8'))
missing=[]
for href in p.hrefs:
    if href.startswith('#'):
        if href[1:] not in p.ids:missing.append(href)
    elif not urlparse(href).scheme:
        if not (R/unquote(href)).exists():missing.append(href)
assert not missing,missing
checks={'original_file_count':len(inv),'additional_pdf_count':1,'source_status_counts':dict(counts),'modified_original_ids':changed,'all_other_original_hashes_preserved':True,'original_backups_hash_verified':True,'received_pdf_hash_preserved':True,'roadmap_local_links_valid':True,'live_esits_checked':False,'signatures_cryptographically_verified':False,'personal_key_content_accessed':False}
(H/'validation.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False,indent=2))
