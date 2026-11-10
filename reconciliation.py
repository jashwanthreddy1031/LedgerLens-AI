"""
reconciliation.py - Deterministic Financial Reconciliation Engine for LedgerLens AI.
Performs smart column detection, date/amount normalization, exact and fuzzy matching,
discrepancy detection, duplicate analysis, and report generation (Excel & PDF).
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import difflib
import io
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from fpdf import FPDF


# =========================================================
# DATA STRUCTURES
# =========================================================

@dataclass
class NormalizedTransaction:
    raw_id: str
    source: str  # "bank" or "ledger"
    date_val: Optional[date]
    amount: float  # Positive for inflow / credit, negative for outflow / debit, or absolute depending on reconciliation mode
    description: str
    reference: str
    original_row: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MatchResult:
    bank_tx: NormalizedTransaction
    ledger_tx: NormalizedTransaction
    match_type: str  # "EXACT", "REFERENCE", "FUZZY_DATE_AMOUNT"
    confidence: float  # 0 to 100
    date_diff_days: int
    amount_diff: float
    notes: str


@dataclass
class AmountMismatch:
    bank_tx: NormalizedTransaction
    ledger_tx: NormalizedTransaction
    bank_amount: float
    ledger_amount: float
    difference: float
    date_diff_days: int
    similarity: float
    notes: str


@dataclass
class ReconciliationSummary:
    total_bank_count: int
    total_ledger_count: int
    matched_count: int
    unmatched_bank_count: int
    unmatched_ledger_count: int
    amount_mismatch_count: int
    bank_duplicates_count: int
    ledger_duplicates_count: int
    total_bank_amount: float
    total_ledger_amount: float
    matched_amount: float
    net_discrepancy: float
    match_rate_percent: float


# =========================================================
# NORMALIZATION & COLUMN DETECTION
# =========================================================

DATE_COL_NAMES = ["date", "txn_date", "trans_date", "booking_date", "value_date", "transaction_date", "posted_date"]
DESC_COL_NAMES = ["description", "narration", "particulars", "memo", "details", "payee", "remarks", "name", "category"]
AMOUNT_COL_NAMES = ["amount", "txn_amount", "net_amount", "total", "value"]
DEBIT_COL_NAMES = ["debit", "withdrawal", "dr", "expense", "paid_out", "outflow"]
CREDIT_COL_NAMES = ["credit", "deposit", "cr", "income", "paid_in", "inflow"]
REF_COL_NAMES = ["reference", "ref", "ref_no", "chq_no", "cheque_no", "utr", "txn_id", "transaction_id", "id"]


def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Automatically detect column roles from DataFrame header names."""
    cols = {str(c).lower().strip(): c for c in df.columns}
    
    mapping = {
        "date": None,
        "description": None,
        "amount": None,
        "debit": None,
        "credit": None,
        "reference": None,
    }

    for norm_name, original_col in cols.items():
        clean_name = re.sub(r"[^a-z0-9]", "", norm_name)
        
        if not mapping["date"] and any(d in clean_name for d in ["date", "time"]):
            mapping["date"] = original_col
        elif not mapping["description"] and any(d in clean_name for d in ["desc", "narrat", "partic", "memo", "remark", "detail", "payee"]):
            mapping["description"] = original_col
        elif not mapping["debit"] and any(d in clean_name for d in ["debit", "withdraw"]):
            mapping["debit"] = original_col
        elif not mapping["credit"] and any(d in clean_name for d in ["credit", "deposit"]):
            mapping["credit"] = original_col
        elif not mapping["amount"] and any(d in clean_name for d in ["amount", "total", "val"]):
            mapping["amount"] = original_col
        elif not mapping["reference"] and any(d in clean_name for d in ["ref", "chq", "cheque", "utr", "txnid"]):
            mapping["reference"] = original_col

    # Fallbacks if columns are not named typically
    if not mapping["date"] and len(df.columns) > 0:
        for c in df.columns:
            sample = df[c].dropna().head(5)
            if not sample.empty and pd.to_datetime(sample, errors="coerce").notnull().all():
                mapping["date"] = c
                break

    if not mapping["amount"] and not (mapping["debit"] and mapping["credit"]):
        for c in df.columns:
            if c != mapping["date"]:
                sample = df[c].dropna().head(5)
                # check numeric
                try:
                    pd.to_numeric(sample.astype(str).str.replace(r"[^\d.-]", "", regex=True))
                    mapping["amount"] = c
                    break
                except Exception:
                    pass

    return mapping


def parse_clean_amount(val: Any) -> float:
    """Normalize any string, float, or integer into a standard float with 2 decimal rounding."""
    if val is None or pd.isna(val):
        return 0.0
    s = str(val).strip()
    if not s:
        return 0.0
    
    # Handle accounting parentheses: (1,234.50) -> -1234.50
    is_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1]
    elif s.endswith("-"):
        is_negative = True
        s = s[:-1]
    elif s.startswith("-"):
        is_negative = True
        s = s[1:]

    # Remove currency symbols and formatting commas
    cleaned = re.sub(r"[^\d.]", "", s)
    if not cleaned:
        return 0.0
    try:
        dec = Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        result = float(dec)
        return -result if is_negative else result
    except Exception:
        return 0.0


def parse_clean_date(val: Any) -> Optional[date]:
    """Parse various date formats robustly into a datetime.date object."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if not s:
        return None
    
    # If matches ISO YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            pass

    # Try standard dateutil/pandas parsing
    try:
        dt = pd.to_datetime(s, dayfirst=True)
        if pd.notnull(dt):
            return dt.date()
    except Exception:
        pass
    
    try:
        dt = pd.to_datetime(s, dayfirst=False)
        if pd.notnull(dt):
            return dt.date()
    except Exception:
        pass

    return None


def normalize_transactions(
    df: pd.DataFrame, source_name: str, col_mapping: Dict[str, Optional[str]]
) -> List[NormalizedTransaction]:
    """Convert raw DataFrame into standardized NormalizedTransaction objects."""
    records: List[NormalizedTransaction] = []
    
    date_col = col_mapping.get("date")
    desc_col = col_mapping.get("description")
    amt_col = col_mapping.get("amount")
    deb_col = col_mapping.get("debit")
    cred_col = col_mapping.get("credit")
    ref_col = col_mapping.get("reference")

    for idx, row in df.iterrows():
        # Date
        d_val = parse_clean_date(row[date_col]) if date_col and date_col in row else None
        
        # Amount calculation
        amount = 0.0
        if deb_col and cred_col and deb_col in row and cred_col in row:
            deb_amt = parse_clean_amount(row[deb_col])
            cred_amt = parse_clean_amount(row[cred_col])
            # If credit is present, positive. If debit is present, positive or negative
            if cred_amt > 0:
                amount = cred_amt
            elif deb_amt > 0:
                amount = deb_amt  # Keep positive magnitude for matching
            else:
                amount = 0.0
        elif amt_col and amt_col in row:
            amount = abs(parse_clean_amount(row[amt_col]))
        
        # Skip empty rows with no amount and no date
        if amount == 0.0 and d_val is None:
            continue

        # Description
        description = str(row[desc_col]).strip() if desc_col and desc_col in row and pd.notnull(row[desc_col]) else ""
        
        # Reference
        reference = str(row[ref_col]).strip() if ref_col and ref_col in row and pd.notnull(row[ref_col]) else ""

        tx = NormalizedTransaction(
            raw_id=f"{source_name}_{idx + 1}",
            source=source_name,
            date_val=d_val,
            amount=round(amount, 2),
            description=description,
            reference=reference,
            original_row=dict(row),
        )
        records.append(tx)

    return records


# =========================================================
# RECONCILIATION MATCHING ENGINE
# =========================================================

def string_similarity(s1: str, s2: str) -> float:
    """Calculate fuzzy text similarity between 0 and 100."""
    clean1 = re.sub(r"[^a-z0-9]", "", s1.lower())
    clean2 = re.sub(r"[^a-z0-9]", "", s2.lower())
    if not clean1 or not clean2:
        return 0.0
    if clean1 == clean2:
        return 100.0
    if clean1 in clean2 or clean2 in clean1:
        return 85.0
    return round(difflib.SequenceMatcher(None, clean1, clean2).ratio() * 100, 1)


def detect_duplicates(transactions: List[NormalizedTransaction]) -> List[NormalizedTransaction]:
    """Identify duplicate transactions within a single source list."""
    duplicates: List[NormalizedTransaction] = []
    seen = {}
    for tx in transactions:
        key = (tx.date_val, tx.amount, tx.description.lower().strip())
        if key in seen:
            duplicates.append(tx)
        else:
            seen[key] = tx
    return duplicates


def run_reconciliation(
    bank_txs: List[NormalizedTransaction],
    ledger_txs: List[NormalizedTransaction],
    date_tolerance_days: int = 3,
    fuzzy_threshold: float = 70.0,
) -> Tuple[
    List[MatchResult],
    List[NormalizedTransaction],
    List[NormalizedTransaction],
    List[AmountMismatch],
    List[NormalizedTransaction],
    List[NormalizedTransaction],
    ReconciliationSummary,
]:
    """
    Deterministic financial reconciliation engine.
    Matches transactions using multi-pass heuristic ranking:
    Pass 1: Exact Reference Match (if reference is present)
    Pass 2: Exact Amount and Exact Date Match
    Pass 3: Exact Amount and Date within tolerance (ranking by description similarity)
    Pass 4: Amount Mismatch Detection (Same reference or high text match with date tolerance)
    """
    matched_results: List[MatchResult] = []
    amount_mismatches: List[AmountMismatch] = []
    
    bank_matched_ids = set()
    ledger_matched_ids = set()

    # Detect duplicates before reconciliation
    bank_duplicates = detect_duplicates(bank_txs)
    ledger_duplicates = detect_duplicates(ledger_txs)

    # -------------------------------------------------------------
    # Pass 1: Exact Reference Matching (when reference is non-empty)
    # -------------------------------------------------------------
    for b_tx in bank_txs:
        if b_tx.raw_id in bank_matched_ids or not b_tx.reference:
            continue
        for l_tx in ledger_txs:
            if l_tx.raw_id in ledger_matched_ids or not l_tx.reference:
                continue
            if b_tx.reference.lower() == l_tx.reference.lower():
                days_diff = (
                    abs((b_tx.date_val - l_tx.date_val).days)
                    if b_tx.date_val and l_tx.date_val
                    else 0
                )
                amt_diff = round(abs(b_tx.amount - l_tx.amount), 2)
                
                if amt_diff == 0.0:
                    matched_results.append(
                        MatchResult(
                            bank_tx=b_tx,
                            ledger_tx=l_tx,
                            match_type="REFERENCE_EXACT",
                            confidence=100.0,
                            date_diff_days=days_diff,
                            amount_diff=0.0,
                            notes=f"Exact reference match '{b_tx.reference}' with exact amount.",
                        )
                    )
                    bank_matched_ids.add(b_tx.raw_id)
                    ledger_matched_ids.add(l_tx.raw_id)
                    break
                elif days_diff <= date_tolerance_days:
                    amount_mismatches.append(
                        AmountMismatch(
                            bank_tx=b_tx,
                            ledger_tx=l_tx,
                            bank_amount=b_tx.amount,
                            ledger_amount=l_tx.amount,
                            difference=round(b_tx.amount - l_tx.amount, 2),
                            date_diff_days=days_diff,
                            similarity=100.0,
                            notes=f"Reference match '{b_tx.reference}' but amount differs by ₹{amt_diff:.2f}.",
                        )
                    )
                    bank_matched_ids.add(b_tx.raw_id)
                    ledger_matched_ids.add(l_tx.raw_id)
                    break

    # -------------------------------------------------------------
    # Pass 2: Exact Amount & Exact Date Matching
    # -------------------------------------------------------------
    for b_tx in bank_txs:
        if b_tx.raw_id in bank_matched_ids:
            continue
        best_candidate = None
        highest_sim = -1.0

        for l_tx in ledger_txs:
            if l_tx.raw_id in ledger_matched_ids:
                continue
            if b_tx.amount == l_tx.amount and b_tx.date_val == l_tx.date_val and b_tx.date_val is not None:
                sim = string_similarity(b_tx.description, l_tx.description)
                if sim > highest_sim:
                    highest_sim = sim
                    best_candidate = l_tx

        if best_candidate is not None:
            matched_results.append(
                MatchResult(
                    bank_tx=b_tx,
                    ledger_tx=best_candidate,
                    match_type="EXACT_DATE_AMOUNT",
                    confidence=round(90.0 + (highest_sim * 0.1), 1),
                    date_diff_days=0,
                    amount_diff=0.0,
                    notes=f"Exact date & amount match (Description similarity: {highest_sim}%).",
                )
            )
            bank_matched_ids.add(b_tx.raw_id)
            ledger_matched_ids.add(best_candidate.raw_id)

    # -------------------------------------------------------------
    # Pass 3: Exact Amount with Date Tolerance & Fuzzy Description
    # -------------------------------------------------------------
    for b_tx in bank_txs:
        if b_tx.raw_id in bank_matched_ids:
            continue
        best_candidate = None
        best_score = -1.0
        best_days = 999

        for l_tx in ledger_txs:
            if l_tx.raw_id in ledger_matched_ids:
                continue
            if b_tx.amount == l_tx.amount and b_tx.date_val and l_tx.date_val:
                days_diff = abs((b_tx.date_val - l_tx.date_val).days)
                if days_diff <= date_tolerance_days:
                    sim = string_similarity(b_tx.description, l_tx.description)
                    # Heuristic score combining date proximity and description similarity
                    score = (100 - (days_diff * 10)) * 0.4 + (sim * 0.6)
                    if score > best_score and (sim >= fuzzy_threshold or days_diff <= 1):
                        best_score = score
                        best_candidate = l_tx
                        best_days = days_diff

        if best_candidate is not None:
            matched_results.append(
                MatchResult(
                    bank_tx=b_tx,
                    ledger_tx=best_candidate,
                    match_type="TOLERANCE_MATCH",
                    confidence=round(max(70.0, min(95.0, best_score)), 1),
                    date_diff_days=best_days,
                    amount_diff=0.0,
                    notes=f"Matched within {best_days} day(s) tolerance (Score: {best_score:.1f}).",
                )
            )
            bank_matched_ids.add(b_tx.raw_id)
            ledger_matched_ids.add(best_candidate.raw_id)

    # -------------------------------------------------------------
    # Pass 4: Amount Mismatch Detection (Fuzzy Description & Close Date)
    # -------------------------------------------------------------
    for b_tx in bank_txs:
        if b_tx.raw_id in bank_matched_ids:
            continue
        for l_tx in ledger_txs:
            if l_tx.raw_id in ledger_matched_ids:
                continue
            if b_tx.date_val and l_tx.date_val:
                days_diff = abs((b_tx.date_val - l_tx.date_val).days)
                if days_diff <= date_tolerance_days:
                    sim = string_similarity(b_tx.description, l_tx.description)
                    if sim >= 80.0 and b_tx.amount != l_tx.amount:
                        amount_mismatches.append(
                            AmountMismatch(
                                bank_tx=b_tx,
                                ledger_tx=l_tx,
                                bank_amount=b_tx.amount,
                                ledger_amount=l_tx.amount,
                                difference=round(b_tx.amount - l_tx.amount, 2),
                                date_diff_days=days_diff,
                                similarity=sim,
                                notes=f"High description similarity ({sim}%) within {days_diff}d but amounts differ.",
                            )
                        )
                        bank_matched_ids.add(b_tx.raw_id)
                        ledger_matched_ids.add(l_tx.raw_id)
                        break

    # Unmatched
    unmatched_bank = [b for b in bank_txs if b.raw_id not in bank_matched_ids]
    unmatched_ledger = [l for l in ledger_txs if l.raw_id not in ledger_matched_ids]

    # Metrics Summary
    total_bank_amt = sum(b.amount for b in bank_txs)
    total_ledger_amt = sum(l.amount for l in ledger_txs)
    matched_amt = sum(m.bank_tx.amount for m in matched_results)
    
    total_tx_count = len(bank_txs) + len(ledger_txs)
    matched_count = len(matched_results)
    match_rate = (
        round((matched_count * 2 / total_tx_count) * 100, 1)
        if total_tx_count > 0
        else 0.0
    )

    summary = ReconciliationSummary(
        total_bank_count=len(bank_txs),
        total_ledger_count=len(ledger_txs),
        matched_count=matched_count,
        unmatched_bank_count=len(unmatched_bank),
        unmatched_ledger_count=len(unmatched_ledger),
        amount_mismatch_count=len(amount_mismatches),
        bank_duplicates_count=len(bank_duplicates),
        ledger_duplicates_count=len(ledger_duplicates),
        total_bank_amount=round(total_bank_amt, 2),
        total_ledger_amount=round(total_ledger_amt, 2),
        matched_amount=round(matched_amt, 2),
        net_discrepancy=round(total_bank_amt - total_ledger_amt, 2),
        match_rate_percent=match_rate,
    )

    return (
        matched_results,
        unmatched_bank,
        unmatched_ledger,
        amount_mismatches,
        bank_duplicates,
        ledger_duplicates,
        summary,
    )


# =========================================================
# EXCEL AND PDF EXPORT FUNCTIONS
# =========================================================

def export_reconciliation_excel(
    summary: ReconciliationSummary,
    matched_results: List[MatchResult],
    unmatched_bank: List[NormalizedTransaction],
    unmatched_ledger: List[NormalizedTransaction],
    amount_mismatches: List[AmountMismatch],
    bank_duplicates: List[NormalizedTransaction],
) -> bytes:
    """Generate a multi-sheet, beautifully styled Excel reconciliation report."""
    wb = Workbook()
    
    # Styles
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
    title_font = Font(name="Calibri", size=14, bold=True, color="0F172A")
    subtitle_font = Font(name="Calibri", size=10, italic=True, color="64748B")
    border_side = Side(border_style="thin", color="E2E8F0")
    cell_border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)
    
    # 1. Summary Sheet
    ws_sum = wb.active
    ws_sum.title = "Reconciliation Summary"
    ws_sum.views.sheetView[0].showGridLines = True
    
    ws_sum["A1"] = "LedgerLens AI - Financial Reconciliation Report"
    ws_sum["A1"].font = title_font
    ws_sum["A2"] = f"Generated on {date.today().strftime('%d %B %Y')} | Status: Complete"
    ws_sum["A2"].font = subtitle_font
    
    metrics = [
        ("Metric", "Value"),
        ("Match Rate", f"{summary.match_rate_percent}%"),
        ("Total Bank Transactions", summary.total_bank_count),
        ("Total Ledger Transactions", summary.total_ledger_count),
        ("Successfully Matched Pairs", summary.matched_count),
        ("Unmatched Bank Entries", summary.unmatched_bank_count),
        ("Unmatched Ledger Entries", summary.unmatched_ledger_count),
        ("Amount Mismatches Detected", summary.amount_mismatch_count),
        ("Bank Potential Duplicates", summary.bank_duplicates_count),
        ("Total Bank Value", f"₹{summary.total_bank_amount:,.2f}"),
        ("Total Ledger Value", f"₹{summary.total_ledger_amount:,.2f}"),
        ("Total Reconciled Value", f"₹{summary.matched_amount:,.2f}"),
        ("Net Discrepancy (Bank - Ledger)", f"₹{summary.net_discrepancy:,.2f}"),
    ]
    
    for row_idx, (m_label, m_val) in enumerate(metrics, start=4):
        c1 = ws_sum.cell(row=row_idx, column=1, value=m_label)
        c2 = ws_sum.cell(row=row_idx, column=2, value=m_val)
        c1.border = cell_border
        c2.border = cell_border
        if row_idx == 4:
            c1.font = header_font
            c1.fill = header_fill
            c2.font = header_font
            c2.fill = header_fill
        else:
            c1.font = Font(name="Calibri", size=10, bold=True)
            c2.font = Font(name="Calibri", size=10)
    
    ws_sum.column_dimensions["A"].width = 34
    ws_sum.column_dimensions["B"].width = 24

    # 2. Matched Sheet
    ws_match = wb.create_sheet(title="Matched Transactions")
    ws_match.views.sheetView[0].showGridLines = True
    headers = [
        "Bank Date", "Bank Amount (₹)", "Bank Description", "Bank Ref",
        "Ledger Date", "Ledger Amount (₹)", "Ledger Description",
        "Match Type", "Confidence", "Date Diff (Days)", "Notes"
    ]
    for col_idx, h in enumerate(headers, start=1):
        cell = ws_match.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = cell_border

    for row_idx, m in enumerate(matched_results, start=2):
        row_data = [
            str(m.bank_tx.date_val or ""),
            m.bank_tx.amount,
            m.bank_tx.description,
            m.bank_tx.reference,
            str(m.ledger_tx.date_val or ""),
            m.ledger_tx.amount,
            m.ledger_tx.description,
            m.match_type,
            f"{m.confidence}%",
            m.date_diff_days,
            m.notes,
        ]
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws_match.cell(row=row_idx, column=col_idx, value=val)
            cell.border = cell_border
            cell.font = Font(name="Calibri", size=10)
            if col_idx in [2, 6]:
                cell.number_format = "#,##0.00"

    for col in ws_match.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        ws_match.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 12)

    # 3. Unmatched Bank Sheet
    ws_ub = wb.create_sheet(title="Unmatched Bank")
    ub_headers = ["Bank Date", "Amount (₹)", "Description", "Reference", "Status"]
    for col_idx, h in enumerate(ub_headers, start=1):
        cell = ws_ub.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = cell_border

    for row_idx, tx in enumerate(unmatched_bank, start=2):
        row_data = [str(tx.date_val or ""), tx.amount, tx.description, tx.reference, "Missing in Ledger"]
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws_ub.cell(row=row_idx, column=col_idx, value=val)
            cell.border = cell_border
            cell.font = Font(name="Calibri", size=10)
            if col_idx == 2:
                cell.number_format = "#,##0.00"

    for col in ws_ub.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        ws_ub.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 14)

    # 4. Unmatched Ledger Sheet
    ws_ul = wb.create_sheet(title="Unmatched Ledger")
    ul_headers = ["Ledger Date", "Amount (₹)", "Description", "Status"]
    for col_idx, h in enumerate(ul_headers, start=1):
        cell = ws_ul.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = cell_border

    for row_idx, tx in enumerate(unmatched_ledger, start=2):
        row_data = [str(tx.date_val or ""), tx.amount, tx.description, "Missing in Bank Statement"]
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws_ul.cell(row=row_idx, column=col_idx, value=val)
            cell.border = cell_border
            cell.font = Font(name="Calibri", size=10)
            if col_idx == 2:
                cell.number_format = "#,##0.00"

    for col in ws_ul.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        ws_ul.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 14)

    # 5. Amount Mismatches Sheet
    if amount_mismatches:
        ws_amm = wb.create_sheet(title="Amount Discrepancies")
        amm_headers = [
            "Bank Date", "Bank Amount (₹)", "Bank Description",
            "Ledger Date", "Ledger Amount (₹)", "Ledger Description",
            "Variance (₹)", "Notes"
        ]
        for col_idx, h in enumerate(amm_headers, start=1):
            cell = ws_amm.cell(row=1, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = PatternFill(start_color="EF4444", end_color="EF4444", fill_type="solid")
            cell.border = cell_border

        for row_idx, m in enumerate(amount_mismatches, start=2):
            row_data = [
                str(m.bank_tx.date_val or ""),
                m.bank_amount,
                m.bank_tx.description,
                str(m.ledger_tx.date_val or ""),
                m.ledger_amount,
                m.ledger_tx.description,
                m.difference,
                m.notes,
            ]
            for col_idx, val in enumerate(row_data, start=1):
                cell = ws_amm.cell(row=row_idx, column=col_idx, value=val)
                cell.border = cell_border
                cell.font = Font(name="Calibri", size=10)
                if col_idx in [2, 5, 7]:
                    cell.number_format = "#,##0.00"

        for col in ws_amm.columns:
            max_len = max(len(str(c.value or "")) for c in col)
            ws_amm.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 14)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


class ReconciliationPDF(FPDF):
    """Custom clean PDF layout for LedgerLens AI reports."""

    def header(self):
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(15, 23, 42)  # Dark slate
        self.cell(0, 8, "LedgerLens AI - Reconciliation Report", align="L")
        self.ln(8)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 116, 139)  # Slate gray
        self.cell(0, 5, f"Automated Deterministic Financial Audit - Generated on {date.today().strftime('%d %b %Y')}", align="L")
        self.ln(6)
        self.line(10, 26, 200, 26)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"LedgerLens AI | Confidential | Page {self.page_no()}/{{nb}}", align="C")


def export_reconciliation_pdf(
    summary: ReconciliationSummary,
    matched_results: List[MatchResult],
    unmatched_bank: List[NormalizedTransaction],
    unmatched_ledger: List[NormalizedTransaction],
    amount_mismatches: List[AmountMismatch],
) -> bytes:
    """Generate a clean, high-density PDF reconciliation statement."""
    pdf = ReconciliationPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Section 1: Executive KPI Summary Box
    pdf.set_fill_color(248, 250, 252)  # Light theme slate-50
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(10, 30, 190, 42, style="DF")

    pdf.set_xy(14, 33)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(79, 70, 229)  # Primary indigo
    pdf.cell(0, 6, "EXECUTIVE AUDIT SUMMARY")
    pdf.ln(7)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(15, 23, 42)
    
    col_w = 60
    pdf.set_x(14)
    pdf.cell(col_w, 5, f"Match Rate: {summary.match_rate_percent}%")
    pdf.cell(col_w, 5, f"Matched Count: {summary.matched_count} pairs")
    pdf.cell(col_w, 5, f"Reconciled Value: Rs. {summary.matched_amount:,.2f}")
    pdf.ln(5)

    pdf.set_x(14)
    pdf.cell(col_w, 5, f"Bank Txns: {summary.total_bank_count}")
    pdf.cell(col_w, 5, f"Unmatched Bank: {summary.unmatched_bank_count}")
    pdf.cell(col_w, 5, f"Total Bank Value: Rs. {summary.total_bank_amount:,.2f}")
    pdf.ln(5)

    pdf.set_x(14)
    pdf.cell(col_w, 5, f"Ledger Txns: {summary.total_ledger_count}")
    pdf.cell(col_w, 5, f"Unmatched Ledger: {summary.unmatched_ledger_count}")
    pdf.cell(col_w, 5, f"Total Ledger Value: Rs. {summary.total_ledger_amount:,.2f}")
    pdf.ln(5)

    pdf.set_x(14)
    discrepancy_str = f"Rs. {summary.net_discrepancy:,.2f}"
    pdf.cell(col_w, 5, f"Discrepancies: {summary.amount_mismatch_count}")
    pdf.set_font("Helvetica", "B", 9)
    if summary.net_discrepancy == 0:
        pdf.set_text_color(16, 185, 129)  # Emerald
    else:
        pdf.set_text_color(239, 68, 68)  # Red
    pdf.cell(col_w * 2, 5, f"Net Variance (Bank - Ledger): {discrepancy_str}")
    pdf.ln(10)

    # Section 2: Matched Transactions (Sample/List)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, f"Matched Transactions ({len(matched_results)} pairs)")
    pdf.ln(7)

    pdf.set_fill_color(79, 70, 229)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    
    # Header
    pdf.cell(24, 6, "Bank Date", border=1, fill=True)
    pdf.cell(26, 6, "Amount (Rs.)", border=1, fill=True, align="R")
    pdf.cell(60, 6, "Bank Description", border=1, fill=True)
    pdf.cell(24, 6, "Ledger Date", border=1, fill=True)
    pdf.cell(40, 6, "Match Type", border=1, fill=True)
    pdf.cell(16, 6, "Score", border=1, fill=True, align="C")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    
    for m in matched_results[:40]:  # Up to 40 items in PDF
        desc = (m.bank_tx.description[:32] + "..") if len(m.bank_tx.description) > 32 else m.bank_tx.description
        pdf.cell(24, 5, str(m.bank_tx.date_val or "-"), border=1)
        pdf.cell(26, 5, f"{m.bank_tx.amount:,.2f}", border=1, align="R")
        pdf.cell(60, 5, desc or "-", border=1)
        pdf.cell(24, 5, str(m.ledger_tx.date_val or "-"), border=1)
        pdf.cell(40, 5, m.match_type, border=1)
        pdf.cell(16, 5, f"{m.confidence:.0f}%", border=1, align="C")
        pdf.ln(5)

    if len(matched_results) > 40:
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, f"... and {len(matched_results) - 40} more matched entries (see Excel report for complete register).")
        pdf.ln(6)

    pdf.ln(4)

    # Section 3: Amount Mismatches (if any)
    if amount_mismatches:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(239, 68, 68)
        pdf.cell(0, 6, f"Amount Variances ({len(amount_mismatches)} discrepancies)")
        pdf.ln(7)

        pdf.set_fill_color(239, 68, 68)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 8)

        pdf.cell(24, 6, "Date", border=1, fill=True)
        pdf.cell(30, 6, "Bank Amt (Rs.)", border=1, fill=True, align="R")
        pdf.cell(30, 6, "Ledger Amt (Rs.)", border=1, fill=True, align="R")
        pdf.cell(30, 6, "Variance (Rs.)", border=1, fill=True, align="R")
        pdf.cell(76, 6, "Observations", border=1, fill=True)
        pdf.ln(6)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(15, 23, 42)
        for amm in amount_mismatches[:20]:
            pdf.cell(24, 5, str(amm.bank_tx.date_val or "-"), border=1)
            pdf.cell(30, 5, f"{amm.bank_amount:,.2f}", border=1, align="R")
            pdf.cell(30, 5, f"{amm.ledger_amount:,.2f}", border=1, align="R")
            pdf.cell(30, 5, f"{amm.difference:,.2f}", border=1, align="R")
            pdf.cell(76, 5, amm.notes[:45], border=1)
            pdf.ln(5)

    pdf.ln(4)

    # Section 4: Unmatched Bank
    if unmatched_bank:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, f"Unmatched Bank Transactions ({len(unmatched_bank)} items)")
        pdf.ln(7)

        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(15, 23, 42)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(28, 6, "Date", border=1, fill=True)
        pdf.cell(32, 6, "Amount (Rs.)", border=1, fill=True, align="R")
        pdf.cell(90, 6, "Description", border=1, fill=True)
        pdf.cell(40, 6, "Status", border=1, fill=True)
        pdf.ln(6)

        pdf.set_font("Helvetica", "", 8)
        for ub in unmatched_bank[:25]:
            pdf.cell(28, 5, str(ub.date_val or "-"), border=1)
            pdf.cell(32, 5, f"{ub.amount:,.2f}", border=1, align="R")
            pdf.cell(90, 5, (ub.description[:50] if ub.description else "-"), border=1)
            pdf.cell(40, 5, "Missing in Ledger", border=1)
            pdf.ln(5)

    return bytes(pdf.output())
