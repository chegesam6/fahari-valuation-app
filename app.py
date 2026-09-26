import streamlit as st
import pandas as pd
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Savanna Capital Partners — Valuation Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title & Header
st.title("Savanna Capital Partners — Interactive Valuation Engine")
st.caption("Target: Fahari Packaging Limited | Analyst: Byron S.M. Chege (Kenyatta University)")
st.markdown("---")

# Sidebar Controls
st.sidebar.header("Model Inputs & Assumptions")

st.sidebar.subheader("Deal Structure & Pricing")
asking_price = st.sidebar.number_input("Asking Price (KSh)", value=280_000_000, step=10_000_000, format="%d")

st.sidebar.subheader("CAPM & WACC Inputs")
rf = st.sidebar.slider("Risk-Free Rate (r_f)", min_value=0.08, max_value=0.20, value=0.14, step=0.005, format="%.3f")
beta = st.sidebar.slider("Beta (β)", min_value=0.5, max_value=2.5, value=1.3, step=0.05)
rm = st.sidebar.slider("Market Return (r_m)", min_value=0.12, max_value=0.30, value=0.22, step=0.005, format="%.3f")

equity_val = st.sidebar.number_input("Equity Value (E)", value=160_000_000, step=5_000_000, format="%d")
debt_val = st.sidebar.number_input("Debt Value (D)", value=90_000_000, step=5_000_000, format="%d")
cost_of_debt = st.sidebar.slider("Cost of Debt (r_d)", min_value=0.05, max_value=0.25, value=0.13, step=0.005)
tax_rate = st.sidebar.slider("Tax Rate (t)", min_value=0.10, max_value=0.40, value=0.30, step=0.01)

st.sidebar.subheader("DCF Assumptions")
terminal_g = st.sidebar.slider("Terminal Growth Rate (g)", min_value=0.01, max_value=0.10, value=0.05, step=0.005)

st.sidebar.subheader("LBO Parameters")
lbo_debt_pct = st.sidebar.slider("LBO Debt %", min_value=0.30, max_value=0.90, value=0.70, step=0.05)
lbo_interest = st.sidebar.slider("LBO Interest Rate", min_value=0.05, max_value=0.25, value=0.13, step=0.005)
lbo_exit_mult = st.sidebar.slider("LBO Exit Multiple (x FCF)", min_value=3.0, max_value=15.0, value=8.0, step=0.5)

# Calculations
cost_of_equity = rf + beta * (rm - rf)
total_v = equity_val + debt_val
wacc = (equity_val / total_v * cost_of_equity) + (debt_val / total_v * cost_of_debt * (1 - tax_rate))

# Projected FCFs
fcfs = [18_000_000, 22_000_000, 26_000_000, 30_000_000, 34_000_000]
pv_fcfs = [fcf / ((1 + wacc) ** (i + 1)) for i, fcf in enumerate(fcfs)]
sum_pv_fcfs = sum(pv_fcfs)

terminal_val = (fcfs[-1] * (1 + terminal_g)) / (wacc - terminal_g) if wacc > terminal_g else 0
pv_tv = terminal_val / ((1 + wacc) ** len(fcfs))
intrinsic_val = sum_pv_fcfs + pv_tv
mos = ((intrinsic_val - asking_price) / intrinsic_val) * 100 if intrinsic_val > 0 else 0

# Dashboard Layout
tab1, tab2, tab3, tab4 = st.tabs(["DCF Valuation & Sensitivity", "LBO Model", "Comparable Companies (CCA)", "WACC & Income Statement"])

# Tab 1: DCF & Sensitivity
with tab1:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("WACC", f"{wacc*100:.2f}%")
    col2.metric("Intrinsic Value", f"KSh {intrinsic_val:,.0f}")
    col3.metric("Asking Price", f"KSh {asking_price:,.0f}")
    col4.metric("Margin of Safety", f"{mos:.2f}%", delta=f"{mos:.2f}%", delta_color="normal" if mos > 0 else "inverse")

    st.markdown("### Projected Cash Flows")
    dcf_df = pd.DataFrame({
        "Year": [f"Year {i+1}" for i in range(len(fcfs))],
        "FCF (KSh)": fcfs,
        "PV of FCF (KSh)": pv_fcfs
    })
    st.dataframe(dcf_df, use_container_width=True)

    st.markdown("### Interactive Sensitivity Matrix (WACC vs. Growth Rate)")
    wacc_range = np.linspace(wacc - 0.02, wacc + 0.02, 5)
    g_range = np.linspace(terminal_g - 0.02, terminal_g + 0.02, 5)

    sens_matrix = []
    for g in g_range:
        row = []
        for w in wacc_range:
            pvs = sum(fcf / ((1 + w) ** (i + 1)) for i, fcf in enumerate(fcfs))
            tv = (fcfs[-1] * (1 + g)) / (w - g) if w > g else 0
            pv_t = tv / ((1 + w) ** len(fcfs))
            row.append(pvs + pv_t)
        sens_matrix.append(row)

    sens_df = pd.DataFrame(
        sens_matrix,
        index=[f"g = {g*100:.1f}%" for g in g_range],
        columns=[f"WACC = {w*100:.1f}%" for w in wacc_range]
    )

    st.dataframe(sens_df.style.format("KSh {:,.0f}").map(
        lambda val: 'background-color: #d4edda; color: #155724;' if val >= asking_price else 'background-color: #f8d7da; color: #721c24;'
    ), use_container_width=True)

# Tab 2: LBO
with tab2:
    st.markdown("### LBO Debt Amortization Schedule")
    lbo_equity = asking_price * (1 - lbo_debt_pct)
    lbo_debt = asking_price * lbo_debt_pct
    annual_fcf = 30_000_000
    hold_years = 5

    opening = lbo_debt
    schedule = []
    for yr in range(1, hold_years + 1):
        interest = opening * lbo_interest
        principal = annual_fcf - interest
        closing = opening - principal
        schedule.append({
            "Year": yr,
            "Opening Debt": opening,
            "FCF": annual_fcf,
            "Interest": interest,
            "Principal Paydown": principal,
            "Closing Debt": closing
        })
        opening = closing

    sched_df = pd.DataFrame(schedule)
    st.dataframe(sched_df.style.format({
        "Opening Debt": "KSh {:,.0f}",
        "FCF": "KSh {:,.0f}",
        "Interest": "KSh {:,.0f}",
        "Principal Paydown": "KSh {:,.0f}",
        "Closing Debt": "KSh {:,.0f}"
    }), use_container_width=True)

    remaining_debt = schedule[-1]["Closing Debt"]
    exit_value = lbo_exit_mult * annual_fcf
    eev = exit_value - remaining_debt
    moic = eev / lbo_equity if lbo_equity > 0 else 0
    irr = ((moic ** (1 / hold_years)) - 1) * 100 if moic > 0 else 0

    lbo_c1, lbo_c2, lbo_c3, lbo_c4 = st.columns(4)
    lbo_c1.metric("Initial Equity Invested", f"KSh {lbo_equity:,.0f}")
    lbo_c2.metric("Exit Equity Value (EEV)", f"KSh {eev:,.0f}")
    lbo_c3.metric("MOIC", f"{moic:.2f}x")
    lbo_c4.metric("IRR", f"{irr:.2f}%", delta=f"{irr - 15.5:.2f}% vs T-Bill")

# Tab 3: CCA
with tab3:
    st.markdown("### Comparable Market Multiples")
    cca_data = [
        {"Company": "PackCo East Africa", "EV": 365_000_000, "EBITDA": 45_000_000, "Revenue": 180_000_000, "Net Profit": 22_000_000},
        {"Company": "Rift Valley Packaging", "EV": 510_000_000, "EBITDA": 58_000_000, "Revenue": 240_000_000, "Net Profit": 28_000_000},
        {"Company": "Nairobi Container Grp", "EV": 310_000_000, "EBITDA": 38_000_000, "Revenue": 160_000_000, "Net Profit": 17_000_000},
        {"Company": "Mombasa Pack Ind.", "EV": 442_000_000, "EBITDA": 52_000_000, "Revenue": 210_000_000, "Net Profit": 25_000_000},
        {"Company": "Great Lakes Packaging", "EV": 383_000_000, "EBITDA": 47_000_000, "Revenue": 195_000_000, "Net Profit": 21_000_000},
    ]
    cca_df = pd.DataFrame(cca_data)
    cca_df["EV/EBITDA"] = cca_df["EV"] / cca_df["EBITDA"]
    cca_df["EV/Revenue"] = cca_df["EV"] / cca_df["Revenue"]

    st.dataframe(cca_df.style.format({
        "EV": "KSh {:,.0f}", "EBITDA": "KSh {:,.0f}", "Revenue": "KSh {:,.0f}",
        "Net Profit": "KSh {:,.0f}", "EV/EBITDA": "{:.2f}x", "EV/Revenue": "{:.2f}x"
    }), use_container_width=True)

    med_ebitda = cca_df["EV/EBITDA"].median()
    med_rev = cca_df["EV/Revenue"].median()

    target_ebitda = 50_000_000
    target_rev = 200_000_000

    implied_ebitda_val = med_ebitda * target_ebitda
    implied_rev_val = med_rev * target_rev
    mean_cca = (implied_ebitda_val + implied_rev_val) / 2

    c_col1, c_col2, c_col3 = st.columns(3)
    c_col1.metric("EV/EBITDA Valuation", f"KSh {implied_ebitda_val:,.0f}", f"{med_ebitda:.2f}x Multiple")
    c_col2.metric("EV/Revenue Valuation", f"KSh {implied_rev_val:,.0f}", f"{med_rev:.2f}x Multiple")
    c_col3.metric("Mean Implied Valuation", f"KSh {mean_cca:,.0f}")

# Tab 4: WACC & Income Statement
with tab4:
    st.markdown("### WACC Breakdown")
    wacc_df = pd.DataFrame({
        "Component": ["Cost of Equity (r_e)", "After-Tax Cost of Debt", "Equity Weight (E/V)", "Debt Weight (D/V)", "WACC"],
        "Value": [f"{cost_of_equity*100:.2f}%", f"{cost_of_debt*(1-tax_rate)*100:.2f}%", f"{equity_val/total_v*100:.2f}%", f"{debt_val/total_v*100:.2f}%", f"{wacc*100:.2f}%"]
    })
    st.dataframe(wacc_df, use_container_width=True)
