"""Окончательный пересчёт денежных данных по делу 127/20805/26 (третья независимая проверка, 02.10.2026).

Источник: CSV-копии расчёта (349 строк) и выписки (697 операций) из приложений банка к иску.
Соответствие CSV исходному PDF проверено аудитом 01.10.2026 (audit/2026-10-01/extraction_checks.json).
Только стандартная библиотека Python. Запуск из любой папки:
    python recompute.py
Результаты пишутся в папку ./результаты рядом со скриптом. Скрипт ничего не меняет в исходных данных.
"""
import csv
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
ABANK = HERE.parents[1]
SRC = ABANK / 'База доказів от банка (Додатки до позову)'
OUT = HERE / 'результаты'
OUT.mkdir(exist_ok=True)
Q = D('0.01')


def q(x):
    return x.quantize(Q, ROUND_HALF_UP)


def read(name):
    with open(SRC / name, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))
    return rows[0], [r for r in rows[1:] if r]


def write_csv(name, header, rows):
    with open(OUT / name, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ---------- загрузка ----------
_, LR = read('rozrahunok_ledger.csv')
# 0 дата,1 дни,2 текущее тело,3 льготное сальдо,4 просроченное тело,5 ставка,6 ставка проср.,
# 7 начислено,8 текущие проценты,9 просроченные проценты,10 штраф,11 погашение,12 общий остаток
L = [[date.fromisoformat(r[0])] + [D(v) for v in r[1:]] for r in LR]
_, TR = read('card_transactions.csv')
# выписка в файле от новых к старым; разворачиваем
T = []
for r in reversed(TR):
    T.append({'dt': r[0].replace('\n', ' '), 'desc': ' '.join(r[2].split()), 'amt': D(r[4]),
              'op_amt': D(r[5]), 'fee': D(r[8]), 'bal': D(r[10])})

R = {'source_rows': {'ledger': len(L), 'statement': len(T)}}

# ---------- 1. целостность ----------
breaks = sum(1 for older, newer in zip(T, T[1:]) if older['bal'] + newer['amt'] != newer['bal'])
opening = T[0]['bal'] - T[0]['amt']
days_bad = sum(1 for p, c in zip(L, L[1:]) if c[1] != (c[0] - p[0]).days)
own_funds_rows = sum(1 for x in L if x[2] + x[4] + x[8] + x[9] + x[10] != x[12])
R['integrity'] = {
    'statement_continuity_breaks': breaks,
    'statement_opening_balance': str(opening),
    'ledger_days_column_mismatches': days_bad,
    'ledger_rows_with_positive_own_funds (не ошибки)': own_funds_rows,
    'ledger_final_total': str(L[-1][12]),
    'statement_final_balance_2026-06-01': str(T[-1]['bal']),
}

# ---------- 2. классификация операций ----------
def cls(t):
    d = t['desc']
    if 'Списання відсотків' in d:
        return 'проценты_списание'
    if 'Розстрочка миттєва' in d:
        return 'рассрочка_мгновенная_платёж'
    if 'Розстрочка з виписки' in d:
        return 'рассрочка_из_выписки_зачисление' if t['amt'] > 0 else 'рассрочка_из_выписки_платёж'
    if d == 'Abnk':
        return 'зачисление_Abnk (предп. рассрочка мгновенная)'
    if t['amt'] > 0 and d.startswith('Скасування'):
        return 'отмена_покупки'
    if t['amt'] > 0 and d.startswith('Повернення'):
        return 'возврат_неуспешного_перевода'
    if t['amt'] > 0:
        return 'собственный_взнос_или_входящий_перевод'
    return 'траты_клиента'

groups = defaultdict(lambda: [0, D(0), D(0)])
rows = []
for t in T:
    k = cls(t)
    groups[k][0] += 1
    groups[k][1] += t['amt']
    groups[k][2] += t['fee']
    rows.append([t['dt'], t['desc'], str(t['amt']), str(t['fee']), str(t['bal']), k])
write_csv('операции_классифицированы.csv', ['дата_время', 'описание', 'сумма', 'комиссия', 'остаток', 'класс'], rows)
R['groups'] = {k: {'n': v[0], 'sum': str(v[1]), 'fees_inside': str(v[2])} for k, v in sorted(groups.items())}
credits = sum(t['amt'] for t in T if t['amt'] > 0)
debits = sum(t['amt'] for t in T if t['amt'] < 0)
R['totals'] = {
    'зачисления_всего': str(credits), 'списания_всего': str(debits),
    'комиссии_колонка': str(sum(t['fee'] for t in T)),
    'проценты_списано_по_выписке': str(-groups['проценты_списание'][1]),
    'погашения_по_расчёту': str(sum(x[11] for x in L)),
    'начислено_по_колонке_расчёта': str(-sum(x[7] for x in L)),
}

# ---------- 3. разложение долга на 01.06.2026 ----------
spend = -groups['траты_клиента'][1]
own = groups['собственный_взнос_или_входящий_перевод'][1]
refunds = groups['отмена_покупки'][1] + groups['возврат_неуспешного_перевода'][1]
interest = -groups['проценты_списание'][1]
inst_debits = -(groups['рассрочка_мгновенная_платёж'][1] + groups['рассрочка_из_выписки_платёж'][1])
inst_credits = groups['рассрочка_из_выписки_зачисление'][1] + groups['зачисление_Abnk (предп. рассрочка мгновенная)'][1]
net_real = spend - own - refunds - opening
dec = {
    'траты_клиента_с_комиссиями': str(spend),
    'собственные_взносы_и_входящие_переводы': str(own),
    'возвраты_и_отмены': str(refunds),
    'входящее_сальдо (комиссии неуспешных переводов, возвращены позже)': str(-opening),
    'чистые_деньги_банка_у_клиента': str(net_real),
    'проценты_списанные': str(interest),
    'рассрочки_списано': str(inst_debits),
    'рассрочки_зачислено': str(inst_credits),
    'рассрочки_чистая_стоимость': str(inst_debits - inst_credits),
    'итого': str(net_real + interest + inst_debits - inst_credits),
    'долг_по_выписке_01.06.2026': str(-T[-1]['bal']),
    'проценты_1-11.06.2026_в_иске': str(-(L[-1][12] - T[-1]['bal'])),
    'цена_иска': str(-L[-1][12]),
}
assert D(dec['итого']) == D(dec['долг_по_выписке_01.06.2026']), 'разложение не сходится'
R['decomposition_2026-06-01'] = dec

# ---------- 4. объяснённые расхождения расчёта и выписки ----------
lp = defaultdict(D)
for x in L:
    lp[x[0].isoformat()] += x[11]
sc = defaultdict(D)
for t in T:
    if t['amt'] > 0:
        sc[t['dt'][:10]] += t['amt']
mism = {d: str(sc.get(d, D(0)) - lp.get(d, D(0))) for d in sorted(set(lp) | set(sc)) if lp.get(d, D(0)) != sc.get(d, D(0))}
feb = [x for x in L if x[0].isoformat() in ('2021-02-28', '2021-03-01')]
R['explained_differences'] = {
    '711.77': {
        'сумма': str(sum(D(v) for v in mism.values())),
        'по_датам': mism,
        'объяснение': 'Отмены покупок («Скасування …»): расчёт уменьшает на них траты, а не считает погашением. Денежный эффект 0.',
    },
    '41.12': {
        'входящее_сальдо': str(opening),
        'возвраты_комиссий': [[t['dt'], t['desc'], str(t['amt'])] for t in T if 'Повернення комісії' in t['desc']],
        'объяснение': 'Две комиссии за неуспешные переводы (21,12 + 20,00) не показаны в выписке отдельными строками и дают входящее сальдо −41,12; затем они возвращены. Денежный эффект 0.',
    },
    '805.00': {
        'тело_28.02.2021': str(feb[0][2]), 'погашение_01.03.2021': str(feb[1][11]), 'тело_01.03.2021': str(feb[1][2]),
        'проверка': str(feb[0][2] + feb[1][11] - D('805')),
        'объяснение': 'Проценты за февраль 2021 (805) учтены в «теле», а не в колонке процентов; в тот же день внесено 4 200 > 805, итоговый остаток тот же. Денежный эффект 0.',
    },
}
assert D(R['explained_differences']['805.00']['проверка']) == feb[1][2]

# ---------- 5. проценты: независимая модель по базовой ставке ----------
model = defaultdict(D)
for p, c in zip(L, L[1:]):
    base = -(p[2] + p[4])
    d = p[0] + timedelta(days=1)
    while d <= c[0]:
        model[(d.year, d.month)] += base * p[5] / D(36500)
        d += timedelta(days=1)
bank = defaultdict(D)
for x in L:
    bank[(x[0].year, x[0].month)] += -x[7]
mrows = []
for k in sorted(set(model) | set(bank)):
    mrows.append([f'{k[0]}-{k[1]:02d}', str(bank[k]), str(q(model[k])), str(q(bank[k] - model[k]))])
write_csv('проценты_по_месяцам.csv', ['месяц', 'банк_начислил', 'модель_базовая_ставка', 'разница'], mrows)
since = [r for r in mrows if '2024-03' <= r[0] <= '2026-05']
R['interest'] = {
    'макс_отклонение_2024-03..2026-05_грн': str(max(abs(D(r[3])) for r in since)),
    'двойная_ставка_применялась': False,
    'начислено_в_период_44.4%': str(sum(D(r[1]) for r in mrows if r[0] <= '2021-05')),
    'излишек_если_согласована_только_40.8%': str(q(sum(D(r[1]) for r in mrows if r[0] <= '2021-05') * (1 - D('40.8') / D('44.4')))),
    'неуплачено_в_иске': str(-(L[-1][8] + L[-1][9])),
}
june = -(L[-1][8]) + L[-2][8]  # прирост текущих процентов 01.06 → 11.06 (в колонке начислений не показан)
charged = -sum(x[7] for x in L) + D('805') + june
R['interest']['начислено_всего (колонка + 805 февраля 2021 + июнь 2026)'] = str(charged)
R['interest']['уплачено_процентов_всего'] = str(charged - D(R['interest']['неуплачено_в_иске']))

# ---------- 6. рассрочки ----------
inst = [[t['dt'], t['desc'], str(t['amt']), str(t['op_amt']), str(t['fee'])] for t in T
        if 'Розстрочка' in t['desc'] or t['desc'] == 'Abnk']
write_csv('рассрочки_операции.csv', ['дата_время', 'описание', 'сумма_по_карте', 'сумма_операции', 'комиссия'], inst)
stmt_pay = [t for t in T if 'Розстрочка з виписки' in t['desc'] and t['amt'] < 0]
R['installments'] = {
    'из_выписки_зачислено': [[t['dt'], str(t['amt'])] for t in T if 'Розстрочка з виписки' in t['desc'] and t['amt'] > 0],
    'из_выписки_платежей': len(stmt_pay),
    'из_выписки_списано_всего': str(-sum(t['amt'] for t in stmt_pay)),
    'из_выписки_в_т.ч._комиссии': str(sum(t['fee'] for t in stmt_pay)),
    'из_выписки_переплата_сверх_полученного': str(-sum(t['amt'] for t in stmt_pay) - groups['рассрочка_из_выписки_зачисление'][1]),
    'мгновенная_платежей': groups['рассрочка_мгновенная_платёж'][0],
    'мгновенная_списано': str(-groups['рассрочка_мгновенная_платёж'][1]),
    'мгновенная_зачисление_Abnk_2020-12-01': str(groups['зачисление_Abnk (предп. рассрочка мгновенная)'][1]),
    'списано_по_рассрочкам_после_01.08.2025': str(-sum(t['amt'] for t in stmt_pay if t['dt'] >= '2025-08-01')),
}

# ---------- 7. просрочка и правило 91-го дня ----------
start = None
for x in L:
    od = x[4] != 0 or x[9] != 0
    if od and start is None:
        start = x[0]
    if not od:
        start = None
R['overdue'] = {
    'непрерывная_просрочка_с': start.isoformat(),
    '91-й_день': (start + timedelta(days=90)).isoformat(),
    'текущее_тело_в_расчёте_на_11.06.2026': str(-L[-1][2]),
    'просроченное_тело_на_11.06.2026': str(-L[-1][4]),
    'вывод': 'Банк до иска не перевёл всё тело в просроченное, хотя просрочка длится дольше 90 дней.',
}
write_csv('просрочка_по_строкам.csv', ['дата', 'текущее_тело', 'просроченное_тело', 'текущие_проценты', 'просроченные_проценты', 'погашение', 'всего'],
          [[x[0].isoformat(), str(x[2]), str(x[4]), str(x[8]), str(x[9]), str(x[11]), str(x[12])] for x in L])

# ---------- 8. рост долга с 01.01.2025 ----------
g = {'взносы': D(0), 'проценты': D(0), 'рассрочки': D(0), 'покупки': D(0)}
for t in T:
    if t['dt'] < '2025-01-01':
        continue
    k = cls(t)
    if k == 'собственный_взнос_или_входящий_перевод':
        g['взносы'] += t['amt']
    elif k == 'проценты_списание':
        g['проценты'] += -t['amt']
    elif k.startswith('рассрочка') and t['amt'] < 0:
        g['рассрочки'] += -t['amt']
    elif k == 'траты_клиента':
        g['покупки'] += -t['amt']
bal_2024 = [t['bal'] for t in T if t['dt'] < '2025-01-01'][-1]
R['growth_since_2025'] = {k: str(v) for k, v in g.items()}
R['growth_since_2025']['остаток_на_конец_2024'] = str(-bal_2024)
R['growth_since_2025']['остаток_на_01.06.2026'] = str(-T[-1]['bal'])

# ---------- 9. комиссии ----------
crow = [[t['dt'], t['desc'], str(t['fee']), 'Розстрочка' if 'Розстрочка' in t['desc'] else 'прочие'] for t in T if t['fee']]
write_csv('комиссии_96.csv', ['дата_время', 'описание', 'комиссия', 'категория'], crow)
R['commissions'] = {'n': len(crow), 'total': str(sum(D(r[2]) for r in crow)),
                    'rozstrochka_n': sum(1 for r in crow if r[3] == 'Розстрочка'),
                    'rozstrochka_total': str(sum(D(r[2]) for r in crow if r[3] == 'Розстрочка'))}

# ---------- 10. деньги и сроки ----------
claim = -L[-1][12]
fee = D('2662.40')
pm = q(fee / D('0.8'))  # минимальный сбор = 1 прожиточный минимум × 0,8 (электронная подача)
body = -(L[-1][2] + L[-1][4])
R['money'] = {
    'цена_иска': str(claim), 'сбор_банка': str(fee), 'итого_известных_требований': str(claim + fee),
    'тело': str(body), 'проценты': str(-(L[-1][8] + L[-1][9])),
    'прожиточный_минимум_2026_выведен_из_сбора': str(pm),
    'апелляционный_сбор_оценка (150% × ПМ × 0,8)': str(q(pm * D('1.5') * D('0.8'))),
    'гипотетически_проценты_40.8%_в_месяц': str(q(body * D('0.408') / 12)),
    'гипотетически_проценты_40.8%_в_год': str(q(body * D('0.408'))),
}
served = date(2026, 6, 27)
R['deadlines'] = {
    'ухвала_25.06_доставлена': '2026-06-27 02:25 (суббота)',
    'срок_отзыва_если_от_27.06': (served + timedelta(days=15)).isoformat() + ' (воскресенье → понедельник 2026-07-13)',
    'срок_отзыва_если_вручение_29.06': (date(2026, 6, 29) + timedelta(days=15)).isoformat(),
    'документы_поданы_в_суд': '2026-07-29',
    'опоздание_дней': f'{(date(2026, 7, 29) - date(2026, 7, 14)).days}–{(date(2026, 7, 29) - date(2026, 7, 13)).days}',
}

(OUT / 'результаты.json').write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps(R, ensure_ascii=False, indent=2))
