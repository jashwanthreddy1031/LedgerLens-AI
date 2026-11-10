"""
charts.py - Professional Plotly Financial Visualizations for LedgerLens AI.
Adheres strictly to the fintech light-theme design language:
- Off-white / Pure white backgrounds (#FFFFFF)
- Professional typography (Inter, sans-serif)
- Soft subtle gridlines (#E2E8F0)
- Purposeful color palette: Indigo (#4F46E5), Emerald (#10B981), Rose/Red (#EF4444), Slate (#64748B)
"""

from typing import Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go


# Design Constants
FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
COLOR_INCOME = "#10B981"    # Emerald green
COLOR_EXPENSE = "#EF4444"   # Muted rose/red
COLOR_PRIMARY = "#4F46E5"   # Professional indigo
COLOR_SECONDARY = "#3B82F6" # Soft blue
COLOR_TEXT_MAIN = "#0F172A" # Dark slate
COLOR_TEXT_MUTED = "#64748B"# Slate gray
COLOR_GRID = "#F1F5F9"      # Very subtle light gray
COLOR_BORDER = "#E2E8F0"
COLOR_BG = "rgba(0,0,0,0)"

BASE_LAYOUT = dict(
    font=dict(family=FONT_FAMILY, color=COLOR_TEXT_MAIN, size=12),
    plot_bgcolor=COLOR_BG,
    paper_bgcolor=COLOR_BG,
    margin=dict(l=40, r=20, t=35, b=35),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=11, color=COLOR_TEXT_MUTED),
    ),
    hoverlabel=dict(
        bgcolor="#FFFFFF",
        font=dict(family=FONT_FAMILY, size=12, color=COLOR_TEXT_MAIN),
        bordercolor=COLOR_BORDER,
    ),
)


def empty_state_figure(message: str = "No financial data available for this range") -> go.Figure:
    """Return an elegant empty state placeholder chart."""
    fig = go.Figure()
    fig.add_annotation(
        text=f"📊 {message}",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(family=FONT_FAMILY, size=13, color=COLOR_TEXT_MUTED),
    )
    fig.update_layout(
        **BASE_LAYOUT,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        height=320,
    )
    return fig


def create_income_vs_expense_chart(df: pd.DataFrame) -> go.Figure:
    """
    Chart A: Modern grouped bar chart comparing monthly Income vs Expenses.
    Rounded style with interactive tooltips and currency formatting.
    """
    if df.empty or "date" not in df.columns or "amount" not in df.columns:
        return empty_state_figure("No transactions recorded for Income vs Expense comparison")

    work_df = df.copy()
    work_df["month"] = pd.to_datetime(work_df["date"]).dt.to_period("M").dt.to_timestamp()

    monthly = (
        work_df.groupby(["month", "type"])["amount"]
        .sum()
        .unstack(fill_value=0.0)
        .reset_index()
    )

    if "Income" not in monthly.columns:
        monthly["Income"] = 0.0
    if "Expense" not in monthly.columns:
        monthly["Expense"] = 0.0

    monthly["month_label"] = monthly["month"].dt.strftime("%b %Y")

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Income",
            x=monthly["month_label"],
            y=monthly["Income"],
            marker=dict(color=COLOR_INCOME, cornerradius=4),
            hovertemplate="<b>%{x}</b><br>Income: ₹%{y:,.2f}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Expenses",
            x=monthly["month_label"],
            y=monthly["Expense"],
            marker=dict(color=COLOR_EXPENSE, cornerradius=4),
            hovertemplate="<b>%{x}</b><br>Expenses: ₹%{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        **BASE_LAYOUT,
        barmode="group",
        bargap=0.25,
        bargroupgap=0.1,
        height=340,
        xaxis=dict(
            title="",
            tickfont=dict(size=11, color=COLOR_TEXT_MUTED),
            gridcolor=COLOR_GRID,
            linecolor=COLOR_BORDER,
        ),
        yaxis=dict(
            title="",
            tickprefix="₹",
            tickformat=",.0f",
            tickfont=dict(size=11, color=COLOR_TEXT_MUTED),
            gridcolor=COLOR_GRID,
            zeroline=True,
            zerolinecolor=COLOR_BORDER,
        ),
    )
    return fig


def create_cash_flow_trend_chart(df: pd.DataFrame) -> go.Figure:
    """
    Chart B: Professional line chart displaying daily or weekly cumulative cash flow.
    Includes smooth lines and subtle translucent gradient fill.
    """
    if df.empty or "date" not in df.columns:
        return empty_state_figure("No transactions available for cash flow trends")

    work_df = df.copy()
    work_df["date"] = pd.to_datetime(work_df["date"])
    
    # Aggregate daily
    daily = (
        work_df.groupby(["date", "type"])["amount"]
        .sum()
        .unstack(fill_value=0.0)
        .reset_index()
    )
    if "Income" not in daily.columns:
        daily["Income"] = 0.0
    if "Expense" not in daily.columns:
        daily["Expense"] = 0.0

    daily = daily.sort_values("date")
    daily["date_label"] = daily["date"].dt.strftime("%d %b")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["Income"],
            mode="lines+markers",
            name="Daily Income",
            line=dict(color=COLOR_INCOME, width=2.5, shape="spline"),
            marker=dict(size=5, color=COLOR_INCOME),
            fill="tozeroy",
            fillcolor="rgba(16, 185, 129, 0.08)",
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Income: ₹%{y:,.2f}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["Expense"],
            mode="lines+markers",
            name="Daily Expenses",
            line=dict(color=COLOR_EXPENSE, width=2.5, shape="spline"),
            marker=dict(size=5, color=COLOR_EXPENSE),
            fill="tozeroy",
            fillcolor="rgba(239, 68, 68, 0.08)",
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Expenses: ₹%{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        **BASE_LAYOUT,
        height=340,
        xaxis=dict(
            title="",
            tickformat="%d %b",
            tickfont=dict(size=11, color=COLOR_TEXT_MUTED),
            gridcolor=COLOR_GRID,
            linecolor=COLOR_BORDER,
        ),
        yaxis=dict(
            title="",
            tickprefix="₹",
            tickformat=",.0f",
            tickfont=dict(size=11, color=COLOR_TEXT_MUTED),
            gridcolor=COLOR_GRID,
            zeroline=True,
            zerolinecolor=COLOR_BORDER,
        ),
    )
    return fig


def create_expense_breakdown_chart(df: pd.DataFrame) -> go.Figure:
    """
    Chart C: Modern donut chart showing category-wise expense distribution.
    Features center label displaying total expenses, currency hover, and clean palette.
    """
    expense_df = df[df["type"] == "Expense"] if not df.empty else pd.DataFrame()
    
    if expense_df.empty or "amount" not in expense_df.columns:
        return empty_state_figure("No expense entries found for category breakdown")

    cat_totals = (
        expense_df.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    total_expense = cat_totals["amount"].sum()
    if total_expense <= 0:
        return empty_state_figure("Total expenses are ₹0.00")

    # If more than 7 categories, group minor ones into "Other"
    if len(cat_totals) > 7:
        top_cats = cat_totals.head(6).copy()
        other_amt = cat_totals["amount"].iloc[6:].sum()
        other_row = pd.DataFrame([{"category": "Other Categories", "amount": other_amt}])
        cat_totals = pd.concat([top_cats, other_row], ignore_index=True)

    # Modern fintech color palette for categories
    colors = [
        "#4F46E5", "#3B82F6", "#06B6D4", "#10B981",
        "#F59E0B", "#EC4899", "#8B5CF6", "#64748B"
    ]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=cat_totals["category"],
                values=cat_totals["amount"],
                hole=0.68,
                marker=dict(colors=colors[: len(cat_totals)], line=dict(color="#FFFFFF", width=2)),
                textinfo="percent",
                textfont=dict(size=11, family=FONT_FAMILY),
                hovertemplate="<b>%{label}</b><br>Amount: ₹%{value:,.2f}<br>Share: %{percent}<extra></extra>",
                sort=False,
            )
        ]
    )

    layout_args = {k: v for k, v in BASE_LAYOUT.items() if k != "legend"}
    fig.update_layout(
        **layout_args,
        height=340,
        annotations=[
            dict(
                text=f"<span style='font-size:11px;color:{COLOR_TEXT_MUTED};'>TOTAL</span><br><b style='font-size:15px;color:{COLOR_TEXT_MAIN};'>₹{total_expense:,.0f}</b>",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(family=FONT_FAMILY),
            )
        ],
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=11, color=COLOR_TEXT_MUTED),
        ),
    )
    return fig


def create_monthly_performance_chart(df: pd.DataFrame) -> go.Figure:
    """
    Chart D: Monthly financial net performance (savings / deficit).
    Differentiates positive (green) and negative (red) bars from zero baseline.
    """
    if df.empty or "date" not in df.columns or "amount" not in df.columns:
        return empty_state_figure("No transactions available for monthly net savings")

    work_df = df.copy()
    work_df["month"] = pd.to_datetime(work_df["date"]).dt.to_period("M").dt.to_timestamp()

    monthly = (
        work_df.groupby(["month", "type"])["amount"]
        .sum()
        .unstack(fill_value=0.0)
        .reset_index()
    )

    if "Income" not in monthly.columns:
        monthly["Income"] = 0.0
    if "Expense" not in monthly.columns:
        monthly["Expense"] = 0.0

    monthly["Net"] = monthly["Income"] - monthly["Expense"]
    monthly["month_label"] = monthly["month"].dt.strftime("%b %Y")

    colors = [COLOR_INCOME if val >= 0 else COLOR_EXPENSE for val in monthly["Net"]]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=monthly["month_label"],
            y=monthly["Net"],
            marker=dict(color=colors, cornerradius=4),
            hovertemplate="<b>%{x}</b><br>Net Result: ₹%{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        **BASE_LAYOUT,
        showlegend=False,
        height=340,
        xaxis=dict(
            title="",
            tickfont=dict(size=11, color=COLOR_TEXT_MUTED),
            gridcolor=COLOR_GRID,
            linecolor=COLOR_BORDER,
        ),
        yaxis=dict(
            title="",
            tickprefix="₹",
            tickformat=",.0f",
            tickfont=dict(size=11, color=COLOR_TEXT_MUTED),
            gridcolor=COLOR_GRID,
            zeroline=True,
            zerolinecolor=COLOR_TEXT_MAIN,
            zerolinewidth=1.5,
        ),
    )
    return fig
