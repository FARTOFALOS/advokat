from pathlib import Path
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
from zipfile import ZipFile,ZIP_DEFLATED
import json,re,shutil
from docx import Document
from decimal import Decimal

R=Path(__file__).resolve().parent
files=json.loads((R/'packet_files.json').read_text(encoding='utf-8'))
info={
1:('Ознакомление с ответом банка','Подать первым, если ответ и приложения не получены. Запрашиваются также доказательства направления/вручения и время для возражений.','Сейчас'),
2:('Уточнённые письменные пояснения','Основная позиция по доступным документам, с исправлением факта о процентах. Приложить № 05. Содержит просьбу разрешить дополнительные пояснения.','Основной документ'),
3:('Нерешённые процессуальные вопросы','Если статус встречного иска и ходатайства не выяснен или вопросы не решены. Приложить две сохранённые квитанции.','По статусу дела'),
4:('Пояснения по встречному иску','Правильный номер спорного пункта, детализация комиссий и основание льготы по сбору. Приложить № 06. Сначала проверить судьбу встречной заявы.','После проверки статуса'),
5:('Контрольные числовые сопоставления','Приложение к № 02. Проверенные суммы, источники и границы выводов; не экспертное заключение и не признанный остаток.','К документу № 02'),
6:('Все 96 комиссионных операций','Приложение к № 04. Дата, описание, комиссия и страница банковского PDF. Итог — 7 170,44 грн.','К документу № 04'),
7:('Сценарий самостоятельной репетиции','Два вступления, 21 вопрос с вариантами ответов, техническая подготовка и действия после заседания. Не подавать в суд.','Только для Вас')}
cards=[]
for f in files:
    n=f['number'];title,desc,badge=info[n]
    cls='private' if f['role']=='private' else 'check' if n in [3,4] else 'known'
    links=[]
    for ext,label in [('pdf','PDF'),('docx','Word'),('txt','Текст')]:
        target=str(Path(f[ext])).replace('\\','/')
        assert (R/f[ext]).exists(),f[ext]
        links.append(f'<a href="{escape(target,quote=True)}">{label}</a>')
    cards.append(f'<article class="file" data-role="{f["role"]}"><span class="badge {cls}">{escape(badge)}</span><h3>{n:02} · {escape(title)}</h3><p>{escape(desc)}</p><p class="caption">{f["pages"]} стр. · подготовлено 01.10.2026</p><div class="file-links">'+''.join(links)+'</div></article>')
road=R/'roadmap.html';html=road.read_text(encoding='utf-8')
html,n=re.subn(r'<!-- DOCUMENT_CARDS -->.*?<!-- END_DOCUMENT_CARDS -->','<!-- DOCUMENT_CARDS -->\n'+'\n'.join(cards)+'\n<!-- END_DOCUMENT_CARDS -->',html,flags=re.S)
assert n==1
road.write_text(html,encoding='utf-8')

audit=R.parent/'audit/2026-10-01/АУДИТ_ПЕРЕД_05-10-2026.md'
shutil.copyfile(audit,R/'ДЛЯ_СЕБЕ/08_Повний_аудит.md')
readme='''# Пакет к заседанию 5 октября 2026 года

Откройте **roadmap.html**. Это входная страница с резюме, порядком подачи и ссылками на все файлы.

Дополнение 02.10.2026: клиент уточнил главный приоритет — максимально возможное законное время до решения, желательно около года, при почти отсутствующих средствах. Это цель, не гарантия срока. Реальные основания каждого шага, затраты и запасной финансовый путь оцениваются отдельно; фиктивные причины и необоснованные действия не предлагаются. Семь проектов остаются датированными 01.10 и перед подачей требуют проверки актуальности.

**Архив предназначен для Вас. Не отправляйте его целиком в суд:** внутри есть личная подготовка и внутренний аудит.

## Порядок

1. № 01 — запросить ответ банка от 27.07.2026 № 74171/26-Вх, приложения и доказательства доставки. Использовать, только пока факты о неполучении актуальны.
2. № 02 + № 05 — уточнённая позиция и арифметические сопоставления. Суду предлагается разрешить дополнительные пояснения по ч. 5 ст. 174 ЦПК.
3. № 03 + квитанция 7900097 + карточка движения 22.07 — если процессуальные вопросы ещё не решены или их результат неизвестен.
4. № 04 + № 06 — после проверки, что встречный иск находится в суде и не возвращён. При наличии определения об устранении недостатков сначала исполнить именно его требования. Общие пояснения его не заменяют.
5. № 07 и № 08 — только для себя, в суд и банк не направлять.

PDF — для чтения/подачи; DOCX — для редактирования; TXT — текст для формы. Не направляйте три формата как три разных обращения. На всех подготовленных обращениях стоит дата 01.10.2026: перед подачей проверьте дату, актуальность фактов и реквизиты. Подписываете и направляете Вы самостоятельно.

Фактический адрес и город пребывания не включены в новые судебные документы. В шапке указан известный суду адрес регистрации и электронный кабинет. Это не освобождение от всех обязанностей по статье 131 ЦПК и не основание сообщать ложные сведения.

До определения суда о переносе готовьтесь участвовать 05.10.2026 в 10:00; подключение к ВКЗ в 09:40–09:45. Просьба об отложении сама по себе заседание не отменяет.

Ответ банка пока неизвестен. После получения необходима проверка его содержания; пакет не заменяет будущие адресные возражения. Статус встречного иска и разрешение истребования нужно установить в деле. Сроки не обнуляются первым фактически состоявшимся заседанием.

## Что подготовлено

'''
for f in files:readme+=f"- {f['number']:02}: {info[f['number']][0]} — {f['pages']} стр.\n"
readme+='''
Внутренний аудит № 08 сохранён для истории анализа. Часть его предварительных рекомендаций по адресным сведениям уточнена в текущем роадмапе с учётом Вашего последующего указания не раскрывать местонахождение. Для подачи используйте текущие файлы из этого пакета, а не старые июльские шпаргалки или предварительный отдельный черновик запроса.

Все 19 страниц семи документов просмотрены после преобразования Word в PDF. Приложение № 06 содержит 96 операций; суммы и страничные ссылки сверены. Исходные судебные и банковские документы не переписаны. Подача, подписание КЭП, платежи и контакты с банком этим пакетом не выполнялись.
'''
(R/'README.md').write_text(readme,encoding='utf-8')

# Structural and content checks on the final, portable set.
class Links(HTMLParser):
    def __init__(self):super().__init__();self.href=[];self.ids=[]
    def handle_starttag(self,t,attrs):
        a=dict(attrs)
        if 'href' in a:self.href.append(a['href'])
        if 'id' in a:self.ids.append(a['id'])
parser=Links();parser.feed(html);missing=[]
for h in parser.href:
    if h.startswith('#'):
        if h[1:] not in parser.ids:missing.append(h)
    elif not urlparse(h).scheme and not (R/unquote(h)).exists():missing.append(h)
assert not missing,missing
fees=Document(R/'ДОДАТКИ/06_Деталізація_комісій.docx').tables[0]
assert len(fees.rows)==97
total=sum(Decimal(row.cells[3].text) for row in fees.rows[1:])
assert total==Decimal('7170.44'),total
for f in files[:4]:
    s=(R/f['txt']).read_text(encoding='utf-8')
    assert 'Адреса реєстрації' in s
    for prohibited in ['фактично проживаю','перебуваю в іншому','місце фактичного проживання','фактична адреса']:
        assert prohibited not in s.lower(),(f['number'],prohibited)
    assert '[вкажіть' not in s.lower()

deliverables=[road,R/'README.md',R/'ДЛЯ_СЕБЕ/08_Повний_аудит.md',R/'ДОДАТКИ/Квитанція_7900097_09-07-2026.pdf',R/'ДОДАТКИ/Картка_руху_22-07-2026.pdf']
for f in files:
    for kind in ['docx','pdf','txt']:deliverables.append(R/f[kind])
archive=R.parent/'ПАКЕТ_К_05-10-2026.zip'
with ZipFile(archive,'w',compression=ZIP_DEFLATED) as z:
    for p in deliverables:z.write(p,Path(R.name)/p.relative_to(R))
with ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(deliverables)==26
    assert not any(n.lower().endswith(('.pfx','.p7s','.py','.ps1','.png')) for n in z.namelist())
checks={'documents':len(files),'rendered_pages':sum(f['pages'] for f in files),'commission_rows':len(fees.rows)-1,'commission_total':str(total),'local_links_ok':True,'actual_location_not_disclosed_in_court_texts':True,'archive_files':len(deliverables),'archive_crc_ok':True,'archive_excludes_keys_signatures_scripts_and_qa':True,'submitted_to_court':False,'files':[{'path':str(p.relative_to(R)),'sha256':sha256(p.read_bytes()).hexdigest()} for p in deliverables]}
(R/'qa/final_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in checks.items() if k!='files'},ensure_ascii=False,indent=2))
print(archive)
