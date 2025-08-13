# 🇮🇳 India Indicators Dashboard (https://india-indicators.streamlit.app/)

An **interactive data dashboard** built with [Streamlit](https://streamlit.io) that visualizes key **macroeconomic and social indicators** for India, powered by the **World Bank Open Data API**. Compare against peer countries, share permalinks, download data, and generate quick insights — all from a clean, fast UI.

> Demo-friendly, interview-ready, and easy to extend.

---

## 🧭 Table of Contents
- [Features](#-features)
- [Use Cases](#-use-cases)
- [Architecture & Data Flow](#-architecture--data-flow)
- [Quickstart](#-quickstart)
- [Configuration](#-configuration)
- [Supported Indicators](#-supported-indicators)
- [How to Add a New Indicator](#-how-to-add-a-new-indicator)
- [Permalink (URL) Parameters](#-permalink-url-parameters)
- [Performance & Caching](#-performance--caching)
- [Accessibility & UX](#-accessibility--ux)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [API Reference](#-api-reference)
- [Data Usage & Licenses](#-data-usage--licenses)
- [Security & Privacy](#-security--privacy)
- [Roadmap](#-roadmap)
- [Changelog](#-changelog)
- [Contributing](#-contributing)
- [License](#-license)
- [Acknowledgements](#-acknowledgements)

---

## ✨ Features
- **Indicators**: GDP (total & per capita), CPI inflation, unemployment, life expectancy, population, CO₂ per capita.
- **Peer comparison**: Add countries manually or via presets (SAARC, BRICS, G20 sample).
- **Rich charts**: Plotly line & bar charts, optional **log scale** and **3‑year smoothing**.
- **Peer median line**: Dotted reference series computed from selected peers.
- **KPIs**: Latest value, year, YoY change, 5‑year CAGR.
- **Forecast**: Simple projection for India using 5‑year CAGR (peers are not forecasted).
- **Permalinks**: Share current view via URL query parameters.
- **CSV export**: Download the filtered dataset.
- **Resilient fetch**: Cached World Bank API requests with lightweight retries.
- **Python 3.8/3.9 compatible**; no secrets required.

---

## 💡 Use Cases
- **Policy & research**: Rapidly visualize macro trends and cross‑country comparisons for briefs and reports.
- **Consulting & CSR planning**: Sense‑check market size, inflation environment, demographic trends before strategy workshops.
- **Education**: Classroom demos of time‑series analysis, YoY vs CAGR, peer normalization (median lines).
- **Interview portfolio**: Share a live data product demonstrating data fetching, caching, visualization, UX, and basic modeling.
- **Stakeholder updates**: Permalinks allow “frozen” perspectives (indicator, year range, peers) that can be shared as URLs.

---

## 🏗 Architecture & Data Flow
```
World Bank API (v2, JSON)
        │
        ▼
Requests (HTTP)  ──► Cached (Streamlit @st.cache_data, 1h TTL, retry on failure)
        │
        ▼
Pandas transforms ──► KPI calc (YoY, 5y CAGR) ──► Optional forecast (CAGR-based)
        │
        ▼
Plotly charts (line/bar) + Streamlit UI (tabs, sidebar form) + CSV download
```

- **Source of truth**: World Bank Open Data API (`api.worldbank.org/v2`).
- **Caching**: Per indicator × country set, 1 hour TTL (configurable in code).
- **Stateless URLs**: View state (indicator, years, peers, theme, median) can be shared as permalinks.

---

## 🚀 Quickstart

### 1) Clone & enter
```bash
git clone https://github.com/<your-username>/india-indicators-dashboard.git
cd india-indicators-dashboard
```

### 2) Create a virtual environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

### 4) Run the app
```bash
streamlit run app/app.py
```
Open the URL Streamlit prints (default `http://localhost:8501`).

> **Note:** If you’re on Python 3.8/3.9, the app is compatible. For best performance, 3.10+ is recommended.

---

## ⚙️ Configuration
### Streamlit theme
`./.streamlit/config.toml` contains base theming; charts also have a **Light/Dark** toggle in the sidebar.

### Sidebar controls (form-based)
- Indicator selection
- Presets & manual peer selection
- Year range
- Log scale, 3‑year smoothing
- Chart theme (Light/Dark)
- Peer median reference line
- **Reset** & **Permalink** buttons

### Data source
No secrets required. API is public; requests are cached for 1 hour by default.

---

## 📋 Supported Indicators
| Indicator | Code | Unit | Notes |
|---|---|---|---|
| GDP (current US$) | `NY.GDP.MKTP.CD` | US$ | Total GDP in current USD |
| GDP per capita (US$) | `NY.GDP.PCAP.CD` | US$ | GDP divided by population |
| Inflation, CPI (annual %) | `FP.CPI.TOTL.ZG` | % | Year‑over‑year change |
| Unemployment (% of labor force) | `SL.UEM.TOTL.ZS` | % | Modeled ILO estimate |
| Life expectancy at birth (years) | `SP.DYN.LE00.IN` | yrs | |
| Population, total | `SP.POP.TOTL` | (count) | |
| CO₂ emissions (metric tons per capita) | `EN.ATM.CO2E.PC` | t | |

> You can add more indicators in a few lines — see below.

---

## ➕ How to Add a New Indicator
1. Open `app/app.py` and find the `INDICATORS` dict.
2. Add a new entry: `"Label": ("WB_CODE", "unit", "agg", invert_axis_bool)`  
   - Example:  
     ```python
     "Gross capital formation (current US$)": ("NE.GDI.TOTL.CD", "US$", "sum", True),
     ```
3. Save & rerun: the indicator shows up in the dropdown automatically.

---

## 🔗 Permalink (URL) Parameters
The **Permalink** button updates the page URL with your current view:

- `ind`: Indicator code (e.g., `NY.GDP.MKTP.CD`)
- `yr1`, `yr2`: Year range (e.g., `2000`, `2024`)
- `peers`: Comma‑separated ISO‑3 list (e.g., `CHN,USA,BGD`)
- `theme`: `light` or `dark`
- `median`: `1` to show peer median, `0` to hide

**Example:**
```
?ind=NY.GDP.PCAP.CD&yr1=1990&yr2=2024&peers=CHN,USA&theme=dark&median=1
```

On load, the app reads these parameters to **hydrate** the controls.

---

## ⚡ Performance & Caching
- **Caching**: `@st.cache_data` memoizes fetches for 1 hour (configurable).
- **Retries**: Lightweight exponential backoff for transient network hiccups.
- **Client‑side**: Plotly handles millions of points reasonably, but you can reduce the year range for very long series.

Tips:
- Use **smoothing** and **log scale** to improve readability for volatile or wide‑range series.
- Keep peer sets focused (3–8) for the cleanest comparisons.

---

## ♿ Accessibility & UX
- High‑contrast **Light/Dark** chart templates.
- Legible fonts, restrained color palette.
- Clear **empty states** and error messages.
- **Form‑based** sidebar controls reduce flicker and unnecessary reruns.
- CSV exports for offline analysis.

---

## ✅ Testing
Minimal smoke tests can be added with `pytest`. Example scaffolding:
```bash
pip install pytest
pytest
```
- Test ideas: indicator list integrity, API response shape, CAGR/YoY math, URL hydration parsing.

---

## ☁️ Deployment
### Streamlit Community Cloud (recommended, free)
1. Push this repo to GitHub.
2. Go to **Streamlit Cloud** → **New app**.
3. Choose your repo and set **Main file path** to `app/app.py`.
4. Deploy. Subsequent pushes to `main` auto‑update the app.

### Alternatives
- **Hugging Face Spaces** (Gradio/Streamlit)
- **Docker** (optional): build and run a containerized app.
  ```dockerfile
  # Dockerfile (optional)
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  EXPOSE 8501
  CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
  ```

---

## 📚 API Reference
### Base
- **World Bank API v2**: `https://api.worldbank.org/v2`

### Example Endpoint (used by the app)
```
/country/{ISO3}/indicator/{INDICATOR_CODE}?format=json&per_page=20000&page=1
```
- **Params**: `format=json` (JSON output), `per_page` (pagination), `page` (page index).
- Responses include a metadata object and a data array. The app normalizes the array of observations and concatenates all pages.
- **Notes**: Some series have missing years or revised values. Always check the last available year when interpreting KPIs.

---

## 📝 Data Usage & Licenses
- **Data source**: World Bank Open Data — subject to World Bank terms and attribution.  
  See: https://data.worldbank.org/ and related terms.
- **Attribution**: Please cite “World Bank Open Data” when publishing outputs.
- **Code license**: MIT by default (see [License](#-license)).
- **Content license**: If you include documentation content, consider adding a Creative Commons license (e.g., CC BY 4.0) for non‑code assets.

> If your organization needs different licensing (e.g., Apache‑2.0), update the `LICENSE` file accordingly.

---

## 🔒 Security & Privacy
- No credentials or secrets are required.
- Data is public; the app makes anonymous GET requests.
- Do not commit any private datasets to the repo. `.gitignore` excludes common local files and caches.

---

## 🗺 Roadmap
- [ ] Indicator groups & tagging (economy, health, environment).
- [ ] Rolling statistics (5y average, volatility) and z‑score normalization.
- [ ] Optional **Prophet**/**ARIMA** forecasts with confidence intervals.
- [ ] Country detail cards with metadata (population, income level).
- [ ] Export chart images (PNG) for easy sharing.
- [ ] Unit tests (pytest) and pre‑commit hooks (ruff/black/isort).
- [ ] GitHub Actions CI to lint, test, and build on push.

---

## 📣 Changelog
Follow **Keep a Changelog** style.

### [Unreleased]
- Initial public release with indicators, comparisons, KPI cards, smoothing, theme toggle, peer median, permalinks, CSV export.

---

## 🤝 Contributing
PRs welcome! Please:
1. Open an issue describing the feature/fix.
2. Fork the repo, create a branch, and submit a PR.
3. Keep changes focused and include a short demo (GIF or screenshots) when possible.

---

## 📄 License
This project is licensed under the **MIT License**.  
You are free to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies with attribution and license inclusion.

```
MIT License

Copyright (c) 2025 Kumar Suyash Rituraj

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```


---

## 🙏 Acknowledgements
- Data from **World Bank Open Data**.
- UI by **Streamlit** and charts by **Plotly**.
- Project maintained by the community — contributions welcome!
