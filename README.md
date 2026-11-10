# LedgerLens AI — Enterprise Financial Management & Reconciliation Platform

LedgerLens AI is a modern, professional, AI-powered financial management and deterministic reconciliation platform designed with a clean fintech SaaS design language (Stripe, Linear, and Ramp inspired).

---

## 🚀 Key Capabilities

### 1. 📊 Executive Financial Dashboard
- **Dynamic KPI Summary Cards:** Total Income, Total Expenses, Net Balance, and Savings Rate with period-over-period delta comparisons.
- **Plotly Interactive Visualizations:**
  - **Income vs Expenses:** Grouped bar chart with monthly rollups and currency formatting.
  - **Cash Flow Dynamics:** Spline line chart with area fill tracking cash flow trajectory.
  - **Expense Allocation:** Modern donut chart displaying category distribution with center-hole totals.
  - **Monthly Net Performance:** Zero-baseline bar chart distinguishing savings vs deficit periods.
- **Date Range Filters:** Preset filters (Last 7 Days, Last 30 Days, This Month, All Time) with date range pickers.

### 2. 💳 Transaction Management
- Full transaction register with real-time text search, type filters (Income/Expense), and category filters.
- Robust CRUD operations with Decimal precision to prevent floating-point inaccuracies.
- Form validation: strict positive amount validation, non-empty descriptions, valid date parsing.
- Safe modification and deletion with explicit confirmation safeguarding database records.

### 3. ⚖️ Deterministic Financial Reconciliation Engine
- **Independent Deterministic Logic:** Mathematical matching and discrepancy analysis are performed deterministically in Python (not guessed by AI).
- **Multi-Pass Matching Algorithm:**
  1. Exact reference code matching
  2. Exact date & amount matching
  3. Configurable date tolerance window (0–14 days) with fuzzy description scoring (using `difflib.SequenceMatcher`)
  4. Amount mismatch & variance detection
  5. Duplicate transaction detection
- **Versatile Ledger Support:** Reconcile uploaded bank statements (CSV/XLSX) directly against your live SQLite database or against an uploaded ledger file.
- **Audit-Grade Reports:** One-click export of reconciliation results to formatted Excel (`.xlsx`) and PDF (`.pdf`) statements.
- **Gemini Commentary:** Optional AI explanation providing CFO-level commentary on detected variances.

### 4. 🤖 Google Gemini AI Integration
- Powered by the official Google GenAI Python SDK (`google-genai`).
- Default model: `gemini-3.8-flash` (with automated fallback to `gemini-3.5-flash`).
- Strict grounding in database records (zero fabricated figures or hallucinated numbers).
- **AI Financial Insights:** High-level executive summaries, cost center observations, and strategic savings opportunities.
- **AI Assistant:** Context-aware interactive financial chatbot with pre-built prompt pills.
- **Live Diagnostics:** Settings page with real-time connection testing, latency reporting, and error classification (400, 401, 403, 404, 429, 500, 503, network timeouts).
- **Privacy & Security:** Full API key masking and error message sanitization to prevent credential leakage.

---

## 🛠️ Tech Stack & Architecture

- **Frontend & App Framework:** [Streamlit](https://streamlit.io/) (configured with light fintech SaaS design system)
- **Visualizations:** [Plotly](https://plotly.com/)
- **Data Manipulation:** [Pandas](https://pandas.pydata.org/)
- **Database:** SQLite 3 (ACID compliant, parameterized queries)
- **AI / LLM:** Google GenAI SDK (`google-genai`)
- **Reporting:** `openpyxl` (Excel) & `fpdf2` (PDF)

```
LedgerLens-AI/
├── app.py              # Main Streamlit web application & page routing
├── gemini_service.py   # Centralized Google GenAI service & connection testing
├── ai_service.py       # Compatibility interface
├── charts.py           # Plotly light-theme financial visualization module
├── database.py         # SQLite persistence, CRUD operations & Decimal precision
├── reconciliation.py   # Deterministic reconciliation engine & Excel/PDF export
├── test_suite.py       # Comprehensive unit tests (10 test cases)
├── requirements.txt    # Dependency specifications
├── .env.example        # Environment variable template
├── .gitignore          # Git exclusion rules
└── .streamlit/
    └── config.toml     # Streamlit theme and server configuration
```

---

## 🏁 Getting Started

### 1. Installation
Clone the repository and install required packages:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and set your Google Gemini API key:
```bash
cp .env.example .env
```

Edit `.env`:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash
```

*(Note: You can also update and test your API key directly in the application's Settings page).*

### 3. Run the Application
Launch the Streamlit dashboard:
```bash
streamlit run app.py
```

### 4. Run the Unit Test Suite
Verify all calculations, database operations, and reconciliation algorithms:
```bash
python3 test_suite.py
```

---

## 🌐 Deploying to Streamlit Community Cloud

You can deploy LedgerLens AI directly to **Streamlit Community Cloud** in a few clicks:

1. **Sign in to Streamlit Cloud:**
   Visit [share.streamlit.io](https://share.streamlit.io) and connect your GitHub account (`jashwanthreddy1031`).

2. **Create a New App:**
   - **Repository:** `jashwanthreddy1031/LedgerLens-AI`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** (Optional custom subdomain)

3. **Configure Secrets (Crucial for AI Features):**
   - In the deployment interface (or under **App Settings → Secrets**), paste:
     ```toml
     GEMINI_API_KEY = "your_actual_gemini_api_key_here"
     GEMINI_MODEL = "gemini-3.5-flash"
     ```
   - Click **Save**.

4. **Deploy:**
   Click **Deploy!**. Streamlit Cloud will install dependencies from `requirements.txt` and launch the live application.

