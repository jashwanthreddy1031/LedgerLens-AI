"""
LedgerLens AI - Enterprise Financial Management & Reconciliation Platform
Modern fintech SaaS dashboard powered by Streamlit, Plotly, SQLite, and Google Gemini AI.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Ensure environment variables are loaded prior to any operations
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

import pandas as pd
import streamlit as st

import gemini_service as ai_service
import charts
from database import (
    add_transaction,
    delete_transaction,
    get_database_info,
    get_summary,
    get_transaction_by_id,
    get_transactions,
    update_transaction,
)
import reconciliation as rec

# =========================================================
# APPLICATION SETUP & PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="LedgerLens AI — Financial Intelligence",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Light Fintech CSS Theme
LIGHT_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}

/* Backgrounds & Text */
.stApp {
    background-color: #F8FAFC !important;
    color: #0F172A !important;
}

[data-testid="stHeader"] {
    background-color: rgba(248, 250, 252, 0.9) !important;
    backdrop-filter: blur(8px);
}

[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #E2E8F0 !important;
    box-shadow: 1px 0 3px 0 rgba(0, 0, 0, 0.02);
}

.block-container {
    max-width: 1440px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 3.5rem !important;
}

/* KPI Cards */
.fintech-card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 20px 22px;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.04);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    height: 100%;
}
.fintech-card:hover {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.06), 0 2px 4px -2px rgba(0, 0, 0, 0.06);
}

.card-header-flex {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.card-title {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #64748B;
}

.card-icon-badge {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
}

.badge-indigo { background-color: #EEF2FF; color: #4F46E5; }
.badge-emerald { background-color: #ECFDF5; color: #10B981; }
.badge-rose { background-color: #FEF2F2; color: #EF4444; }
.badge-amber { background-color: #FFFBEB; color: #F59E0B; }
.badge-blue { background-color: #EFF6FF; color: #3B82F6; }

.card-value {
    font-size: 28px;
    font-weight: 700;
    color: #0F172A;
    line-height: 1.2;
    margin-bottom: 6px;
}

.card-footer {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12.5px;
    color: #64748B;
}

.pill-delta-positive {
    background-color: #ECFDF5;
    color: #059669;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 12px;
}

.pill-delta-negative {
    background-color: #FEF2F2;
    color: #DC2626;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 12px;
}

.pill-delta-neutral {
    background-color: #F1F5F9;
    color: #64748B;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 12px;
}

/* Page Header & Hero */
.page-hero {
    background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.03);
}

.hero-heading {
    font-size: 26px;
    font-weight: 800;
    color: #0F172A;
    letter-spacing: -0.02em;
    margin-bottom: 4px;
}

.hero-subheading {
    font-size: 14px;
    color: #64748B;
}

/* Section titles */
.section-heading {
    font-size: 17px;
    font-weight: 700;
    color: #0F172A;
    margin-top: 14px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Streamlit Native Elements Overrides for Clean Light SaaS */
div[data-testid="stForm"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 14px !important;
    padding: 24px !important;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
}

div.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    padding: 6px 16px !important;
    transition: all 0.15s ease !important;
}

div.stButton > button[kind="primary"],
div.stFormSubmitButton > button[kind="primary"] {
    background-color: #4F46E5 !important;
    border-color: #4F46E5 !important;
    color: #FFFFFF !important;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #4338CA !important;
    border-color: #4338CA !important;
}

div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea,
div[data-baseweb="select"] {
    background-color: #FFFFFF !important;
    border-color: #CBD5E1 !important;
    color: #0F172A !important;
    border-radius: 8px !important;
}

/* Status Badges */
.badge-income-pill {
    background-color: #ECFDF5;
    color: #059669;
    border: 1px solid #A7F3D0;
    border-radius: 6px;
    padding: 3px 10px;
    font-weight: 600;
    font-size: 12px;
    display: inline-block;
}

.badge-expense-pill {
    background-color: #FEF2F2;
    color: #DC2626;
    border: 1px solid #FECACA;
    border-radius: 6px;
    padding: 3px 10px;
    font-weight: 600;
    font-size: 12px;
    display: inline-block;
}

/* AI Message & Chat Styling */
.ai-summary-box {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left: 4px solid #4F46E5;
    border-radius: 12px;
    padding: 22px 26px;
    margin: 16px 0;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.03);
    line-height: 1.6;
}

.ai-pill-question {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 12.5px;
    color: #334155;
    cursor: pointer;
    display: inline-block;
    margin-right: 6px;
    margin-bottom: 6px;
    transition: all 0.15s ease;
}
.ai-pill-question:hover {
    background-color: #EEF2FF;
    border-color: #C7D2FE;
    color: #4F46E5;
}

/* Hide streamlit default chrome */
#MainMenu, footer {
    visibility: hidden;
}
</style>
"""

st.markdown(LIGHT_THEME_CSS, unsafe_allow_html=True)


# =========================================================
# HELPER UTILITIES
# =========================================================

def format_currency(amount: float) -> str:
    """Format float into Indian Rupee notation with standard decimals."""
    return f"₹{amount:,.2f}"


def get_greeting() -> str:
    """Return greeting string based on local hour."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"


def get_all_transactions_df() -> pd.DataFrame:
    """Retrieve all transactions as a typed Pandas DataFrame."""
    records = get_transactions()
    cols = ["id", "date", "type", "category", "amount", "description"]
    if not records:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df = df.dropna(subset=["date"])
    return df[cols]


def compute_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """Calculate income, expense, net balance, and savings rate."""
    if df.empty:
        return {"income": 0.0, "expenses": 0.0, "balance": 0.0, "savings_rate": 0.0}
    inc = float(df.loc[df["type"] == "Income", "amount"].sum())
    exp = float(df.loc[df["type"] == "Expense", "amount"].sum())
    bal = inc - exp
    rate = round((bal / inc * 100), 1) if inc > 0 else 0.0
    return {
        "income": round(inc, 2),
        "expenses": round(exp, 2),
        "balance": round(bal, 2),
        "savings_rate": rate,
    }


def compute_period_comparison(
    current_df: pd.DataFrame,
    all_df: pd.DataFrame,
    start_d: date,
    end_d: date,
) -> Dict[str, Optional[float]]:
    """
    Compare current period with equivalent previous period without inventing data.
    Returns percentage change or None if insufficient history.
    """
    duration_days = (end_d - start_d).days + 1
    prev_end = start_d - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration_days - 1)

    prev_df = all_df[(all_df["date"] >= prev_start) & (all_df["date"] <= prev_end)]
    if prev_df.empty:
        return {"income_change": None, "expenses_change": None, "balance_change": None}

    curr_metrics = compute_metrics(current_df)
    prev_metrics = compute_metrics(prev_df)

    def calc_pct(curr, prev):
        if prev == 0:
            return None
        return round(((curr - prev) / abs(prev)) * 100, 1)

    return {
        "income_change": calc_pct(curr_metrics["income"], prev_metrics["income"]),
        "expenses_change": calc_pct(curr_metrics["expenses"], prev_metrics["expenses"]),
        "balance_change": calc_pct(curr_metrics["balance"], prev_metrics["balance"]),
    }


def build_financial_context_text(df: pd.DataFrame, start_d: date, end_d: date) -> str:
    """Format filtered records into structured factual text for Gemini."""
    metrics = compute_metrics(df)
    tx_lines = []
    sorted_df = df.sort_values("date", ascending=False)
    for _, r in sorted_df.iterrows():
        tx_lines.append(
            f"- Date: {r['date']}, Type: {r['type']}, Category: {r['category']}, "
            f"Amount: ₹{r['amount']:,.2f}, Description: {r['description'] or 'None'}"
        )
    tx_text = "\n".join(tx_lines) if tx_lines else "No transactions recorded for this period."

    return f"""
LedgerLens AI Database Financial Snapshot:
Date Range: {start_d.strftime('%Y-%m-%d')} to {end_d.strftime('%Y-%m-%d')}
Total Transactions: {len(df)}
Total Recorded Income: ₹{metrics['income']:,.2f}
Total Recorded Expenses: ₹{metrics['expenses']:,.2f}
Net Balance (Income minus Expenses): ₹{metrics['balance']:,.2f}
Savings Rate: {metrics['savings_rate']}%

Detailed Transaction Register:
{tx_text}
"""


# =========================================================
# SIDEBAR NAVIGATION
# =========================================================

with st.sidebar:
    # Brand & Logo
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:12px;padding:6px 0 16px 0;border-bottom:1px solid #E2E8F0;">
            <div style="
                background: linear-gradient(135deg, #4F46E5 0%, #3B82F6 100%);
                width: 40px; height: 40px; border-radius: 10px;
                display: flex; align-items: center; justify-content: center;
                color: #FFFFFF; font-size: 20px; font-weight: 800;
                box-shadow: 0 2px 4px rgba(79, 70, 229, 0.2);">
                ✦
            </div>
            <div>
                <div style="font-size:18px;font-weight:800;color:#0F172A;letter-spacing:-0.01em;">
                    LedgerLens <span style="color:#4F46E5;">AI</span>
                </div>
                <div style="font-size:11.5px;font-weight:500;color:#64748B;">
                    Intelligent Financial Management
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    # Navigation Radio
    nav_options = [
        "📊  Dashboard",
        "💳  Transactions",
        "⚖️  Reconciliation",
        "💡  AI Insights",
        "💬  AI Assistant",
        "⚙️  Settings",
    ]

    selected_nav = st.radio(
        "Navigation",
        options=nav_options,
        index=0,
        label_visibility="collapsed",
        key="global_nav_page",
    )

    # Clean active page name
    current_page = selected_nav.split("  ")[1]

    # Spacer
    st.markdown("<div style='height: 38vh;'></div>", unsafe_allow_html=True)

    # User Profile / Workspace Section at bottom of sidebar
    db_stat = get_database_info()
    api_stat_msg = "Connected" if ai_service.get_api_key() else "No API Key"
    status_dot = "#10B981" if ai_service.get_api_key() else "#EF4444"

    st.markdown(
        f"""
        <div style="
            background: #F8FAFC; border: 1px solid #E2E8F0;
            border-radius: 12px; padding: 14px; margin-top: auto;">
            <div style="display:flex;align-items:center;gap:10px;">
                <div style="
                    width:32px;height:32px;border-radius:50%;
                    background:#EEF2FF;color:#4F46E5;
                    display:flex;align-items:center;justify-content:center;
                    font-size:13px;font-weight:700;">
                    LL
                </div>
                <div style="flex:1;overflow:hidden;">
                    <div style="font-size:13px;font-weight:700;color:#0F172A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        Enterprise Ledger
                    </div>
                    <div style="font-size:11px;color:#64748B;">
                        {db_stat['total_transactions']} txns · {db_stat['size_kb']} KB
                    </div>
                </div>
                <div style="width:8px;height:8px;border-radius:50%;background:{status_dot};" title="{api_stat_msg}"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# GLOBAL DATA & DATE FILTERING
# =========================================================

all_transactions_df = get_all_transactions_df()

# Compute initial start and end dates
default_end = date.today()
default_start = default_end - timedelta(days=29)

if "filter_start_date" not in st.session_state:
    st.session_state["filter_start_date"] = default_start
if "filter_end_date" not in st.session_state:
    st.session_state["filter_end_date"] = default_end

active_start = st.session_state["filter_start_date"]
active_end = st.session_state["filter_end_date"]

# Filtered dataset
if not all_transactions_df.empty:
    filtered_df = all_transactions_df[
        (all_transactions_df["date"] >= active_start)
        & (all_transactions_df["date"] <= active_end)
    ].copy()
else:
    filtered_df = all_transactions_df.copy()

current_metrics = compute_metrics(filtered_df)
period_deltas = compute_period_comparison(
    filtered_df, all_transactions_df, active_start, active_end
)
financial_context = build_financial_context_text(filtered_df, active_start, active_end)


# =========================================================
# PAGE 1: MAIN DASHBOARD
# =========================================================

if current_page == "Dashboard":

    # Hero Header with greeting and Date Range Controls
    hero_col, filter_col = st.columns([2.4, 1.6])

    with hero_col:
        st.markdown(
            f"""
            <div class="page-hero">
                <div class="hero-heading">{get_greeting()}, Finance Team</div>
                <div class="hero-subheading">
                    Here's your real-time financial overview for 
                    <b>{active_start.strftime('%d %b %Y')}</b> to <b>{active_end.strftime('%d %b %Y')}</b>.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with filter_col:
        with st.container():
            st.markdown(
                """
                <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.03);">
                    <div style="font-size:12px;font-weight:700;color:#64748B;text-transform:uppercase;margin-bottom:8px;">
                        📅 Date Range Filter
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                new_start = st.date_input("From", value=active_start, key="dash_start_d")
            with d_col2:
                new_end = st.date_input("To", value=active_end, key="dash_end_d")

            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                if st.button("Apply Filter", type="primary", use_container_width=True):
                    if new_start > new_end:
                        st.error("Start date must be before end date.")
                    else:
                        st.session_state["filter_start_date"] = new_start
                        st.session_state["filter_end_date"] = new_end
                        st.rerun()
            with btn_col2:
                if st.button("All Time", use_container_width=True):
                    if not all_transactions_df.empty:
                        st.session_state["filter_start_date"] = all_transactions_df["date"].min()
                        st.session_state["filter_end_date"] = all_transactions_df["date"].max()
                    st.rerun()

    # 4 Financial Summary Cards
    card1, card2, card3, card4 = st.columns(4)

    # 1. Total Income
    with card1:
        inc_delta = period_deltas["income_change"]
        delta_html = (
            f"<span class='pill-delta-positive'>+{inc_delta}% vs prev</span>"
            if inc_delta is not None and inc_delta > 0
            else (
                f"<span class='pill-delta-negative'>{inc_delta}% vs prev</span>"
                if inc_delta is not None and inc_delta < 0
                else "<span class='pill-delta-neutral'>No prev period</span>"
            )
        )
        st.markdown(
            f"""
            <div class="fintech-card">
                <div class="card-header-flex">
                    <span class="card-title">Total Income</span>
                    <div class="card-icon-badge badge-emerald">↓</div>
                </div>
                <div class="card-value">{format_currency(current_metrics['income'])}</div>
                <div class="card-footer">
                    {delta_html}
                    <span>Revenue & receipts</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Total Expenses
    with card2:
        exp_delta = period_deltas["expenses_change"]
        delta_html = (
            f"<span class='pill-delta-negative'>+{exp_delta}% vs prev</span>"
            if exp_delta is not None and exp_delta > 0
            else (
                f"<span class='pill-delta-positive'>{exp_delta}% vs prev</span>"
                if exp_delta is not None and exp_delta < 0
                else "<span class='pill-delta-neutral'>No prev period</span>"
            )
        )
        st.markdown(
            f"""
            <div class="fintech-card">
                <div class="card-header-flex">
                    <span class="card-title">Total Expenses</span>
                    <div class="card-icon-badge badge-rose">↑</div>
                </div>
                <div class="card-value">{format_currency(current_metrics['expenses'])}</div>
                <div class="card-footer">
                    {delta_html}
                    <span>Operating outflows</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 3. Net Balance
    with card3:
        bal = current_metrics["balance"]
        bal_delta = period_deltas["balance_change"]
        bal_class = "badge-emerald" if bal >= 0 else "badge-rose"
        bal_symbol = "↗" if bal >= 0 else "↘"
        delta_html = (
            f"<span class='pill-delta-positive'>+{bal_delta}%</span>"
            if bal_delta is not None and bal_delta > 0
            else (
                f"<span class='pill-delta-negative'>{bal_delta}%</span>"
                if bal_delta is not None and bal_delta < 0
                else "<span class='pill-delta-neutral'>Calculated</span>"
            )
        )
        st.markdown(
            f"""
            <div class="fintech-card">
                <div class="card-header-flex">
                    <span class="card-title">Net Balance</span>
                    <div class="card-icon-badge {bal_class}">{bal_symbol}</div>
                </div>
                <div class="card-value">{format_currency(bal)}</div>
                <div class="card-footer">
                    {delta_html}
                    <span>Income minus expenses</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 4. Savings Rate
    with card4:
        rate = current_metrics["savings_rate"]
        rate_class = "badge-indigo" if rate >= 20 else ("badge-amber" if rate >= 0 else "badge-rose")
        rate_indicator = (
            "<span class='pill-delta-positive'>Optimal</span>"
            if rate >= 20
            else ("<span class='pill-delta-neutral'>Break-even</span>" if rate >= 0 else "<span class='pill-delta-negative'>Deficit</span>")
        )
        st.markdown(
            f"""
            <div class="fintech-card">
                <div class="card-header-flex">
                    <span class="card-title">Savings Rate</span>
                    <div class="card-icon-badge {rate_class}">%</div>
                </div>
                <div class="card-value">{rate}%</div>
                <div class="card-footer">
                    {rate_indicator}
                    <span>Share of income saved</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # Visualizations Row 1: Chart A (Income vs Expense) & Chart B (Cash Flow Trend)
    st.markdown('<div class="section-heading">📈 Financial Performance & Cash Flow</div>', unsafe_allow_html=True)
    c_col1, c_col2 = st.columns(2)

    with c_col1:
        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;padding:16px 20px 8px 20px;">
                <div style="font-size:14px;font-weight:700;color:#0F172A;margin-bottom:2px;">Income vs Expenses Comparison</div>
                <div style="font-size:12px;color:#64748B;">Monthly side-by-side grouped totals</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig_a = charts.create_income_vs_expense_chart(filtered_df)
        st.plotly_chart(fig_a, use_container_width=True, config={"displayModeBar": False})

    with c_col2:
        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;padding:16px 20px 8px 20px;">
                <div style="font-size:14px;font-weight:700;color:#0F172A;margin-bottom:2px;">Cash Flow Dynamics</div>
                <div style="font-size:12px;color:#64748B;">Income and expense velocity over time</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig_b = charts.create_cash_flow_trend_chart(filtered_df)
        st.plotly_chart(fig_b, use_container_width=True, config={"displayModeBar": False})

    # Visualizations Row 2: Chart C (Expense Breakdown Donut) & Chart D (Monthly Net Savings)
    c_col3, c_col4 = st.columns(2)

    with c_col3:
        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;padding:16px 20px 8px 20px;">
                <div style="font-size:14px;font-weight:700;color:#0F172A;margin-bottom:2px;">Expense Distribution by Category</div>
                <div style="font-size:12px;color:#64748B;">Breakdown of operational capital allocation</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig_c = charts.create_expense_breakdown_chart(filtered_df)
        st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False})

    with c_col4:
        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;padding:16px 20px 8px 20px;">
                <div style="font-size:14px;font-weight:700;color:#0F172A;margin-bottom:2px;">Monthly Net Performance</div>
                <div style="font-size:12px;color:#64748B;">Monthly retained capital above/below baseline</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig_d = charts.create_monthly_performance_chart(filtered_df)
        st.plotly_chart(fig_d, use_container_width=True, config={"displayModeBar": False})

    # Recent Transactions Section
    st.markdown('<div class="section-heading">🕒 Recent Ledger Entries</div>', unsafe_allow_html=True)
    if not filtered_df.empty:
        preview_df = (
            filtered_df.sort_values(["date", "id"], ascending=[False, False])
            .head(6)
            .copy()
        )
        preview_df["date"] = preview_df["date"].astype(str)
        preview_df["formatted_amount"] = preview_df["amount"].map(format_currency)

        st.dataframe(
            preview_df[["date", "type", "category", "formatted_amount", "description"]].rename(
                columns={
                    "date": "Date",
                    "type": "Type",
                    "category": "Category",
                    "formatted_amount": "Amount",
                    "description": "Description",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No transaction records found for the selected date range.")


# =========================================================
# PAGE 2: TRANSACTIONS MANAGEMENT
# =========================================================

elif current_page == "Transactions":

    st.markdown(
        """
        <div class="page-hero">
            <div class="hero-heading">Transaction Management</div>
            <div class="hero-subheading">
                Record new ledger entries, filter financial activity, and maintain accurate records.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    t_tab1, t_tab2 = st.tabs(["📋 Ledger Register & Search", "➕ New Transaction Entry"])

    with t_tab1:
        # Search & Filter Controls
        f1, f2, f3 = st.columns([2, 1, 1])
        with f1:
            search_query = st.text_input(
                "Search transactions",
                placeholder="Search by description, reference, or category...",
                key="tx_search_q",
            )
        with f2:
            type_filter = st.selectbox(
                "Filter by Type",
                ["All Types", "Income", "Expense"],
                key="tx_type_f",
            )
        with f3:
            all_cats = sorted(all_transactions_df["category"].dropna().unique().tolist())
            cat_filter = st.selectbox(
                "Filter by Category",
                ["All Categories"] + all_cats,
                key="tx_cat_f",
            )

        # Apply filtering
        work_tx_df = filtered_df.copy()
        if type_filter != "All Types":
            work_tx_df = work_tx_df[work_tx_df["type"] == type_filter]
        if cat_filter != "All Categories":
            work_tx_df = work_tx_df[work_tx_df["category"] == cat_filter]
        if search_query.strip():
            sq = search_query.strip().lower()
            mask = (
                work_tx_df["description"].astype(str).str.lower().str.contains(sq)
                | work_tx_df["category"].astype(str).str.lower().str.contains(sq)
            )
            work_tx_df = work_tx_df[mask]

        st.caption(f"Showing {len(work_tx_df)} of {len(all_transactions_df)} total transactions")

        if not work_tx_df.empty:
            display_table = work_tx_df.copy()
            display_table["date"] = display_table["date"].astype(str)
            display_table["formatted_amount"] = display_table["amount"].map(format_currency)

            st.dataframe(
                display_table[
                    ["id", "date", "type", "category", "formatted_amount", "description"]
                ].rename(
                    columns={
                        "id": "ID",
                        "date": "Date",
                        "type": "Type",
                        "category": "Category",
                        "formatted_amount": "Amount",
                        "description": "Description",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

            # Edit and Delete Controls
            st.divider()
            st.markdown('<div class="section-heading">✏️ Modify or Delete Record</div>', unsafe_allow_html=True)
            
            selected_tx_id = st.selectbox(
                "Select Transaction ID to manage",
                options=work_tx_df["id"].tolist(),
                key="sel_tx_id",
            )

            tx_record = get_transaction_by_id(selected_tx_id)
            if tx_record:
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    with st.form("edit_tx_form"):
                        st.markdown(f"<b>Edit Record #{selected_tx_id}</b>", unsafe_allow_html=True)
                        edit_date = st.date_input("Date", value=datetime.strptime(tx_record["date"], "%Y-%m-%d").date())
                        edit_type = st.selectbox(
                            "Type",
                            ["Income", "Expense"],
                            index=0 if tx_record["type"] == "Income" else 1,
                        )
                        edit_cat = st.text_input("Category", value=tx_record["category"])
                        edit_amount = st.number_input(
                            "Amount (₹)",
                            min_value=0.01,
                            value=float(tx_record["amount"]),
                            step=100.0,
                            format="%.2f",
                        )
                        edit_desc = st.text_area("Description", value=tx_record["description"] or "")
                        
                        save_edit = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
                        if save_edit:
                            if not edit_cat.strip():
                                st.error("Category cannot be empty.")
                            elif edit_amount <= 0:
                                st.error("Amount must be greater than zero.")
                            else:
                                update_transaction(
                                    selected_tx_id,
                                    str(edit_date),
                                    edit_type,
                                    edit_cat.strip(),
                                    edit_amount,
                                    edit_desc.strip(),
                                )
                                st.success("Transaction updated successfully.")
                                st.rerun()

                with e_col2:
                    st.markdown(
                        f"""
                        <div style="background:#FFF1F2;border:1px solid #FECDD3;border-radius:14px;padding:22px;">
                            <div style="font-size:15px;font-weight:700;color:#9F1239;margin-bottom:8px;">
                                ⚠️ Delete Transaction Record
                            </div>
                            <div style="font-size:13px;color:#4C0519;margin-bottom:16px;">
                                Deleting will permanently remove transaction <b>#{selected_tx_id}</b> 
                                (₹{tx_record['amount']:,.2f} · {tx_record['category']}) from your SQLite database.
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.write("")
                    confirm_del = st.checkbox(
                        f"I confirm permanent deletion of ID #{selected_tx_id}",
                        key=f"del_chk_{selected_tx_id}",
                    )
                    if st.button("Delete Transaction Permanently", key="btn_del_tx"):
                        if confirm_del:
                            delete_transaction(selected_tx_id)
                            st.success("Transaction deleted successfully.")
                            st.rerun()
                        else:
                            st.warning("Please tick the confirmation checkbox first.")
        else:
            st.info("No matching transactions found.")

    with t_tab2:
        st.markdown(
            """
            <div style="max-width:700px;margin:0 auto;">
                <div style="font-size:16px;font-weight:700;color:#0F172A;margin-bottom:4px;">
                    Create New Transaction Record
                </div>
                <div style="font-size:13px;color:#64748B;margin-bottom:16px;">
                    Enter the details below. All fields are validated before inserting into the ledger.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("new_transaction_form", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                t_date = st.date_input("Transaction Date", value=date.today())
                t_type = st.selectbox("Transaction Type", ["Income", "Expense"])
            with f_col2:
                t_amount = st.number_input(
                    "Amount (₹)",
                    min_value=0.01,
                    value=1000.0,
                    step=100.0,
                    format="%.2f",
                )
                t_desc = st.text_input(
                    "Description / Narration",
                    placeholder="e.g., Client payment for Q3 consulting invoice",
                )

            standard_income_cats = [
                "Sales & Revenue",
                "Service Revenue",
                "Customer Payment",
                "Interest Received",
                "Capital Introduced",
                "Investment Return",
                "Other Income",
            ]
            standard_expense_cats = [
                "Salaries & Wages",
                "Rent & Office Space",
                "Cloud & SaaS Software",
                "Utilities & Electricity",
                "Supplier & Inventory Payment",
                "Marketing & Advertising",
                "Legal & Accounting Fees",
                "Travel & Logistics",
                "Taxes & Compliance",
                "Bank & Gateway Charges",
                "Other Expense",
            ]

            available_cats = standard_income_cats if t_type == "Income" else standard_expense_cats
            cat_c1, cat_c2 = st.columns(2)
            with cat_c1:
                t_category = st.selectbox("Category", available_cats)
            with cat_c2:
                custom_cat = st.text_input("Custom Category (Optional)", placeholder="Or type a custom category")

            submit_new = st.form_submit_button("Record Transaction", type="primary", use_container_width=True)

            if submit_new:
                final_cat = custom_cat.strip() if custom_cat.strip() else t_category
                if t_amount <= 0:
                    st.error("Amount must be strictly greater than zero.")
                elif not t_desc.strip():
                    st.error("Please provide a description for the transaction.")
                else:
                    new_id = add_transaction(
                        str(t_date),
                        t_type,
                        final_cat,
                        t_amount,
                        t_desc.strip(),
                    )
                    st.success(f"Transaction #{new_id} recorded successfully.")
                    st.rerun()


# =========================================================
# PAGE 3: RECONCILIATION
# =========================================================

elif current_page == "Reconciliation":

    st.markdown(
        """
        <div class="page-hero">
            <div class="hero-heading">Deterministic Financial Reconciliation</div>
            <div class="hero-subheading">
                Audit bank statements against ledger records with multi-pass matching, fuzzy text similarity, 
                date tolerance, duplicate detection, and automated variance analysis.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    rec_col_left, rec_col_right = st.columns([1, 1])

    with rec_col_left:
        st.markdown("<b>1. Bank Statement File</b>", unsafe_allow_html=True)
        bank_file = st.file_uploader(
            "Upload Bank Statement (CSV or Excel)",
            type=["csv", "xlsx", "xls"],
            key="rec_bank_file",
        )

    with rec_col_right:
        st.markdown("<b>2. Ledger Source</b>", unsafe_allow_html=True)
        use_active_db = st.checkbox(
            "Reconcile directly against current Database Ledger",
            value=True,
            key="rec_use_db",
        )
        ledger_file = None
        if not use_active_db:
            ledger_file = st.file_uploader(
                "Upload Company Ledger (CSV or Excel)",
                type=["csv", "xlsx", "xls"],
                key="rec_ledger_file",
            )
        else:
            st.info(f"Using {len(all_transactions_df)} transactions from your local SQLite database.")

    # Matching Configuration
    with st.expander("⚙️ Reconciliation Matching Parameters", expanded=False):
        par_c1, par_c2 = st.columns(2)
        with par_c1:
            date_tolerance = st.slider(
                "Date Tolerance Window (Days)",
                min_value=0,
                max_value=14,
                value=3,
                help="Allowable date difference between bank posting and ledger entry",
            )
        with par_c2:
            fuzzy_sim = st.slider(
                "Fuzzy Description Similarity Threshold (%)",
                min_value=50,
                max_value=95,
                value=70,
                help="Minimum text similarity score for approximate description matching",
            )

    # Process files
    if bank_file is not None:
        try:
            # Read bank file
            if bank_file.name.endswith(".csv"):
                bank_raw_df = pd.read_csv(bank_file)
            else:
                bank_raw_df = pd.read_excel(bank_file)

            # Read ledger file
            if use_active_db:
                ledger_raw_df = all_transactions_df.copy()
            elif ledger_file is not None:
                if ledger_file.name.endswith(".csv"):
                    ledger_raw_df = pd.read_csv(ledger_file)
                else:
                    ledger_raw_df = pd.read_excel(ledger_file)
            else:
                st.warning("Please upload a company ledger file or enable the database option.")
                ledger_raw_df = None

            if ledger_raw_df is not None and not bank_raw_df.empty:
                # Column detection
                bank_cols = rec.detect_columns(bank_raw_df)
                ledger_cols = rec.detect_columns(ledger_raw_df)

                bank_txs = rec.normalize_transactions(bank_raw_df, "bank", bank_cols)
                ledger_txs = rec.normalize_transactions(ledger_raw_df, "ledger", ledger_cols)

                # Execute Deterministic Reconciliation
                (
                    matched_results,
                    unmatched_bank,
                    unmatched_ledger,
                    amount_mismatches,
                    bank_dups,
                    ledger_dups,
                    rec_summary,
                ) = rec.run_reconciliation(
                    bank_txs,
                    ledger_txs,
                    date_tolerance_days=date_tolerance,
                    fuzzy_threshold=float(fuzzy_sim),
                )

                st.write("")
                # Reconciliation KPI Metrics
                k1, k2, k3, k4 = st.columns(4)
                with k1:
                    rate_color = "badge-emerald" if rec_summary.match_rate_percent >= 80 else "badge-amber"
                    st.markdown(
                        f"""
                        <div class="fintech-card">
                            <div class="card-header-flex">
                                <span class="card-title">Match Rate</span>
                                <div class="card-icon-badge {rate_color}">✓</div>
                            </div>
                            <div class="card-value">{rec_summary.match_rate_percent}%</div>
                            <div class="card-footer"><span>{rec_summary.matched_count} pairs matched</span></div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with k2:
                    st.markdown(
                        f"""
                        <div class="fintech-card">
                            <div class="card-header-flex">
                                <span class="card-title">Bank Statement Total</span>
                                <div class="card-icon-badge badge-blue">🏦</div>
                            </div>
                            <div class="card-value">₹{rec_summary.total_bank_amount:,.2f}</div>
                            <div class="card-footer"><span>{rec_summary.total_bank_count} transactions</span></div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with k3:
                    st.markdown(
                        f"""
                        <div class="fintech-card">
                            <div class="card-header-flex">
                                <span class="card-title">Company Ledger Total</span>
                                <div class="card-icon-badge badge-indigo">📖</div>
                            </div>
                            <div class="card-value">₹{rec_summary.total_ledger_amount:,.2f}</div>
                            <div class="card-footer"><span>{rec_summary.total_ledger_count} transactions</span></div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with k4:
                    disc = rec_summary.net_discrepancy
                    disc_badge = "badge-emerald" if disc == 0 else "badge-rose"
                    st.markdown(
                        f"""
                        <div class="fintech-card">
                            <div class="card-header-flex">
                                <span class="card-title">Net Discrepancy</span>
                                <div class="card-icon-badge {disc_badge}">Δ</div>
                            </div>
                            <div class="card-value">₹{disc:,.2f}</div>
                            <div class="card-footer"><span>Bank minus ledger</span></div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.write("")

                # Export Controls Row
                exp_c1, exp_c2, exp_c3 = st.columns([1, 1, 1.5])
                with exp_c1:
                    excel_bytes = rec.export_reconciliation_excel(
                        rec_summary,
                        matched_results,
                        unmatched_bank,
                        unmatched_ledger,
                        amount_mismatches,
                        bank_dups,
                    )
                    st.download_button(
                        label="📥 Export Report to Excel",
                        data=excel_bytes,
                        file_name=f"reconciliation_report_{date.today().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

                with exp_c2:
                    pdf_bytes = rec.export_reconciliation_pdf(
                        rec_summary,
                        matched_results,
                        unmatched_bank,
                        unmatched_ledger,
                        amount_mismatches,
                    )
                    st.download_button(
                        label="📄 Export Report to PDF",
                        data=pdf_bytes,
                        file_name=f"reconciliation_report_{date.today().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )

                with exp_c3:
                    if st.button("✨ AI Discrepancy Explanation", use_container_width=True):
                        st.session_state["run_ai_rec_explanation"] = True

                # AI Explanation Box (Optional)
                if st.session_state.get("run_ai_rec_explanation", False):
                    rec_explanation_context = f"""
Reconciliation Audit Results:
Match Rate: {rec_summary.match_rate_percent}%
Total Bank Transactions: {rec_summary.total_bank_count} (Total Value: ₹{rec_summary.total_bank_amount:,.2f})
Total Ledger Transactions: {rec_summary.total_ledger_count} (Total Value: ₹{rec_summary.total_ledger_amount:,.2f})
Successfully Matched: {rec_summary.matched_count}
Unmatched Bank Entries: {rec_summary.unmatched_bank_count}
Unmatched Ledger Entries: {rec_summary.unmatched_ledger_count}
Amount Mismatches: {rec_summary.amount_mismatch_count}
Potential Duplicates: {rec_summary.bank_duplicates_count}
Net Discrepancy: ₹{rec_summary.net_discrepancy:,.2f}

Sample Discrepancies:
{', '.join([f'{m.bank_tx.description}: Bank ₹{m.bank_amount} vs Ledger ₹{m.ledger_amount}' for m in amount_mismatches[:5]]) if amount_mismatches else 'None'}
"""
                    with st.spinner("Analyzing reconciliation variances with Gemini..."):
                        try:
                            ai_audit_notes = ai_service.generate_ai_insights(rec_explanation_context)
                            st.markdown(
                                f"""
                                <div class="ai-summary-box">
                                    <div style="font-size:14px;font-weight:700;color:#4F46E5;margin-bottom:8px;">
                                        ✦ Gemini Reconciliation Commentary
                                    </div>
                                    <div>{ai_audit_notes}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        except Exception as e:
                            st.error(f"AI explanation error: {e}")

                # Tabbed Results Breakdown
                st.write("")
                tab_m, tab_ub, tab_ul, tab_amm, tab_dup = st.tabs([
                    f"✓ Matched ({len(matched_results)})",
                    f"🏦 Unmatched Bank ({len(unmatched_bank)})",
                    f"📖 Unmatched Ledger ({len(unmatched_ledger)})",
                    f"⚠️ Amount Variances ({len(amount_mismatches)})",
                    f"🔁 Duplicates ({len(bank_dups)})",
                ])

                with tab_m:
                    if matched_results:
                        m_rows = []
                        for m in matched_results:
                            m_rows.append({
                                "Bank Date": str(m.bank_tx.date_val or ""),
                                "Bank Amount": format_currency(m.bank_tx.amount),
                                "Bank Description": m.bank_tx.description,
                                "Ledger Date": str(m.ledger_tx.date_val or ""),
                                "Ledger Amount": format_currency(m.ledger_tx.amount),
                                "Ledger Description": m.ledger_tx.description,
                                "Match Method": m.match_type,
                                "Confidence": f"{m.confidence}%",
                                "Date Delta": f"{m.date_diff_days}d",
                            })
                        st.dataframe(pd.DataFrame(m_rows), use_container_width=True, hide_index=True)
                    else:
                        st.info("No matched transactions found.")

                with tab_ub:
                    if unmatched_bank:
                        ub_rows = [
                            {
                                "Date": str(u.date_val or ""),
                                "Amount": format_currency(u.amount),
                                "Description": u.description,
                                "Reference": u.reference,
                                "Status": "Missing in Ledger",
                            }
                            for u in unmatched_bank
                        ]
                        st.dataframe(pd.DataFrame(ub_rows), use_container_width=True, hide_index=True)
                    else:
                        st.success("All bank statement transactions were successfully reconciled!")

                with tab_ul:
                    if unmatched_ledger:
                        ul_rows = [
                            {
                                "Date": str(u.date_val or ""),
                                "Amount": format_currency(u.amount),
                                "Description": u.description,
                                "Status": "Missing in Bank Statement",
                            }
                            for u in unmatched_ledger
                        ]
                        st.dataframe(pd.DataFrame(ul_rows), use_container_width=True, hide_index=True)
                    else:
                        st.success("All ledger records are reconciled against the bank statement!")

                with tab_amm:
                    if amount_mismatches:
                        amm_rows = [
                            {
                                "Date": str(a.bank_tx.date_val or ""),
                                "Bank Amount": format_currency(a.bank_amount),
                                "Ledger Amount": format_currency(a.ledger_amount),
                                "Variance": format_currency(a.difference),
                                "Description": a.bank_tx.description,
                                "Notes": a.notes,
                            }
                            for a in amount_mismatches
                        ]
                        st.dataframe(pd.DataFrame(amm_rows), use_container_width=True, hide_index=True)
                    else:
                        st.success("No amount discrepancies detected.")

                with tab_dup:
                    if bank_dups:
                        dup_rows = [
                            {
                                "Date": str(d.date_val or ""),
                                "Amount": format_currency(d.amount),
                                "Description": d.description,
                                "Source": "Bank Statement",
                            }
                            for d in bank_dups
                        ]
                        st.dataframe(pd.DataFrame(dup_rows), use_container_width=True, hide_index=True)
                    else:
                        st.info("No duplicate transaction patterns detected in the bank statement.")

        except Exception as exc:
            st.error(f"Reconciliation error: {exc}")
    else:
        st.markdown(
            """
            <div style="background:#FFFFFF;border:2px dashed #CBD5E1;border-radius:14px;padding:36px;text-align:center;">
                <div style="font-size:32px;margin-bottom:8px;">📁</div>
                <div style="font-size:16px;font-weight:700;color:#0F172A;margin-bottom:4px;">
                    Upload Bank Statement to Begin
                </div>
                <div style="font-size:13px;color:#64748B;max-width:500px;margin:0 auto;">
                    Upload your bank statement in CSV or XLSX format. LedgerLens AI will automatically detect columns, 
                    normalize amounts and dates, and match transactions against your company records.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# PAGE 4: AI INSIGHTS
# =========================================================

elif current_page == "AI Insights":

    st.markdown(
        """
        <div class="page-hero">
            <div class="hero-heading">AI Financial Intelligence & Insights</div>
            <div class="hero-subheading">
                Comprehensive financial health audit and strategic analysis powered by Google Gemini, 
                strictly grounded in your verified ledger records.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top KPI summary row
    k_col1, k_col2, k_col3 = st.columns(3)
    with k_col1:
        st.markdown(
            f"""
            <div class="fintech-card">
                <div class="card-header-flex">
                    <span class="card-title">Recorded Inflow</span>
                    <div class="card-icon-badge badge-emerald">↓</div>
                </div>
                <div class="card-value">{format_currency(current_metrics['income'])}</div>
                <div class="card-footer"><span>{len(filtered_df[filtered_df['type']=='Income'])} income entries</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k_col2:
        st.markdown(
            f"""
            <div class="fintech-card">
                <div class="card-header-flex">
                    <span class="card-title">Recorded Outflow</span>
                    <div class="card-icon-badge badge-rose">↑</div>
                </div>
                <div class="card-value">{format_currency(current_metrics['expenses'])}</div>
                <div class="card-footer"><span>{len(filtered_df[filtered_df['type']=='Expense'])} expense entries</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k_col3:
        st.markdown(
            f"""
            <div class="fintech-card">
                <div class="card-header-flex">
                    <span class="card-title">Retained Margin</span>
                    <div class="card-icon-badge badge-indigo">%</div>
                </div>
                <div class="card-value">{current_metrics['savings_rate']}%</div>
                <div class="card-footer"><span>Net: {format_currency(current_metrics['balance'])}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # Generate Insights Button
    if st.button("✨ Generate AI Strategic Audit", type="primary"):
        st.session_state["execute_ai_insights"] = True

    if st.session_state.get("execute_ai_insights", False):
        if filtered_df.empty:
            st.warning("No transactions recorded for the selected period. Add transactions to generate AI insights.")
        else:
            with st.spinner("Analyzing ledger with Google Gemini AI..."):
                try:
                    insights_text = ai_service.generate_ai_insights(financial_context)
                    st.markdown(
                        f"""
                        <div class="ai-summary-box">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                                <div style="color:#4F46E5;font-size:20px;">✦</div>
                                <div style="font-size:16px;font-weight:700;color:#0F172A;">
                                    Executive Financial Audit & Observations
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.markdown(insights_text)
                except Exception as err:
                    st.error(f"AI Generation Failed: {err}")
                    st.info(
                        "Please verify your Gemini API key in the **Settings** page. "
                        "You can test the connection in real-time or update your API key."
                    )
    else:
        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;padding:26px;margin-top:14px;">
                <div style="font-size:15px;font-weight:700;color:#0F172A;margin-bottom:6px;">
                    What this report includes:
                </div>
                <ul style="font-size:13.5px;color:#475569;line-height:1.8;padding-left:20px;">
                    <li><b>Executive Summary:</b> High-level breakdown of revenue, expenses, and retained capital.</li>
                    <li><b>Category Spending Patterns:</b> Identification of primary cost centers and concentration risks.</li>
                    <li><b>Cash Flow Observations:</b> Timing gaps between receipts and disbursements.</li>
                    <li><b>Strategic Recommendations:</b> Actionable suggestions to improve margins and reduce unnecessary expenditures.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# PAGE 5: AI ASSISTANT
# =========================================================

elif current_page == "AI Assistant":

    st.markdown(
        """
        <div class="page-hero">
            <div class="hero-heading">LedgerLens Financial Assistant</div>
            <div class="hero-subheading">
                Interact with your financial records in plain English. Get instant answers regarding expenses, income, trends, and specific counterparties.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Quick prompt pills
    st.markdown(
        """
        <div style="font-size:12px;font-weight:600;color:#64748B;text-transform:uppercase;margin-bottom:8px;">
            Suggested Questions
        </div>
        """,
        unsafe_allow_html=True,
    )

    q_col1, q_col2, q_col3, q_col4, q_col5 = st.columns(5)
    selected_prompt = None

    with q_col1:
        if st.button("💰 How much did I spend this month?", use_container_width=True):
            selected_prompt = "How much did I spend this month?"
    with q_col2:
        if st.button("📊 Largest expense category?", use_container_width=True):
            selected_prompt = "What is my largest expense category and what percentage is it?"
    with q_col3:
        if st.button("⚖️ Compare income & expenses", use_container_width=True):
            selected_prompt = "Compare my total income and expenses and explain the net margin."
    with q_col4:
        if st.button("🏦 How much did I save?", use_container_width=True):
            selected_prompt = "How much did I save this month, and what is my savings rate?"
    with q_col5:
        if st.button("🔍 Unusual transactions?", use_container_width=True):
            selected_prompt = "Identify any unusual or high-value transactions in the records."

    st.write("")

    # Chat session state
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    # Display Chat History
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_query = st.chat_input("Ask a question about your finances...")

    # Override if prompt pill clicked
    if selected_prompt:
        user_query = selected_prompt

    if user_query:
        st.session_state["chat_messages"].append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing ledger records..."):
                try:
                    assistant_reply = ai_service.chat_with_financial_assistant(
                        user_query=user_query,
                        conversation_history=st.session_state["chat_messages"][:-1],
                        financial_context=financial_context,
                    )
                    st.markdown(assistant_reply)
                    st.session_state["chat_messages"].append(
                        {"role": "assistant", "content": assistant_reply}
                    )
                except Exception as err:
                    err_msg = str(err)
                    st.error(err_msg)
                    st.session_state["chat_messages"].append(
                        {"role": "assistant", "content": f"⚠️ {err_msg}"}
                    )

    if st.session_state["chat_messages"]:
        st.write("")
        if st.button("Clear Conversation History"):
            st.session_state["chat_messages"] = []
            st.rerun()


# =========================================================
# PAGE 6: SETTINGS & DIAGNOSTICS
# =========================================================

elif current_page == "Settings":

    st.markdown(
        """
        <div class="page-hero">
            <div class="hero-heading">Settings & System Health</div>
            <div class="hero-subheading">
                Configure your Gemini API credentials, monitor diagnostic connection health, 
                and inspect database metrics.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    s_col1, s_col2 = st.columns(2)

    with s_col1:
        # API Connection & Testing
        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;padding:22px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size:16px;font-weight:700;color:#0F172A;margin-bottom:4px;">
                    🤖 Google Gemini API Configuration
                </div>
                <div style="font-size:13px;color:#64748B;margin-bottom:16px;">
                    LedgerLens AI uses the official Google GenAI Python SDK (google-genai) to power natural language financial reasoning.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        active_key = ai_service.get_api_key()
        active_model = ai_service.get_selected_model()

        status_badge = (
            "<span class='badge-income-pill'>Key Configured</span>"
            if active_key
            else "<span class='badge-expense-pill'>Key Missing</span>"
        )

        st.markdown(
            f"""
            <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:14px;margin-bottom:16px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="font-size:13px;color:#64748B;">API Status:</span>
                    {status_badge}
                </div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="font-size:13px;color:#64748B;">Masked Key:</span>
                    <span style="font-size:13px;font-family:monospace;font-weight:600;color:#0F172A;">{ai_service.mask_key(active_key)}</span>
                </div>
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-size:13px;color:#64748B;">Active Model:</span>
                    <span style="font-size:13px;font-family:monospace;font-weight:600;color:#4F46E5;">{active_model}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Live Test Connection Button
        if st.button("🧪 Test Gemini API Connection", type="primary", use_container_width=True):
            with st.spinner("Testing connection with Google Gemini endpoint..."):
                diag = ai_service.test_gemini_connection()
                if diag["success"]:
                    st.success(
                        f"✅ {diag['message']} (Response Latency: {diag['latency_ms']} ms)"
                    )
                else:
                    st.error(f"❌ {diag['status']}: {diag['message']}")
                    if "raw_error" in diag:
                        st.caption(f"Diagnostic details: {diag['raw_error']}")

        st.divider()

        # Update API Key Form
        st.markdown("<b>Update Gemini Credentials</b>", unsafe_allow_html=True)
        with st.form("update_api_key_form"):
            new_key_input = st.text_input(
                "Gemini API Key",
                type="password",
                placeholder="Paste new Gemini API key here...",
                help="Key will be securely saved into your local .env file",
            )
            model_options = ai_service.SUPPORTED_MODELS
            new_model_select = st.selectbox(
                "Select Model",
                model_options,
                index=model_options.index(active_model) if active_model in model_options else 0,
            )

            save_key_submit = st.form_submit_button("Save to .env File", use_container_width=True)

            if save_key_submit:
                if not new_key_input.strip():
                    st.error("Please enter a valid API key string.")
                else:
                    saved = ai_service.save_api_credentials(new_key_input.strip(), new_model_select)
                    if saved:
                        st.success("API credentials saved securely to .env!")
                        st.rerun()
                    else:
                        st.error("Could not write to .env file.")

    with s_col2:
        # System & Database Info
        db_details = get_database_info()

        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;padding:22px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size:16px;font-weight:700;color:#0F172A;margin-bottom:4px;">
                    🗄️ Database & Environment Information
                </div>
                <div style="font-size:13px;color:#64748B;margin-bottom:16px;">
                    Local persistence, integrity checks, and environment specs.
                </div>
                <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:14px;line-height:2;">
                    <div style="display:flex;justify-content:space-between;font-size:13px;">
                        <span style="color:#64748B;">Platform Engine:</span>
                        <b>LedgerLens AI Enterprise</b>
                    </div>
                    <div style="display:flex;justify-content:space-between;font-size:13px;">
                        <span style="color:#64748B;">Version:</span>
                        <b>v2.0.0 (Production)</b>
                    </div>
                    <div style="display:flex;justify-content:space-between;font-size:13px;">
                        <span style="color:#64748B;">Theme:</span>
                        <b>Fintech SaaS Light Theme</b>
                    </div>
                    <div style="display:flex;justify-content:space-between;font-size:13px;">
                        <span style="color:#64748B;">Database Engine:</span>
                        <b>SQLite 3 (ACID compliant)</b>
                    </div>
                    <div style="display:flex;justify-content:space-between;font-size:13px;">
                        <span style="color:#64748B;">Total Transactions:</span>
                        <b>{db_details['total_transactions']} records</b>
                    </div>
                    <div style="display:flex;justify-content:space-between;font-size:13px;">
                        <span style="color:#64748B;">Database Size:</span>
                        <b>{db_details['size_kb']} KB</b>
                    </div>
                    <div style="display:flex;justify-content:space-between;font-size:13px;overflow:hidden;text-overflow:ellipsis;">
                        <span style="color:#64748B;">File Path:</span>
                        <span style="font-family:monospace;font-size:11px;">{db_details['path']}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="background:#EEF2FF;border:1px solid #C7D2FE;border-radius:14px;padding:20px;">
                <div style="font-size:14px;font-weight:700;color:#3730A3;margin-bottom:6px;">
                    📖 How to obtain your Gemini API Key
                </div>
                <ol style="font-size:13px;color:#312E81;line-height:1.7;padding-left:18px;margin-bottom:0;">
                    <li>Navigate to <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color:#4F46E5;font-weight:600;">Google AI Studio</a>.</li>
                    <li>Sign in with your Google Workspace or personal Google account.</li>
                    <li>Click <b>Create API Key</b> and copy the generated token.</li>
                    <li>Paste the key into the form on the left or save it into your <code>.env</code> file under <code>GEMINI_API_KEY</code>.</li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )
