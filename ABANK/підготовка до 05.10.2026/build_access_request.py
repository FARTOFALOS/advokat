from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

OUT=Path(__file__).resolve().parent
doc=Document()
sec=doc.sections[0]
sec.page_width=Cm(21);sec.page_height=Cm(29.7)
sec.top_margin=Cm(1.8);sec.bottom_margin=Cm(1.8)
sec.left_margin=Cm(2.5);sec.right_margin=Cm(1.8)
sec.footer_distance=Cm(.8)
normal=doc.styles['Normal'];normal.font.name='Times New Roman';normal.font.size=Pt(12)
normal.font.color.rgb=RGBColor(0,0,0)
normal.paragraph_format.line_spacing=1.08
normal.paragraph_format.space_after=Pt(6)
normal.paragraph_format.widow_control=True
for name in ['Title','Subtitle','Heading 1']:
    style=doc.styles[name];style.font.name='Times New Roman';style.font.color.rgb=RGBColor(0,0,0)
doc.styles['Title'].font.size=Pt(14);doc.styles['Title'].font.bold=True
doc.styles['Title'].paragraph_format.space_after=Pt(3)
doc.styles['Subtitle'].font.size=Pt(12);doc.styles['Subtitle'].font.italic=False
lang=OxmlElement('w:lang');lang.set(qn('w:val'),'uk-UA');normal.element.get_or_add_rPr().append(lang)
alltext=[]
def p(text,bold=False,align=None,header=False,keep=False,style=None):
    para=doc.add_paragraph(style=style)
    run=para.add_run(text);run.bold=bold
    if align is not None:para.alignment=align
    if header:
        para.paragraph_format.left_indent=Cm(7.3)
        para.paragraph_format.space_after=Pt(0)
        para.paragraph_format.line_spacing=1.0
        run.font.size=Pt(11)
    para.paragraph_format.keep_with_next=keep
    alltext.append(text)
    return para

for text,bold in [
('До Вінницького міського суду Вінницької області',True),
('21050, м. Вінниця, вул. Грушевського, 17',False),
('Справа № 127/20805/26',True),
('Провадження № 2/127/5742/26',False),
('Суддя Бессараб Н. М.',False),
('',False),
('Відповідач: Подольський Андрій Юрійович',True),
('РНОКПП 3138306873',False),
('Адреса реєстрації: 21022, м. Вінниця,',False),
('вул. Тарногородського, буд. 48А, кв. 90',False),
('Електронний кабінет ЄСІТС зареєстровано',False),
('Ел. пошта: andrii.podolskyi@gmail.com',False),
('Тел.: +380930808888',False),
('',False),
('Позивач: АТ «АКЦЕНТ-БАНК»',True),
('ЄДРПОУ 14360080',False),
('49074, м. Дніпро, вул. Батумська, 11',False),
('Електронний кабінет ЄСІТС зареєстровано',False),
]:p(text,bold=bold,header=True,keep=True)

title=p('КЛОПОТАННЯ',bold=True,align=WD_ALIGN_PARAGRAPH.CENTER,style='Title',keep=True)
title.paragraph_format.space_before=Pt(12)
p('про ознайомлення з відповіддю на відзив та її додатками\nі забезпечення можливості подати заперечення',align=WD_ALIGN_PARAGRAPH.CENTER,style='Subtitle',keep=True)

paragraphs=[
'У провадженні суду перебуває справа № 127/20805/26 за позовом АТ «АКЦЕНТ-БАНК» до мене про стягнення заборгованості. Судове засідання призначено на 05.10.2026 о 10:00.',
'Згідно з реєстраційною карткою вхідного документа, 27.07.2026 за № 74171/26-Вх суд зареєстрував відповідь представника позивача на відзив у цій справі. У картці зазначено обсяг 6 аркушів та позначку «пошта».',
'Станом на дату цього клопотання зазначеної відповіді на відзив та доданих до неї документів я фактично не отримав, їхнього змісту не знаю та копій не маю. Позначка про поштове надходження документа до суду сама по собі не встановлює обставин направлення та вручення копії мені. Прошу перевірити відповідні докази, якщо вони містяться у справі.',
'Ухвалою від 25.06.2026 встановлено триденний строк для подання заперечень із дня отримання відповіді на відзив. Для підготовки змістовних заперечень необхідно ознайомитися з повним текстом відповіді та всіма її додатками.',
'Пункт 1 частини першої статті 43 ЦПК України передбачає право учасника справи ознайомлюватися з матеріалами справи та робити з них копії. Частина четверта статті 179 ЦПК України передбачає можливість відповідача надати заперечення завчасно до початку розгляду справи по суті. Маю зареєстрований електронний кабінет ЄСІТС та прошу забезпечити доступ до зазначених матеріалів через нього.',
'Керуючись статтями 12, 14, 43, 178–180, 182, 183 ЦПК України,',
]
for t in paragraphs:p(t)
p('ПРОШУ СУД',bold=True,align=WD_ALIGN_PARAGRAPH.CENTER,keep=True)
requests=[
'Надати мені можливість ознайомитися з повним текстом відповіді позивача на відзив, зареєстрованої 27.07.2026 за № 74171/26-Вх, та всіма доданими до неї документами, забезпечивши доступ до їх електронних копій у моєму електронному кабінеті ЄСІТС.',
'Надати можливість ознайомитися з наявними у справі доказами направлення та вручення мені зазначеної відповіді й додатків, у тому числі поштовими документами або відомостями про електронну доставку, та забезпечити доступ до їх копій у моєму електронному кабінеті.',
'Після надання повного комплекту документів забезпечити мені можливість подати заперечення протягом трьох днів із дня їх отримання відповідно до ухвали від 25.06.2026. Якщо суд вважатиме необхідним окремо вирішити питання процесуального строку, прошу надати достатній строк для заперечень з урахуванням фактичних обставин отримання документів.',
'Якщо до засідання 05.10.2026 ознайомлення з цими матеріалами та підготовка заперечень у зазначений строк будуть неможливими, прошу відкласти розгляд справи по суті для забезпечення такої можливості.',
]
for i,t in enumerate(requests,1):
    para=p(f'{i}. {t}')
    para.paragraph_format.left_indent=Cm(.6)
    para.paragraph_format.first_line_indent=Cm(-.6)
p('Додаткові документи не додаються. Реєстраційна картка та ухвала, на які посилаюся, містяться в матеріалах справи.')
p('01 жовтня 2026 року')
p('Подольський Андрій Юрійович                         __________________')

f=sec.footer.paragraphs[0];f.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=f.add_run();fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');r._r.addnext(fld)
doc.core_properties.title='Клопотання про ознайомлення з відповіддю на відзив'
doc.core_properties.author='Подольський Андрій Юрійович'
doc.core_properties.subject='Справа 127/20805/26'
doc.core_properties.comments=''
name='Клопотання про ознайомлення з відповіддю банку — 01.10.2026'
doc.save(OUT/(name+'.docx'))
(OUT/(name+'.txt')).write_text('\n\n'.join(alltext),encoding='utf-8')
print(OUT/(name+'.docx'))
