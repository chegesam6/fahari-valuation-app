"""
========================================================
SAVANNA CAPITAL PARTNERS — VALUATION ENGINE v1.0
========================================================
Analyst: Byron S.M. Chege
Kenyatta University | Nairobi, Kenya
========================================================
Covers: CAPM → WACC → DCF → Sensitivity → LBO → CCA
========================================================
"""

from tabulate import tabulate
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
import datetime
import os
import sys

# ============================================================
# COLOUR CODES FOR TERMINAL OUTPUT
# ============================================================
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
GOLD   = "\033[33m"

def fmt(n):
    """Format number as KSh with commas."""
    return f"KSh {n:,.2f}"

def pct(n):
    """Format number as percentage."""
    return f"{n*100:.2f}%"

def header(title):
    print(f"\n{GOLD}{'='*60}{RESET}")
    print(f"{BOLD}{GOLD}  {title}{RESET}")
    print(f"{GOLD}{'='*60}{RESET}")

def subheader(title):
    print(f"\n{BLUE}{'─'*60}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BLUE}{'─'*60}{RESET}")

# ============================================================
# CORE FINANCE FUNCTIONS
# ============================================================

def capm(rf, beta, rm):
    """
    Capital Asset Pricing Model
    r_e = r_f + Beta x (r_m - r_f)
    Returns cost of equity
    """
    return rf + beta * (rm - rf)

def wacc_calc(E, D, re, rd, t):
    """
    Weighted Average Cost of Capital
    WACC = (E/V x r_e) + (D/V x r_d x (1-t))
    Returns WACC as decimal
    """
    V = E + D
    return (E/V * re) + (D/V * rd * (1 - t))

def dcf_engine(fcfs, wacc, g, asking_price):
    """
    Full DCF Valuation Engine
    Returns dict with all components
    """
    n = len(fcfs)
    pv_fcfs = []
    for i, fcf in enumerate(fcfs, 1):
        pv = fcf / (1 + wacc)**i
        pv_fcfs.append(pv)

    sum_pv_fcfs = sum(pv_fcfs)
    tv = (fcfs[-1] * (1 + g)) / (wacc - g)
    pv_tv = tv / (1 + wacc)**n
    intrinsic_value = sum_pv_fcfs + pv_tv
    mos = (intrinsic_value - asking_price) / intrinsic_value * 100

    return {
        'fcfs': fcfs,
        'pv_fcfs': pv_fcfs,
        'sum_pv_fcfs': sum_pv_fcfs,
        'tv': tv,
        'pv_tv': pv_tv,
        'intrinsic_value': intrinsic_value,
        'asking_price': asking_price,
        'mos': mos,
        'n': n,
        'wacc': wacc,
        'g': g
    }

def sensitivity_engine(fcfs, wacc_range, g_range):
    """
    Sensitivity Analysis Engine
    Returns 2D matrix of intrinsic values
    """
    matrix = []
    for g in g_range:
        row = []
        for wacc in wacc_range:
            pv_fcfs = sum(fcf/(1+wacc)**t for t, fcf in enumerate(fcfs, 1))
            tv = (fcfs[-1] * (1+g)) / (wacc - g)
            pv_tv = tv / (1+wacc)**len(fcfs)
            iv = pv_fcfs + pv_tv
            row.append(iv)
        matrix.append(row)
    return matrix

def lbo_engine(purchase_price, equity_pct, debt_pct, interest_rate,
               annual_fcf, exit_multiple, hold_years=5, growing_fcf=None):
    """
    LBO Analysis Engine
    Returns dict with amortization schedule and returns
    """
    equity = purchase_price * equity_pct
    debt = purchase_price * debt_pct

    schedule = []
    opening_balance = debt

    for year in range(1, hold_years + 1):
        if growing_fcf:
            fcf = growing_fcf[year-1]
        else:
            fcf = annual_fcf

        interest = opening_balance * interest_rate
        principal = fcf - interest
        closing_balance = opening_balance - principal

        schedule.append({
            'year': year,
            'opening_balance': opening_balance,
            'fcf': fcf,
            'interest': interest,
            'principal': principal,
            'closing_balance': closing_balance
        })

        opening_balance = closing_balance

    remaining_debt = schedule[-1]['closing_balance']
    last_fcf = growing_fcf[-1] if growing_fcf else annual_fcf
    exit_value = exit_multiple * last_fcf
    eev = exit_value - remaining_debt
    moic = eev / equity
    irr = (moic ** (1/hold_years) - 1) * 100
    t_bill = 15.5
    outperformance = irr - t_bill

    return {
        'equity': equity,
        'debt': debt,
        'schedule': schedule,
        'exit_value': exit_value,
        'remaining_debt': remaining_debt,
        'eev': eev,
        'moic': moic,
        'irr': irr,
        't_bill': t_bill,
        'outperformance': outperformance,
        'interest_rate': interest_rate,
        'exit_multiple': exit_multiple,
        'purchase_price': purchase_price
    }

def cca_engine(comparables, target_ebitda, target_revenue, target_net_profit):
    """
    Comparable Company Analysis Engine
    comparables: list of dicts with market_cap, debt, cash, ebitda, revenue, net_profit
    Returns implied valuations
    """
    ev_ebitda_multiples = []
    ev_revenue_multiples = []
    pe_multiples = []

    for comp in comparables:
        ev = comp['market_cap'] + comp['debt'] - comp['cash']
        comp['ev'] = ev
        ev_ebitda = ev / comp['ebitda']
        ev_revenue = ev / comp['revenue']
        pe = comp['market_cap'] / comp['net_profit']
        comp['ev_ebitda'] = ev_ebitda
        comp['ev_revenue'] = ev_revenue
        comp['pe'] = pe
        ev_ebitda_multiples.append(ev_ebitda)
        ev_revenue_multiples.append(ev_revenue)
        pe_multiples.append(pe)

    sorted_ebitda = sorted(ev_ebitda_multiples)
    sorted_revenue = sorted(ev_revenue_multiples)
    sorted_pe = sorted(pe_multiples)
    n = len(comparables)

    median_ev_ebitda = sorted_ebitda[n//2] if n % 2 != 0 else (sorted_ebitda[n//2-1] + sorted_ebitda[n//2])/2
    median_ev_revenue = sorted_revenue[n//2] if n % 2 != 0 else (sorted_revenue[n//2-1] + sorted_revenue[n//2])/2
    median_pe = sorted_pe[n//2] if n % 2 != 0 else (sorted_pe[n//2-1] + sorted_pe[n//2])/2

    implied_ev_ebitda = median_ev_ebitda * target_ebitda
    implied_ev_revenue = median_ev_revenue * target_revenue
    implied_pe = median_pe * target_net_profit

    return {
        'comparables': comparables,
        'median_ev_ebitda': median_ev_ebitda,
        'median_ev_revenue': median_ev_revenue,
        'median_pe': median_pe,
        'implied_ev_ebitda': implied_ev_ebitda,
        'implied_ev_revenue': implied_ev_revenue,
        'implied_pe': implied_pe,
        'mean_implied': (implied_ev_ebitda + implied_ev_revenue + implied_pe) / 3
    }

def income_statement_engine(revenue, cogs, opex, da, debt, interest_rate, tax_rate, capex):
    """
    Income Statement Engine
    Returns full waterfall and FCF bridge
    """
    gross_profit = revenue - cogs
    ebitda = gross_profit - opex
    ebit = ebitda - da
    interest = debt * interest_rate
    ebt = ebit - interest
    tax = ebt * tax_rate
    net_profit = ebt - tax
    fcf = net_profit + da - capex

    gross_margin = gross_profit / revenue * 100
    ebitda_margin = ebitda / revenue * 100
    net_margin = net_profit / revenue * 100

    return {
        'revenue': revenue,
        'cogs': cogs,
        'gross_profit': gross_profit,
        'opex': opex,
        'ebitda': ebitda,
        'da': da,
        'ebit': ebit,
        'interest': interest,
        'ebt': ebt,
        'tax': tax,
        'net_profit': net_profit,
        'fcf': fcf,
        'gross_margin': gross_margin,
        'ebitda_margin': ebitda_margin,
        'net_margin': net_margin
    }

# ============================================================
# DISPLAY FUNCTIONS
# ============================================================

def display_capm_wacc(company_name, rf, beta, rm, E, D, rd, t):
    header(f"CAPM & WACC — {company_name}")

    re = capm(rf, beta, rm)
    wacc = wacc_calc(E, D, re, rd, t)

    subheader("CAPM — Cost of Equity")
    capm_data = [
        ["Risk Free Rate (r_f)", pct(rf)],
        ["Beta (β)", f"{beta:.2f}"],
        ["Market Return (r_m)", pct(rm)],
        ["Market Risk Premium (r_m - r_f)", pct(rm - rf)],
        ["β × Market Risk Premium", pct(beta * (rm - rf))],
        [f"{BOLD}Cost of Equity (r_e){RESET}", f"{BOLD}{GREEN}{pct(re)}{RESET}"],
    ]
    print(tabulate(capm_data, tablefmt="rounded_outline"))

    subheader("WACC — Weighted Average Cost of Capital")
    V = E + D
    wacc_data = [
        ["Total Equity (E)", fmt(E)],
        ["Total Debt (D)", fmt(D)],
        ["Total Value (V)", fmt(V)],
        ["Equity Weight (E/V)", pct(E/V)],
        ["Debt Weight (D/V)", pct(D/V)],
        ["Cost of Debt (r_d)", pct(rd)],
        ["Tax Rate (t)", pct(t)],
        ["After-tax Cost of Debt", pct(rd*(1-t))],
        ["Equity Component", pct(E/V * re)],
        ["Debt Component", pct(D/V * rd * (1-t))],
        [f"{BOLD}WACC{RESET}", f"{BOLD}{GREEN}{pct(wacc)}{RESET}"],
    ]
    print(tabulate(wacc_data, tablefmt="rounded_outline"))
    return re, wacc

def display_dcf(company_name, result):
    header(f"DCF VALUATION — {company_name}")

    subheader("Projected Free Cash Flows & Present Values")
    dcf_rows = []
    for i, (fcf, pv) in enumerate(zip(result['fcfs'], result['pv_fcfs']), 1):
        dcf_rows.append([f"Year {i}", fmt(fcf), pct(result['wacc']), fmt(pv)])
    dcf_rows.append(["", "", "Sum of PV FCFs", fmt(result['sum_pv_fcfs'])])
    print(tabulate(dcf_rows,
        headers=["Year", "FCF (KSh)", "Discount Rate", "PV of FCF"],
        tablefmt="rounded_outline"))

    subheader("Terminal Value")
    tv_data = [
        ["Year 5 FCF", fmt(result['fcfs'][-1])],
        ["Terminal Growth Rate (g)", pct(result['g'])],
        ["FCF5 × (1+g)", fmt(result['fcfs'][-1] * (1+result['g']))],
        ["WACC - g", pct(result['wacc'] - result['g'])],
        ["Terminal Value (TV)", fmt(result['tv'])],
        [f"PV of TV (discounted {result['n']} years)", fmt(result['pv_tv'])],
    ]
    print(tabulate(tv_data, tablefmt="rounded_outline"))

    subheader("Intrinsic Value & Deal Assessment")
    mos = result['mos']
    mos_colour = GREEN if mos > 0 else RED
    verdict_colour = GREEN if mos > 0 else RED
    verdict = "UNDERPRICED ✓" if mos > 0 else "OVERPRICED ✗"

    iv_data = [
        ["Sum of PV of FCFs", fmt(result['sum_pv_fcfs'])],
        ["PV of Terminal Value", fmt(result['pv_tv'])],
        [f"{BOLD}Intrinsic Value{RESET}", f"{BOLD}{GREEN}{fmt(result['intrinsic_value'])}{RESET}"],
        ["Asking Price", fmt(result['asking_price'])],
        ["Difference", fmt(result['intrinsic_value'] - result['asking_price'])],
        ["Margin of Safety", f"{mos_colour}{mos:.2f}%{RESET}"],
        [f"{BOLD}Verdict{RESET}", f"{BOLD}{verdict_colour}{verdict}{RESET}"],
    ]
    print(tabulate(iv_data, tablefmt="rounded_outline"))
    return result['intrinsic_value']

def display_sensitivity(company_name, matrix, wacc_range, g_range, asking_price):
    header(f"SENSITIVITY ANALYSIS — {company_name}")
    print(f"  Asking Price: {fmt(asking_price)}")
    print(f"  Green = Undervalued (IV > Asking Price)")
    print(f"  Red   = Overpriced  (IV < Asking Price)\n")

    headers = ["g \\ WACC"] + [f"{w:.0%}" for w in wacc_range]
    rows = []
    green_count = 0
    total = 0

    for i, g in enumerate(g_range):
        row = [f"g={g:.0%}"]
        for j, wacc in enumerate(wacc_range):
            iv = matrix[i][j]
            total += 1
            if iv >= asking_price:
                green_count += 1
                row.append(f"{GREEN}{iv:>16,.0f}{RESET}")
            else:
                row.append(f"{RED}{iv:>16,.0f}{RESET}")
        rows.append(row)

    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))

    all_values = [matrix[i][j] for i in range(len(g_range)) for j in range(len(wacc_range))]
    best = max(all_values)
    worst = min(all_values)
    best_g = g_range[next(i for i in range(len(g_range)) for j in range(len(wacc_range)) if matrix[i][j] == best)]
    best_wacc = wacc_range[next(j for i in range(len(g_range)) for j in range(len(wacc_range)) if matrix[i][j] == best)]

    print(f"\n  {GREEN}Best case:  {fmt(best)} (WACC={best_wacc:.0%}, g={best_g:.0%}){RESET}")
    print(f"  {RED}Worst case: {fmt(worst)}{RESET}")
    print(f"  {GREEN if green_count > total//2 else RED}{green_count} of {total} scenarios justify the asking price{RESET}")

def display_lbo(company_name, result):
    header(f"LBO ANALYSIS — {company_name}")

    subheader("Capital Structure")
    cap_data = [
        ["Purchase Price", fmt(result['purchase_price'])],
        ["Equity", fmt(result['equity']),
         f"{result['equity']/result['purchase_price']:.0%}"],
        ["Debt", fmt(result['debt']),
         f"{result['debt']/result['purchase_price']:.0%}"],
        ["Interest Rate", pct(result['interest_rate'])],
        ["Exit Multiple", f"{result['exit_multiple']}x FCF"],
    ]
    print(tabulate(cap_data,
        headers=["Item", "Amount", "Pct"],
        tablefmt="rounded_outline"))

    subheader("Amortization Schedule")
    sched_rows = []
    for s in result['schedule']:
        neg = s['principal'] < 0
        pr_str = f"{RED}{fmt(s['principal'])}{RESET}" if neg else fmt(s['principal'])
        sched_rows.append([
            s['year'],
            fmt(s['opening_balance']),
            fmt(s['fcf']),
            fmt(s['interest']),
            pr_str,
            fmt(s['closing_balance'])
        ])
    print(tabulate(sched_rows,
        headers=["Year", "Opening Bal", "FCF", "Interest", "Principal", "Closing Bal"],
        tablefmt="rounded_outline"))

    if any(s['principal'] < 0 for s in result['schedule']):
        print(f"  {RED}⚠ NEGATIVE AMORTIZATION DETECTED — interest exceeds FCF{RESET}")
        print(f"  {RED}  Debt is growing. Similar to interest-only mortgage bonds.{RESET}")

    subheader("Exit Returns")
    moic_colour = GREEN if result['moic'] >= 2 else (YELLOW if result['moic'] >= 1 else RED)
    irr_colour = GREEN if result['irr'] >= 20 else (YELLOW if result['irr'] >= result['t_bill'] else RED)
    verdict = "GOOD DEAL ✓" if result['irr'] >= result['t_bill'] and result['moic'] >= 1 else "BAD DEAL ✗"
    verdict_colour = GREEN if "GOOD" in verdict else RED

    exit_data = [
        ["Exit Value", fmt(result['exit_value'])],
        ["Remaining Debt", fmt(result['remaining_debt'])],
        [f"{BOLD}Exit Equity Value (EEV){RESET}",
         f"{BOLD}{fmt(result['eev'])}{RESET}"],
        ["Initial Equity Invested", fmt(result['equity'])],
        [f"{BOLD}MOIC{RESET}",
         f"{BOLD}{moic_colour}{result['moic']:.3f}x{RESET}"],
        [f"{BOLD}IRR{RESET}",
         f"{BOLD}{irr_colour}{result['irr']:.3f}%{RESET}"],
        ["Kenya T-Bill Benchmark", f"{result['t_bill']:.1f}%"],
        ["Outperformance vs T-Bill",
         f"{irr_colour}{result['outperformance']:+.3f}%{RESET}"],
        [f"{BOLD}Verdict{RESET}",
         f"{BOLD}{verdict_colour}{verdict}{RESET}"],
    ]
    print(tabulate(exit_data, tablefmt="rounded_outline"))

def display_income_statement(company_name, result):
    header(f"INCOME STATEMENT — {company_name}")

    is_data = [
        ["Revenue", fmt(result['revenue']), ""],
        ["Less: COGS", f"({fmt(result['cogs'])})", ""],
        ["GROSS PROFIT", fmt(result['gross_profit']),
         f"Margin: {result['gross_margin']:.2f}%"],
        ["Less: Operating Expenses", f"({fmt(result['opex'])})", ""],
        ["EBITDA", fmt(result['ebitda']),
         f"Margin: {result['ebitda_margin']:.2f}%"],
        ["Less: D&A", f"({fmt(result['da'])})", ""],
        ["EBIT (Operating Profit)", fmt(result['ebit']), ""],
        ["Less: Interest", f"({fmt(result['interest'])})", ""],
        ["EBT", fmt(result['ebt']), ""],
        ["Less: Tax", f"({fmt(result['tax'])})", ""],
        ["NET PROFIT", fmt(result['net_profit']),
         f"Margin: {result['net_margin']:.2f}%"],
    ]
    print(tabulate(is_data,
        headers=["Line Item", "Amount (KSh)", "Notes"],
        tablefmt="rounded_outline"))

    subheader("FCF Bridge")
    fcf_data = [
        ["Net Profit", fmt(result['net_profit'])],
        ["Add: Depreciation & Amortization", fmt(result['da'])],
        ["Less: Capital Expenditure", f"({fmt(result['da'])})"],
        [f"{BOLD}Free Cash Flow{RESET}", f"{BOLD}{GREEN}{fmt(result['fcf'])}{RESET}"],
    ]
    print(tabulate(fcf_data, tablefmt="rounded_outline"))

def display_cca(company_name, result, asking_price):
    header(f"COMPARABLE COMPANY ANALYSIS — {company_name}")

    subheader("Comparable Companies")
    comp_rows = []
    for c in result['comparables']:
        comp_rows.append([
            c['name'],
            fmt(c['ev']),
            fmt(c['ebitda']),
            fmt(c['revenue']),
            fmt(c['net_profit']),
            f"{c['ev_ebitda']:.2f}x",
            f"{c['ev_revenue']:.2f}x",
            f"{c['pe']:.2f}x",
        ])
    print(tabulate(comp_rows,
        headers=["Company", "EV", "EBITDA", "Revenue", "Net Profit",
                 "EV/EBITDA", "EV/Rev", "P/E"],
        tablefmt="rounded_outline"))

    subheader("Benchmark Multiples")
    mult_data = [
        ["Median EV/EBITDA", f"{result['median_ev_ebitda']:.2f}x"],
        ["Median EV/Revenue", f"{result['median_ev_revenue']:.2f}x"],
        ["Median P/E", f"{result['median_pe']:.2f}x"],
    ]
    print(tabulate(mult_data, tablefmt="rounded_outline"))

    subheader("Implied Valuations for Target")
    imp_data = [
        ["EV/EBITDA implied value",
         fmt(result['implied_ev_ebitda']),
         f"{result['median_ev_ebitda']:.2f}x × EBITDA"],
        ["EV/Revenue implied value",
         fmt(result['implied_ev_revenue']),
         f"{result['median_ev_revenue']:.2f}x × Revenue"],
        ["P/E implied value",
         fmt(result['implied_pe']),
         f"{result['median_pe']:.2f}x × Net Profit"],
        [f"{BOLD}Average implied value{RESET}",
         f"{BOLD}{GREEN}{fmt(result['mean_implied'])}{RESET}", ""],
        ["Asking Price", fmt(asking_price), ""],
        ["Difference", fmt(result['mean_implied'] - asking_price), ""],
    ]
    print(tabulate(imp_data,
        headers=["Method", "Implied Value", "Calculation"],
        tablefmt="rounded_outline"))

# ============================================================
# PDF REPORT GENERATOR
# ============================================================

def generate_pdf_report(company_name, analyst, dcf_result, lbo_result,
                        sensitivity_matrix, wacc_range, g_range,
                        cca_result, is_result, asking_price, filename):

    doc = SimpleDocTemplate(filename, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    title_s = ParagraphStyle('T', parent=styles['Title'], fontSize=18,
        textColor=colors.HexColor('#1a1a2e'), spaceAfter=4, alignment=1)
    sub_s = ParagraphStyle('S', parent=styles['Normal'], fontSize=10,
        textColor=colors.HexColor('#4a4a6a'), spaceAfter=4, alignment=1)
    gold_s = ParagraphStyle('G', parent=styles['Normal'], fontSize=12,
        textColor=colors.HexColor('#c9a84c'), spaceAfter=16, alignment=1,
        fontName='Helvetica-Bold')
    section_s = ParagraphStyle('SEC', parent=styles['Heading1'], fontSize=12,
        textColor=colors.white, backColor=colors.HexColor('#1a1a2e'),
        spaceBefore=12, spaceAfter=6, leftIndent=-10, rightIndent=-10, borderPad=6)
    body_s = ParagraphStyle('B', parent=styles['Normal'], fontSize=9,
        textColor=colors.HexColor('#1a1a2e'), spaceBefore=2, spaceAfter=2)
    note_s = ParagraphStyle('N', parent=styles['Normal'], fontSize=8,
        textColor=colors.HexColor('#666666'), alignment=1,
        fontName='Helvetica-Oblique')

    def pdf_table(data, col_widths=None, header=True):
        t = Table(data, colWidths=col_widths)
        style = [
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (0,1), (0,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cccccc')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('ROWBACKGROUNDS', (0,1 if header else 0), (-1,-1),
             [colors.HexColor('#f5f5f5'), colors.white]),
        ]
        if header:
            style += [
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ]
        t.setStyle(TableStyle(style))
        return t

    story = []
    date_str = datetime.datetime.now().strftime("%d %B %Y")

    # Cover
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("INVESTMENT MEMORANDUM", sub_s))
    story.append(Paragraph(company_name.upper(), title_s))
    story.append(Paragraph("SAVANNA CAPITAL PARTNERS", gold_s))
    story.append(Paragraph(f"Analyst: {analyst} | Date: {date_str}", sub_s))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=2,
        color=colors.HexColor('#c9a84c')))
    story.append(Spacer(1, 0.5*cm))

    # Key Metrics Summary
    story.append(Paragraph("KEY METRICS SUMMARY", section_s))
    iv = dcf_result['intrinsic_value']
    mos = dcf_result['mos']
    verdict = "OVERPRICED" if mos < 0 else "UNDERPRICED"
    summary_data = [
        ['Metric', 'Value', 'Metric', 'Value'],
        ['Intrinsic Value (DCF)', f"KSh {iv:,.0f}",
         'Asking Price', f"KSh {asking_price:,.0f}"],
        ['Margin of Safety', f"{mos:.2f}%",
         'Verdict', verdict],
        ['MOIC', f"{lbo_result['moic']:.3f}x",
         'IRR', f"{lbo_result['irr']:.2f}%"],
        ['CCA Mean Implied Value',
         f"KSh {cca_result['mean_implied']:,.0f}",
         'T-Bill Benchmark', f"{lbo_result['t_bill']:.1f}%"],
    ]
    story.append(pdf_table(summary_data,
        col_widths=[4.5*cm, 4.5*cm, 4.5*cm, 4.5*cm]))
    story.append(Spacer(1, 0.3*cm))

    # Income Statement
    story.append(Paragraph("INCOME STATEMENT", section_s))
    is_data = [
        ['Line Item', 'Amount (KSh)', 'Margin'],
        ['Revenue', f"{is_result['revenue']:,.0f}", ''],
        ['Less: COGS', f"({is_result['cogs']:,.0f})", ''],
        ['Gross Profit', f"{is_result['gross_profit']:,.0f}",
         f"{is_result['gross_margin']:.2f}%"],
        ['Less: OpEx', f"({is_result['opex']:,.0f})", ''],
        ['EBITDA', f"{is_result['ebitda']:,.0f}",
         f"{is_result['ebitda_margin']:.2f}%"],
        ['Less: D&A', f"({is_result['da']:,.0f})", ''],
        ['EBIT', f"{is_result['ebit']:,.0f}", ''],
        ['Less: Interest', f"({is_result['interest']:,.0f})", ''],
        ['EBT', f"{is_result['ebt']:,.0f}", ''],
        ['Less: Tax', f"({is_result['tax']:,.0f})", ''],
        ['Net Profit', f"{is_result['net_profit']:,.0f}",
         f"{is_result['net_margin']:.2f}%"],
        ['FCF (Net Profit + D&A - Capex)',
         f"{is_result['fcf']:,.0f}", ''],
    ]
    story.append(pdf_table(is_data, col_widths=[7*cm, 5*cm, 5*cm]))
    story.append(Spacer(1, 0.3*cm))

    # DCF
    story.append(Paragraph("DCF VALUATION", section_s))
    dcf_data = [['Year', 'FCF (KSh)', 'PV of FCF (KSh)']]
    for i, (fcf, pv) in enumerate(zip(dcf_result['fcfs'], dcf_result['pv_fcfs']), 1):
        dcf_data.append([f'Year {i}', f"{fcf:,.0f}", f"{pv:,.0f}"])
    dcf_data.append(['Terminal Value', f"{dcf_result['tv']:,.0f}", f"{dcf_result['pv_tv']:,.0f}"])
    dcf_data.append(['INTRINSIC VALUE', '', f"{dcf_result['intrinsic_value']:,.0f}"])
    story.append(pdf_table(dcf_data, col_widths=[4*cm, 6*cm, 7*cm]))
    story.append(Spacer(1, 0.3*cm))

    # Sensitivity
    story.append(Paragraph("SENSITIVITY ANALYSIS", section_s))
    sens_header = ['g \\ WACC'] + [f"{w:.0%}" for w in wacc_range]
    sens_rows = [sens_header]
    for i, g in enumerate(g_range):
        row = [f"g={g:.0%}"]
        for j in range(len(wacc_range)):
            iv_cell = sensitivity_matrix[i][j]
            row.append(f"{iv_cell:,.0f}")
        sens_rows.append(row)
    col_w = [2*cm] + [2.5*cm]*len(wacc_range)
    t = pdf_table(sens_rows, col_widths=col_w)

    # Add colour to sensitivity cells
    for i, g in enumerate(g_range):
        for j in range(len(wacc_range)):
            iv_cell = sensitivity_matrix[i][j]
            bg = colors.HexColor('#d4edda') if iv_cell >= asking_price \
                else colors.HexColor('#f8d7da')
            t.setStyle(TableStyle([
                ('BACKGROUND', (j+1, i+1), (j+1, i+1), bg)
            ]))
    story.append(t)
    story.append(Spacer(1, 0.3*cm))

    # LBO
    story.append(Paragraph("LBO ANALYSIS", section_s))
    lbo_sched = [['Year', 'Opening Bal', 'FCF', 'Interest', 'Principal', 'Closing Bal']]
    for s in lbo_result['schedule']:
        lbo_sched.append([
            s['year'],
            f"{s['opening_balance']:,.0f}",
            f"{s['fcf']:,.0f}",
            f"{s['interest']:,.0f}",
            f"{s['principal']:,.0f}",
            f"{s['closing_balance']:,.0f}",
        ])
    story.append(pdf_table(lbo_sched,
        col_widths=[1.5*cm, 3*cm, 3*cm, 3*cm, 3*cm, 3.5*cm]))

    lbo_returns = [
        ['Metric', 'Value'],
        ['Exit Value', f"KSh {lbo_result['exit_value']:,.0f}"],
        ['Remaining Debt', f"KSh {lbo_result['remaining_debt']:,.0f}"],
        ['Exit Equity Value', f"KSh {lbo_result['eev']:,.0f}"],
        ['MOIC', f"{lbo_result['moic']:.3f}x"],
        ['IRR', f"{lbo_result['irr']:.3f}%"],
        ['T-Bill Benchmark', f"{lbo_result['t_bill']:.1f}%"],
        ['Outperformance', f"{lbo_result['outperformance']:+.3f}%"],
    ]
    story.append(Spacer(1, 0.2*cm))
    story.append(pdf_table(lbo_returns, col_widths=[7*cm, 10*cm]))
    story.append(Spacer(1, 0.3*cm))

    # CCA
    story.append(Paragraph("COMPARABLE COMPANY ANALYSIS", section_s))
    cca_data = [['Company', 'EV', 'EV/EBITDA', 'EV/Revenue', 'P/E']]
    for c in cca_result['comparables']:
        cca_data.append([
            c['name'],
            f"{c['ev']:,.0f}",
            f"{c['ev_ebitda']:.2f}x",
            f"{c['ev_revenue']:.2f}x",
            f"{c['pe']:.2f}x",
        ])
    cca_data.append(['MEDIAN', '',
        f"{cca_result['median_ev_ebitda']:.2f}x",
        f"{cca_result['median_ev_revenue']:.2f}x",
        f"{cca_result['median_pe']:.2f}x"])
    story.append(pdf_table(cca_data,
        col_widths=[5*cm, 3*cm, 3*cm, 3.5*cm, 2.5*cm]))

    implied_data = [
        ['Method', 'Implied Value (KSh)'],
        ['EV/EBITDA', f"{cca_result['implied_ev_ebitda']:,.0f}"],
        ['EV/Revenue', f"{cca_result['implied_ev_revenue']:,.0f}"],
        ['P/E', f"{cca_result['implied_pe']:,.0f}"],
        ['Average', f"{cca_result['mean_implied']:,.0f}"],
    ]
    story.append(Spacer(1, 0.2*cm))
    story.append(pdf_table(implied_data, col_widths=[7*cm, 10*cm]))
    story.append(Spacer(1, 0.3*cm))

    # Investment Recommendation
    story.append(Paragraph("INVESTMENT RECOMMENDATION", section_s))
    dcf_verdict = "OVERPRICED" if dcf_result['mos'] < 0 else "UNDERPRICED"
    lbo_verdict = "POOR RETURNS" if lbo_result['irr'] < lbo_result['t_bill'] else "GOOD RETURNS"
    cca_verdict = "OVERPRICED" if cca_result['mean_implied'] < asking_price else "UNDERPRICED"

    signals = sum([
        1 if dcf_verdict == "UNDERPRICED" else 0,
        1 if lbo_verdict == "GOOD RETURNS" else 0,
        1 if cca_verdict == "UNDERPRICED" else 0,
    ])

    final = "DO NOT ACQUIRE" if signals < 2 else "ACQUIRE"

    rec_data = [
        ['Valuation Method', 'Implied Value', 'vs Asking Price', 'Signal'],
        ['DCF', f"KSh {dcf_result['intrinsic_value']:,.0f}",
         f"{dcf_result['mos']:.2f}%", dcf_verdict],
        ['LBO', f"IRR: {lbo_result['irr']:.2f}%",
         f"vs T-Bill {lbo_result['t_bill']:.1f}%", lbo_verdict],
        ['CCA', f"KSh {cca_result['mean_implied']:,.0f}",
         f"KSh {cca_result['mean_implied']-asking_price:+,.0f}", cca_verdict],
        ['FINAL RECOMMENDATION', '', '', final],
    ]
    story.append(pdf_table(rec_data,
        col_widths=[5*cm, 4*cm, 4*cm, 4*cm]))

    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=1,
        color=colors.HexColor('#c9a84c')))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"Savanna Capital Partners | {company_name} | {analyst} | {date_str}",
        note_s))

    doc.build(story)
    print(f"\n{GREEN}✓ PDF report saved: {filename}{RESET}")

# ============================================================
# MAIN — FAHARI PACKAGING FULL ANALYSIS
# ============================================================

def run_fahari_analysis():
    COMPANY = "Fahari Packaging Limited"
    ANALYST = "Byron S.M. Chege"
    ASKING_PRICE = 280_000_000

    print(f"\n{GOLD}{'='*60}{RESET}")
    print(f"{BOLD}{GOLD}  SAVANNA CAPITAL PARTNERS{RESET}")
    print(f"{BOLD}{GOLD}  VALUATION ENGINE v1.0{RESET}")
    print(f"{GOLD}{'='*60}{RESET}")
    print(f"  Company: {COMPANY}")
    print(f"  Analyst: {ANALYST}")
    print(f"  Date: {datetime.datetime.now().strftime('%d %B %Y')}")

    # ── CAPM & WACC ──
    rf    = 0.14
    beta  = 1.3
    rm    = 0.22
    E     = 160_000_000
    D     =  90_000_000
    rd    = 0.13
    t     = 0.30
    re, wacc = display_capm_wacc(COMPANY, rf, beta, rm, E, D, rd, t)

    # ── INCOME STATEMENT ──
    is_result = income_statement_engine(
        revenue=200_000_000,
        cogs=120_000_000,
        opex=30_000_000,
        da=10_000_000,
        debt=90_000_000,
        interest_rate=0.13,
        tax_rate=0.30,
        capex=8_000_000
    )
    display_income_statement(COMPANY, is_result)

    # ── DCF ──
    fcfs = [18_000_000, 22_000_000, 26_000_000, 30_000_000, 34_000_000]
    g    = 0.05
    dcf_result = dcf_engine(fcfs, wacc, g, ASKING_PRICE)
    display_dcf(COMPANY, dcf_result)

    # ── SENSITIVITY ──
    wacc_range = [0.17, 0.18, 0.19, 0.20, 0.21]
    g_range    = [0.03, 0.04, 0.05, 0.06, 0.07]
    sens_matrix = sensitivity_engine(fcfs, wacc_range, g_range)
    display_sensitivity(COMPANY, sens_matrix, wacc_range, g_range, ASKING_PRICE)

    # ── LBO ──
    lbo_result = lbo_engine(
        purchase_price=280_000_000,
        equity_pct=0.30,
        debt_pct=0.70,
        interest_rate=0.13,
        annual_fcf=30_000_000,
        exit_multiple=8,
        hold_years=5
    )
    display_lbo(COMPANY, lbo_result)

    # ── CCA ──
    comparables = [
        {'name': 'PackCo East Africa',     'market_cap': 320_000_000,
         'debt': 60_000_000, 'cash': 15_000_000,
         'ebitda': 45_000_000, 'revenue': 180_000_000, 'net_profit': 22_000_000},
        {'name': 'Rift Valley Packaging',  'market_cap': 450_000_000,
         'debt': 80_000_000, 'cash': 20_000_000,
         'ebitda': 58_000_000, 'revenue': 240_000_000, 'net_profit': 28_000_000},
        {'name': 'Nairobi Container Grp',  'market_cap': 275_000_000,
         'debt': 45_000_000, 'cash': 10_000_000,
         'ebitda': 38_000_000, 'revenue': 160_000_000, 'net_profit': 17_000_000},
        {'name': 'Mombasa Pack Ind.',       'market_cap': 390_000_000,
         'debt': 70_000_000, 'cash': 18_000_000,
         'ebitda': 52_000_000, 'revenue': 210_000_000, 'net_profit': 25_000_000},
        {'name': 'Great Lakes Packaging',  'market_cap': 340_000_000,
         'debt': 55_000_000, 'cash': 12_000_000,
         'ebitda': 47_000_000, 'revenue': 195_000_000, 'net_profit': 21_000_000},
    ]
    cca_result = cca_engine(comparables,
        target_ebitda=is_result['ebitda'],
        target_revenue=is_result['revenue'],
        target_net_profit=is_result['net_profit']
    )
    display_cca(COMPANY, cca_result, ASKING_PRICE)

    # ── PDF REPORT GENERATION ──
    pdf_filename = "Fahari_Packaging_Valuation_Report.pdf"
    generate_pdf_report(
        company_name=COMPANY,
        analyst=ANALYST,
        dcf_result=dcf_result,
        lbo_result=lbo_result,
        sensitivity_matrix=sens_matrix,
        wacc_range=wacc_range,
        g_range=g_range,
        cca_result=cca_result,
        is_result=is_result,
        asking_price=ASKING_PRICE,
        filename=pdf_filename
    )

if __name__ == "__main__":
    run_fahari_analysis()