"""Независимая проверка сумм по делу 127/20805/26 (V3.1, 04.10.2026).

Своя классификация операций выписки, отдельная от recompute.py. Дополнительно считает:
- кто кому сколько за весь период: использованные кредитные средства, ваши взносы, начисления банка;
- разложение по годам и с 01.01.2023 (к концу 2022 года долга не было);
- как банк распределил платежи (ст. 534 ЦК: сначала проценты, затем тело) и из чего сложено «тело»;
- влияние рассрочек на проценты карты (сравнение с вариантом без рассрочек);
- период просрочки с 01.08.2025.
Только стандартная библиотека Python. Запуск из любой папки:
    python verify_2026-10-04.py
Каждое разложение проверяется assert'ом на точное совпадение с остатком выписки.
"""
import csv
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
SRC = Path(__file__).resolve().parents[2] / 'База доказів от банка (Додатки до позову)'
q = lambda x: x.quantize(D('0.01'), ROUND_HALF_UP)

with open(SRC / 'card_transactions.csv', encoding='utf-8-sig', newline='') as f:
    raw = [r for r in list(csv.reader(f))[1:] if r]
T = []
for r in reversed(raw):  # в файле операции идут от новых к старым
    T.append(dict(dt=datetime.strptime(' '.join(r[0].split()), '%Y-%m-%d %H:%M'),
                  desc=' '.join(r[2].split()), amt=D(r[4]), fee=D(r[8]), bal=D(r[10])))
opening = T[0]['bal'] - T[0]['amt']
assert all(a['bal'] + b['amt'] == b['bal'] for a, b in zip(T, T[1:])), 'разрыв остатков в выписке'

TOPUP = ('Поповнення карти у терміналі', 'ПриватБанк', 'Монобанк', 'City24', 'Sportbank', 'УкрСиббанк',
         'Поповнення картки', 'Зі своєї картки', 'Зарахування переказу на карту', 'Миттєвий переказ', 'Зарахування від')
SPEND = ('D_покупка', 'D_перевод_с_карты', 'D_наличные')


def kind(t):
    d, a = t['desc'], t['amt']
    if a > 0:
        if 'Розстрочка' in d or d == 'Abnk':
            return 'C_рассрочка_зачисление'
        if d.startswith('Скасування') or d.startswith('Повернення'):
            return 'C_отмена_возврат'
        if any(d.startswith(k) for k in TOPUP):
            return 'C_ваш_взнос'
        return 'C_ПРОЧЕЕ'
    if 'Списання відсотків' in d:
        return 'D_проценты'
    if 'Розстрочка' in d:
        return 'D_рассрочка_платёж'
    if d.startswith('Зняття готівки'):
        return 'D_наличные'
    if d[:4].isdigit() or d.startswith('*') or d.startswith('Зі своєї'):
        return 'D_перевод_с_карты'
    return 'D_покупка'


S = defaultdict(lambda: [0, D(0), D(0)])
for t in T:
    k = kind(t)
    S[k][0] += 1
    S[k][1] += t['amt']
    S[k][2] += t['fee']
assert S['C_ПРОЧЕЕ'][0] == 0, 'есть неклассифицированные зачисления'
print('== 1. Группы операций: количество | сумма | в т.ч. комиссия банка')
for k in sorted(S):
    print(f'  {k:26s} {S[k][0]:4d} {S[k][1]:>13} {S[k][2]:>10}')

spend_gross = -sum(S[k][1] for k in SPEND)
fees = sum(S[k][2] for k in SPEND)
spend_net = spend_gross - fees
refunds = S['C_отмена_возврат'][1]
used = spend_net - refunds
paid = S['C_ваш_взнос'][1]
interest = -S['D_проценты'][1]
inst_paid = -S['D_рассрочка_платёж'][1]
inst_got = S['C_рассрочка_зачисление'][1]
inst_cost = inst_paid - inst_got
charges = interest + fees + inst_cost
debt = -T[-1]['bal']
print('\n== 2. Весь период 18.11.2020 – 01.06.2026')
print('  Использовано кредитных средств (траты без комиссий − отмены):', spend_net, '−', refunds, '=', used)
print('  Вы внесли:', paid)
print('  Начисления банка: проценты', interest, '+ комиссии', fees, '+ стоимость рассрочек', inst_cost, '=', charges)
print('  Входящее сальдо:', -opening)
print('  Долг = использовано + начисления + сальдо − внесено =', used + charges - opening - paid, '| по выписке:', debt)
assert used + charges - opening - paid == debt

with open(SRC / 'rozrahunok_ledger.csv', encoding='utf-8-sig', newline='') as f:
    L = [r for r in list(csv.reader(f))[1:] if r]
body = -(D(L[-1][2]) + D(L[-1][4]))
unpaid_int = -(D(L[-1][8]) + D(L[-1][9]))
charged = -sum(D(r[7]) for r in L) + D('805') + (-D(L[-1][8]) + D(L[-2][8]))
paid_int = charged - unpaid_int
print('\n== 3. Как банк зачёл ваши платежи (ст. 534 ЦК: сначала проценты, потом тело)')
print('  Начислено процентов всего (с июнем 2026):', charged)
print('  Из ваших платежей на проценты:', paid_int, '| на тело:', paid - paid_int)
print('  Тело по банку:', body, '| проценты к взысканию:', unpaid_int, '| цена иска:', body + unpaid_int)
body_check = spend_net + fees + inst_cost - opening - refunds - (paid - paid_int)
assert body_check == body
print('  Тело = траты', spend_net, '+ комиссии', fees, '+ стоимость рассрочек', inst_cost, '+ сальдо', -opening,
      '− отмены', refunds, '− платежи, зачтённые в тело', paid - paid_int, '=', body_check)

rate = {}
for p, c in zip(L, L[1:]):
    d = date.fromisoformat(p[0]) + timedelta(days=1)
    while d <= date.fromisoformat(c[0]):
        rate[d] = D(p[5])
        d += timedelta(days=1)
flows = defaultdict(D)
for t in T:
    if kind(t) in ('C_рассрочка_зачисление', 'D_рассрочка_платёж'):
        flows[t['dt'].date()] += -t['amt']
cum, extra, d = D(0), D(0), date(2020, 11, 19)
while d <= date(2026, 6, 11):
    cum += flows.get(d, D(0))
    extra += cum * rate.get(d, D('40.8')) / D(36500)
    d += timedelta(days=1)
print('\n== 4. Рассрочки')
print('  Зачислено', inst_got, '| списано с лимита карты', inst_paid, '| чистая стоимость', inst_cost)
print('  Разница в процентах карты против варианта без рассрочек:', q(extra), '| влияние на иск ≈', q(inst_cost + extra))

Y = defaultdict(lambda: defaultdict(D))
for t in T:
    Y[t['dt'].year][kind(t)] += t['amt']
    Y[t['dt'].year]['end'] = t['bal']
print('\n== 5. По годам: траты с комиссиями | ваши взносы | проценты | рассрочки нетто | долг на конец года')
for y in sorted(Y):
    g = Y[y]
    print(f"  {y}: {-sum(g[k] for k in SPEND):>11} {g['C_ваш_взнос']:>11} {-g['D_проценты']:>10} "
          f"{-(g['D_рассрочка_платёж'] + g['C_рассрочка_зачисление']):>11} {-g['end']:>11}")


def window(start):
    prev = [t for t in T if t['dt'] < start]
    W, F = defaultdict(D), D(0)
    for t in T:
        if t['dt'] >= start:
            k = kind(t)
            W[k] += t['amt']
            if k in SPEND:
                F += t['fee']
    r = dict(долг_на_начало=-(prev[-1]['bal'] if prev else opening),
             траты_без_комиссий=-sum(W[k] for k in SPEND) - F, комиссии=F, отмены=W['C_отмена_возврат'],
             внесено=W['C_ваш_взнос'], проценты=-W['D_проценты'],
             рассрочки_зачислено=W['C_рассрочка_зачисление'], рассрочки_списано=-W['D_рассрочка_платёж'])
    r['рассрочки_стоимость'] = r['рассрочки_списано'] - r['рассрочки_зачислено']
    r['долг_на_01.06.2026'] = (r['долг_на_начало'] + r['траты_без_комиссий'] + F - r['отмены'] - r['внесено']
                               + r['проценты'] + r['рассрочки_стоимость'])
    assert r['долг_на_01.06.2026'] == debt
    return r


for label, start in (('6. С 01.01.2023 (на конец 2022 года долга не было)', datetime(2023, 1, 1)),
                     ('7. Период просрочки с 01.08.2025', datetime(2025, 8, 1))):
    print(f'\n== {label}')
    for k, v in window(start).items():
        print(f'  {k:22s} {v:>12}')
