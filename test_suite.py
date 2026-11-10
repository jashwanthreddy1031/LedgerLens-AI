"""
test_suite.py - Unit and Integration Tests for LedgerLens AI.
Tests database operations, financial calculations, deterministic reconciliation,
and AI security/error handling.
"""

from datetime import date, timedelta
from decimal import Decimal
import os
import unittest
import pandas as pd

import database
import reconciliation as rec
import ai_service
import charts


class TestDatabaseOperations(unittest.TestCase):
    """Verify database CRUD and integrity."""

    def test_database_connection_and_info(self):
        info = database.get_database_info()
        self.assertIn("path", info)
        self.assertIn("total_transactions", info)
        self.assertGreaterEqual(info["total_transactions"], 0)

    def test_add_and_delete_transaction(self):
        initial_count = len(database.get_transactions())
        new_id = database.add_transaction(
            date="2026-11-01",
            type_="Income",
            category="Test Revenue",
            amount=5432.10,
            description="Automated unit test entry",
        )
        self.assertGreater(new_id, 0)
        
        # Verify retrieved
        tx = database.get_transaction_by_id(new_id)
        self.assertIsNotNone(tx)
        self.assertEqual(tx["amount"], 5432.10)
        self.assertEqual(tx["category"], "Test Revenue")
        
        # Test update
        updated = database.update_transaction(
            id_=new_id,
            date="2026-11-02",
            type_="Income",
            category="Updated Revenue",
            amount=6000.0,
            description="Updated description",
        )
        self.assertTrue(updated)
        tx_up = database.get_transaction_by_id(new_id)
        self.assertEqual(tx_up["amount"], 6000.0)
        self.assertEqual(tx_up["category"], "Updated Revenue")

        # Clean up: delete
        deleted = database.delete_transaction(new_id)
        self.assertTrue(deleted)
        final_count = len(database.get_transactions())
        self.assertEqual(final_count, initial_count)

    def test_negative_or_zero_amount_rejected(self):
        with self.assertRaises(ValueError):
            database.add_transaction(
                date="2026-11-01",
                type_="Income",
                category="Invalid",
                amount=-100.0,
                description="Negative",
            )
        with self.assertRaises(ValueError):
            database.add_transaction(
                date="2026-11-01",
                type_="Income",
                category="Invalid",
                amount=0.0,
                description="Zero",
            )


class TestReconciliationEngine(unittest.TestCase):
    """Verify deterministic reconciliation logic."""

    def setUp(self):
        self.bank_df = pd.DataFrame({
            "txn_date": ["2026-11-01", "2026-11-03", "2026-11-05", "2026-11-05"],
            "particulars": ["Payment Alpha Tech", "Server Hosting Corp", "Office Supplies", "Office Supplies"],
            "amount": [12000.0, 3500.0, 850.0, 850.0],
            "ref_number": ["TXN101", "AWS909", "STAT1", "STAT1"],
        })

        self.ledger_df = pd.DataFrame({
            "Date": ["2026-11-01", "2026-11-04", "2026-11-05"],
            "Description": ["Alpha Tech Client Payment", "Server Hosting", "Office Supplies Stationary"],
            "Amount": [12000.0, 3500.0, 800.0],  # 800 vs 850 is an amount mismatch
            "Reference": ["TXN101", "AWS909", "STAT1"],
        })

    def test_column_detection(self):
        b_cols = rec.detect_columns(self.bank_df)
        l_cols = rec.detect_columns(self.ledger_df)
        self.assertEqual(b_cols["date"], "txn_date")
        self.assertEqual(b_cols["amount"], "amount")
        self.assertEqual(b_cols["reference"], "ref_number")
        self.assertEqual(l_cols["date"], "Date")
        self.assertEqual(l_cols["description"], "Description")

    def test_reconciliation_matching(self):
        b_cols = rec.detect_columns(self.bank_df)
        l_cols = rec.detect_columns(self.ledger_df)
        bank_txs = rec.normalize_transactions(self.bank_df, "bank", b_cols)
        ledger_txs = rec.normalize_transactions(self.ledger_df, "ledger", l_cols)

        matched, ub, ul, mismatches, bank_dups, ledger_dups, summary = rec.run_reconciliation(
            bank_txs, ledger_txs, date_tolerance_days=3
        )

        # 2 should match exactly (TXN101 and AWS909 within 1 day)
        self.assertEqual(len(matched), 2)
        # 1 amount mismatch (STAT1: 850 vs 800)
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0].bank_amount, 850.0)
        self.assertEqual(mismatches[0].ledger_amount, 800.0)
        # 1 duplicate in bank
        self.assertEqual(len(bank_dups), 1)
        self.assertGreater(summary.match_rate_percent, 50.0)

    def test_exports_excel_and_pdf(self):
        b_cols = rec.detect_columns(self.bank_df)
        l_cols = rec.detect_columns(self.ledger_df)
        bank_txs = rec.normalize_transactions(self.bank_df, "bank", b_cols)
        ledger_txs = rec.normalize_transactions(self.ledger_df, "ledger", l_cols)

        matched, ub, ul, mismatches, bank_dups, ledger_dups, summary = rec.run_reconciliation(
            bank_txs, ledger_txs
        )

        excel_data = rec.export_reconciliation_excel(summary, matched, ub, ul, mismatches, bank_dups)
        pdf_data = rec.export_reconciliation_pdf(summary, matched, ub, ul, mismatches)

        self.assertIsInstance(excel_data, bytes)
        self.assertGreater(len(excel_data), 1000)
        self.assertIsInstance(pdf_data, bytes)
        self.assertGreater(len(pdf_data), 1000)


class TestAIServiceSecurity(unittest.TestCase):
    """Verify key masking, error sanitization, and diagnostics."""

    def test_key_masking(self):
        self.assertEqual(ai_service.mask_key(None), "Not configured")
        self.assertEqual(ai_service.mask_key(""), "Not configured")
        self.assertEqual(ai_service.mask_key("AIzaSyD8765432101234567890"), "AIza••••••••7890")

    def test_error_sanitization(self):
        secret = "AIzaSyD8765432101234567890_SECRET_KEY"
        fake_err = Exception(f"Failed to connect using key {secret} to google.com")
        clean = ai_service.sanitize_error_message(fake_err, secret)
        self.assertNotIn(secret, clean)
        self.assertIn("[REDACTED_API_KEY]", clean)

    def test_granular_error_classification(self):
        # 400
        e400 = Exception("INVALID_ARGUMENT: Bad parameter")
        self.assertIn("400", ai_service.classify_gemini_error(e400))

        # 401
        e401 = Exception("UNAUTHENTICATED: API key not valid")
        self.assertIn("401", ai_service.classify_gemini_error(e401))

        # 403
        e403 = Exception("PERMISSION_DENIED: Access forbidden")
        self.assertIn("403", ai_service.classify_gemini_error(e403))

        # 404
        e404 = Exception("NOT_FOUND: Model not found")
        self.assertIn("404", ai_service.classify_gemini_error(e404))

        # 429
        e429 = Exception("RESOURCE_EXHAUSTED: Quota exceeded")
        self.assertIn("429", ai_service.classify_gemini_error(e429))

        # 503 / 504
        e503 = Exception("503 UNAVAILABLE: High demand")
        self.assertIn("503", ai_service.classify_gemini_error(e503))

    def test_deprecated_model_upgrade(self):
        # gemini-2.0-flash should map to gemini-3.8-flash
        self.assertEqual(ai_service.DEPRECATED_MODEL_MAP["gemini-2.0-flash"], "gemini-3.8-flash")
        self.assertNotIn("gemini-2.0-flash", ai_service.SUPPORTED_MODELS)


class TestCharts(unittest.TestCase):
    """Verify chart creation and fallback states."""

    def test_charts_with_sample_data(self):
        df = pd.DataFrame({
            "date": ["2026-10-01", "2026-10-15"],
            "type": ["Income", "Expense"],
            "category": ["Salary", "Rent"],
            "amount": [50000.0, 20000.0],
        })
        self.assertIsNotNone(charts.create_income_vs_expense_chart(df))
        self.assertIsNotNone(charts.create_cash_flow_trend_chart(df))
        self.assertIsNotNone(charts.create_expense_breakdown_chart(df))
        self.assertIsNotNone(charts.create_monthly_performance_chart(df))

    def test_charts_empty_dataframe(self):
        empty_df = pd.DataFrame()
        self.assertIsNotNone(charts.create_income_vs_expense_chart(empty_df))
        self.assertIsNotNone(charts.create_cash_flow_trend_chart(empty_df))
        self.assertIsNotNone(charts.create_expense_breakdown_chart(empty_df))
        self.assertIsNotNone(charts.create_monthly_performance_chart(empty_df))


if __name__ == "__main__":
    unittest.main()

