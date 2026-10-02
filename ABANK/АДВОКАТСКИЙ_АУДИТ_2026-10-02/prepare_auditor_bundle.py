from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile, ZIP_DEFLATED
from collections import Counter
import json, shutil, re, csv
from decimal import Decimal as D

R=Path(__file__).resolve().parent;AB=R.parent;PRE=AB/'audit/2026-10-01'
for name in ['sources','texts','drafts','checks']:(R/name).mkdir(exist_ok=True)
inv=json.loads((PRE/'inventory.json').read_text(encoding='utf-8'))
skip={'001','002','004','067'}
seen={};records=[]
for item in inv:
    if item['id'] in skip:continue
    src=AB/item['path']
    if item['id']=='005':src=PRE/'originals/STATUS-before.md'
    if item['id']=='035':src=PRE/'originals/roadmap-2.0-before.html'
    # Opaque copy/hash only: no PDF parser, OCR, page renderer or PDF reading by the model.
    digest=sha256(src.read_bytes()).hexdigest()
    assert digest==item['sha256'],('source changed',item['id'])
    eid='E'+item['id']
    if digest in seen:
        canonical=seen[digest];raw=canonical['copy'];duplicate=canonical['id']
    else:
        raw=f'sources/{eid}{src.suffix.lower()}'
        shutil.copyfile(src,R/raw);duplicate=None
        seen[digest]={'id':eid,'copy':raw}
    textfile=None
    if item.get('extracted'):
        textfile=f'texts/{eid}.txt';shutil.copyfile(PRE/item['extracted'],R/textfile)
    if item['id']=='036':
        textfile='texts/E036_visual_observation.txt'
        (R/textfile).write_text('Краткая запись визуального наблюдения 01.10.2026. Не OCR и не замена оригинала. PDF в завершающей фазе 02.10 повторно не открывался.\n\nКарточка движения ходатайства об истребовании доказательств: дело 127/20805/26, производство 2/127/5742/26; состояние «Надіслано сторонам»; изменение состояния и направление 22.07.2026 17:20. Адресат АТ «АКЦЕНТ-БАНК», ЕДРПОУ 14360080. На второй странице в таблице доставки указана доставка этому адресату 22.07.2026 17:20. Снимок карточки сформирован 22.07.2026 17:22. Эта запись не устанавливает принятия ходатайства судом или его удовлетворения.\n',encoding='utf-8')
    kind='Контекст или рабочий материал'
    if src.suffix.lower()=='.p7s':kind='Публичный контейнер подписи; криптографически не проверен'
    elif 'копии ответов' in item['path'] or 'повестка в суд' in item['path']:kind='Сохранённая судебная копия или подтверждение'
    elif item['id'] in ['016','017','023']:kind='Материалы банка'
    elif item['id']=='003':kind='Ролевая проектная инструкция; не доказательство юридической квалификации'
    elif item['id'] in ['026','027','029','058','059','060','037']:kind='Архив процессуального текста; статус подачи проверяется отдельно'
    records.append({'id':eid,'original_path':item['path'],'copy':raw,'text':textfile,'sha256':digest,'duplicate_of':duplicate,'kind':kind,'pages_in_prior_inventory':item.get('pages')})

u=json.loads((PRE/'received/provenance.json').read_text(encoding='utf-8'))
src=PRE/'received'/Path(u['source_path']).name
assert sha256(src.read_bytes()).hexdigest()==u['sha256']
shutil.copyfile(src,R/'sources/U01.pdf');shutil.copyfile(PRE/'extracted/U01.txt',R/'texts/U01.txt')
records.append({'id':'U01','original_path':src.name,'copy':'sources/U01.pdf','text':'texts/U01.txt','sha256':u['sha256'],'duplicate_of':None,'kind':'Передан клиентом 01.10; пояснения ЕСІТС о сборе от 29.07','pages_in_prior_inventory':2})

packet=AB/'ПАКЕТ_К_05-10-2026.zip'
prefix='ПАКЕТ_К_05-10-2026/'
with ZipFile(packet) as z:
    for entry in z.infolist():
        assert entry.filename.startswith(prefix)
        rel=Path(entry.filename[len(prefix):])
        assert not rel.is_absolute() and '..' not in rel.parts
        dst=(R/'drafts'/rel).resolve()
        assert dst.is_relative_to((R/'drafts').resolve())
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(z.read(entry))

for f in ['numeric_checks.json','extraction_checks.json','transaction_continuity.json','validation.json']:
    shutil.copyfile(PRE/f,R/'checks'/f)
drafts=json.loads((AB/'ПАКЕТ_К_05-10-2026/packet_files.json').read_text(encoding='utf-8'))
draft_records=[]
for item in drafts:
    rec={'id':f"P{item['number']:02}",'role':item['role'],'pages':item['pages'],'files':{}}
    for fmt in ['txt','docx','pdf']:
        p=R/'drafts'/item[fmt]
        rec['files'][fmt]={'path':p.relative_to(R).as_posix(),'sha256':sha256(p.read_bytes()).hexdigest()}
    draft_records.append(rec)

rows=['# Каталог источников для адвокатского аудита','',
'Основной анализ выполняется по текстам. Ссылки на оригиналы оставлены для независимой проверки; PDF в этой фазе моделью повторно не читались. Тексты извлечения не заменяют подписанные документы и не содержат распознавания всех сканов. Побайтовые дубликаты ведут к одной неизменной копии.','',
'**В подборке нет личного ключа КЭП.** Подписи p7s — отдельные исходные данные, не результат новой криптографической проверки.','',
'| Код | Источник | Доступ | Статус |','|---|---|---|---|']
for item in records:
    label=item['original_path'].replace('|','\\|')
    links=f"[Оригинал]({item['copy']})"
    if item['text']:links=f"[{'Запись прежнего просмотра' if item['id']=='E036' else 'Текст для поиска'}]({item['text']}) · "+links
    note=item['kind']
    if item['duplicate_of']:note+=f"; побайтовый дубликат {item['duplicate_of']}"
    rows.append(f"| {item['id']} | {label} | {links} | {note} |")
rows+=['','## Подготовленные проекты','',
'Ниже проекты, не доказательство их направления суду. Фактический адрес в них не включён. Даты 01.10 сохранены.','',
'| Код | Назначение | Доступ |','|---|---|---|']
for f in draft_records:
    links=' · '.join(f"[{label}]({f['files'][fmt]['path']})" for fmt,label in [('txt','Текст'),('docx','Word'),('pdf','PDF')])
    rows.append(f"| {f['id']} | {f['role']} · {f['pages']} стр. | {links} |")
rows+=['','P01–P04 — обращения по указанным в роадмапе условиям; P05–P06 — приложения; P07 — только личная репетиция. Внутренний аудит и досье не предназначены для направления суду/банку.','',
'## Числовые проверки','',
'[Проверка извлечения 349 и 697 строк](checks/extraction_checks.json), [контрольные суммы и модель](checks/numeric_checks.json), [непрерывность выписки](checks/transaction_continuity.json). Эти результаты получены на предыдущем этапе; PDF повторно не анализировались. Скрипт `checks/recheck_csv.py` повторяет только агрегаты CSV без чтения PDF.','']
(R/'КАТАЛОГ_ИСТОЧНИКОВ.md').write_text('\n'.join(rows),encoding='utf-8')
manifest={'date':'2026-10-02','source_snapshot':'2026-10-01 + received U01','source_count':len(records),'unique_source_files':len(seen)+1,'source_records':records,'drafts':draft_records,'excluded_original_ids':sorted(skip),'private_key_read':False,'pdfs_reparsed_this_phase':False,'signature_verification_performed':False,'independent_lawyer_review_completed':False,'external_submission_performed':False,'client_goal_provenance':'Direct user message in this conversation on 2026-10-02: maximize lawful time before judgment, ideally about a year, with almost no money; no authority to fabricate grounds, file or sign on behalf of user.'}
(R/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

readme='''# Начало независимого адвокатского аудита

Откройте **ДОСЬЕ.html**. Это один основной документ: факты, цель клиента, 12 доводов, проверка 7 проектов, 35 ветвей действий до завершения, сроки и вопросы аудитору. Тот же текст доступен в Markdown.

Начните с разделов 1, 4–7 и 17. Затем используйте каталог источников и отдельные ветви по актуальному событию. Проверка идёт прежде всего по текстам; первичные файлы сохранены без преобразования для независимой сверки.

Подготовленные P01–P07 находятся в drafts/. Статус «подготовлено» не означает «подано» или «принято». Ответ банка на шести листах отсутствует; судебное разрешение встречного иска и истребования не установлено по актуальной карточке.

Клиент 02.10.2026 уточнил приоритет: максимально возможное законное время до решения, желательно год, ввиду почти отсутствующих средств. Досье оценивает способы и пределы; не обещает срок и не предлагает фиктивные причины или необоснованные обращения.

**Материалы предназначены для клиента и выбранного им независимого адвоката. Не подавать архив целиком в суд и не направлять банку.** Внутреннее обозначение не является гарантией адвокатской тайны. Внешняя передача не выполнена.

Личный ключ КЭП не включён. Не передавайте исходный рабочий каталог целиком без отбора: там имеется личный контейнер ключа. Для проверки материалов предназначен этот отобранный архив.

Фактический адрес и город пребывания не включены в новые судебные проекты. Известный адрес регистрации обозначен именно как регистрация. Возможные законные обязанности отдельно оценивает адвокат; ложные сведения не предлагаются.

Независимый аудит ещё не выполнен. Просим пофайловые замечания: подтвердить в определённой границе, допустить при условии, исправить или не использовать. Нет необходимости соглашаться с общей стратегией автора.
'''
(R/'README.md').write_text(readme,encoding='utf-8')
print(json.dumps({k:manifest[k] for k in ['source_count','unique_source_files','private_key_read','pdfs_reparsed_this_phase']},ensure_ascii=False))
