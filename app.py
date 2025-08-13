import math
import time
from datetime import datetime
from typing import Optional, List, Dict, Tuple

import pandas as pd
import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go  # for median reference trace

st.set_page_config(page_title="India Indicators", page_icon="📊", layout="wide")

# ======================
# Config & Constants
# ======================
WB_BASE = "https://api.worldbank.org/v2"
DEFAULT_COUNTRY = "IND"

COUNTRY_LABELS: Dict[str, str] = {
    "IND": "India", "CHN": "China", "USA": "United States", "BGD": "Bangladesh",
    "PAK": "Pakistan", "LKA": "Sri Lanka", "NPL": "Nepal", "BRA": "Brazil",
    "RUS": "Russia", "ZAF": "South Africa", "IDN": "Indonesia", "MEX": "Mexico",
    "TUR": "Türkiye", "GBR": "United Kingdom", "DEU": "Germany", "FRA": "France",
    "JPN": "Japan",
}

PEERS = {
    "China": "CHN", "United States": "USA", "Bangladesh": "BGD", "Pakistan": "PAK",
    "Sri Lanka": "LKA", "Nepal": "NPL", "Brazil": "BRA", "Russia": "RUS",
    "South Africa": "ZAF", "Indonesia": "IDN", "Mexico": "MEX", "Türkiye": "TUR",
    "United Kingdom": "GBR", "Germany": "DEU", "France": "FRA", "Japan": "JPN",
}

PRESETS: Dict[str, List[str]] = {
    "SAARC": ["BGD", "PAK", "LKA", "NPL"],
    "BRICS": ["BRA", "RUS", "CHN", "ZAF"],
    "G20 sample": ["USA", "CHN", "JPN", "DEU", "GBR", "FRA"],
}

INDICATORS: Dict[str, Tuple[str, str, str, bool]] = {
    "GDP (current US$)": ("NY.GDP.MKTP.CD", "US$", "sum", True),
    "GDP per capita (US$)": ("NY.GDP.PCAP.CD", "US$", "mean", True),
    "Inflation, CPI (% YoY)": ("FP.CPI.TOTL.ZG", "%", "mean", False),
    "Unemployment (% labor force)": ("SL.UEM.TOTL.ZS", "%", "mean", False),
    "Life expectancy (years)": ("SP.DYN.LE00.IN", "yrs", "mean", False),
    "Population": ("SP.POP.TOTL", "", "sum", True),
    "CO₂ emissions (t per capita)": ("EN.ATM.CO2E.PC", "t", "mean", False),
}

GLOSSARY = {
    "NY.GDP.MKTP.CD": "GDP (current US$): Market value of all final goods and services produced in a year.",
    "NY.GDP.PCAP.CD": "GDP per capita (current US$): GDP divided by midyear population.",
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %).",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of total labor force).",
    "SP.DYN.LE00.IN": "Life expectancy at birth (years).",
    "SP.POP.TOTL": "Population, total.",
    "EN.ATM.CO2E.PC": "CO₂ emissions (metric tons per capita).",
}

MIN_YEAR = 1960
MAX_YEAR = datetime.now().year

# ======================
# Data Access (cached)
# ======================
def _safe_request(url: str, params: dict, retries: int = 3, backoff: float = 0.6):
    last_exc = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r
        except Exception as e:
            last_exc = e
            time.sleep(backoff * (2 ** i))
    raise last_exc

@st.cache_data(show_spinner=False, ttl=60 * 60)
def wb_fetch_series(country_code: str, indicator_code: str) -> pd.DataFrame:
    url = f"{WB_BASE}/country/{country_code}/indicator/{indicator_code}"
    params = {"format": "json", "per_page": 20000}
    out = []
    page = 1
    while True:
        params["page"] = page
        r = _safe_request(url, params)
        data = r.json()
        if not isinstance(data, list) or len(data) < 2:
            break
        meta, rows = data
        out.extend(rows)
        if page >= meta.get("pages", 1):
            break
        page += 1
    if not out:
        return pd.DataFrame(columns=["country", "iso3", "indicator", "date", "value"])
    df = pd.json_normalize(out).rename(columns={
        "country.value": "country",
        "countryiso3code": "iso3",
        "indicator.id": "indicator",
        "date": "date",
        "value": "value",
    })
    df["date"] = pd.to_numeric(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    df["iso3"] = df["iso3"].astype("category")
    df["indicator"] = df["indicator"].astype("category")
    return df[["country", "iso3", "indicator", "date", "value"]]

@st.cache_data(show_spinner=False, ttl=60 * 60)
def wb_fetch_multi(countries: List[str], indicator_code: str) -> pd.DataFrame:
    frames = [wb_fetch_series(c, indicator_code) for c in countries]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

# ======================
# Metrics & Utils
# ======================
def latest_non_null(df: pd.DataFrame) -> Optional[pd.Series]:
    clean = df.dropna(subset=["value"]).sort_values("date")
    return clean.iloc[-1] if len(clean) else None

def yoy_change(df: pd.DataFrame) -> Optional[float]:
    clean = df.dropna(subset=["value"]).sort_values("date")
    if len(clean) < 2:
        return None
    last, prev = clean.iloc[-1]["value"], clean.iloc[-2]["value"]
    if prev in [0, None] or (isinstance(prev, float) and math.isclose(prev, 0.0)):
        return None
    return ((last - prev) / prev) * 100.0

def cagr_from_last_n_years(df: pd.DataFrame, n: int = 5) -> Optional[float]:
    clean = df.dropna(subset=["value"]).sort_values("date")
    if len(clean) == 0:
        return None
    last_year = int(clean.iloc[-1]["date"])
    first_year = last_year - n
    window = clean[clean["date"].between(first_year, last_year, inclusive="both")]
    if len(window) < 2:
        return None
    start_val = window.iloc[0]["value"]
    end_val = window.iloc[-1]["value"]
    years = int(window.iloc[-1]["date"] - window.iloc[0]["date"])
    if years <= 0 or start_val in [0, None] or (isinstance(start_val, float) and math.isclose(start_val, 0.0)):
        return None
    return (end_val / start_val) ** (1.0 / years) - 1.0

def format_val(val, unit: str) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "—"
    if unit in ("US$", ""):
        absval = abs(val); sign = "-" if val < 0 else ""
        if absval >= 1e12: return f"{sign}{absval/1e12:.2f}T"
        if absval >= 1e9:  return f"{sign}{absval/1e9:.2f}B"
        if absval >= 1e6:  return f"{sign}{absval/1e6:.2f}M"
        return f"{val:,.0f}"
    if unit in ("%", "yrs", "t"):
        return f"{val:.2f}"
    return f"{val}"

def quick_insight(series_name: str,
                  latest_year: Optional[int],
                  val_str: str,
                  yoy: Optional[float],
                  cagr5: Optional[float],
                  unit: str) -> str:
    if latest_year is None:
        return f"No recent data available for {series_name}."
    bits = [f"{series_name}: {val_str} in {latest_year}."]
    if yoy is not None:
        arrow = "↑" if yoy >= 0 else "↓"
        bits.append(f"YoY {arrow}{abs(yoy):.2f}%.")
    if cagr5 is not None:
        bits.append(f"5y CAGR {cagr5*100:.2f}%.")
    return " ".join(bits)

def extend_forecast(df: pd.DataFrame, years_ahead: int, cagr: Optional[float]) -> pd.DataFrame:
    if cagr is None or df.empty:
        return df.copy()
    clean = df.dropna(subset=["value"]).sort_values("date").copy()
    if clean.empty:
        return df.copy()
    last_year = int(clean.iloc[-1]["date"])
    last_val = float(clean.iloc[-1]["value"])
    add_rows = []
    for i in range(1, years_ahead + 1):
        y = last_year + i
        last_val = last_val * (1.0 + cagr)
        add_rows.append({"country": clean.iloc[-1]["country"], "iso3": clean.iloc[-1]["iso3"],
                         "indicator": clean.iloc[-1]["indicator"], "date": y, "value": last_val})
    return pd.concat([clean, pd.DataFrame(add_rows)], ignore_index=True) if add_rows else clean

def peer_median_series(df_peers: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Return per-year median of peer countries as a series (country='Peer median')."""
    df = df_peers.dropna(subset=["value"])
    if df.empty:
        return None
    med = df.groupby("date", as_index=False)["value"].median()
    med["country"] = "Peer median"
    return med[["country", "date", "value"]]

# ======================
# Sidebar Controls (form)
# ======================
def _get_qp_val(qp, key: str) -> Optional[str]:
    if key not in qp:
        return None
    v = qp[key]
    if isinstance(v, list):
        return v[0] if v else None
    return v

def init_defaults():
    if "controls" not in st.session_state:
        st.session_state.controls = {
            "indicator_label": list(INDICATORS.keys())[0],
            "preset_choice": "None",
            "manual_peers": [],
            "yr1": 2000,
            "yr2": MAX_YEAR,
            "log_scale": False,
            "smooth3": False,
            "chart_theme": "Light",      # NEW
            "show_median": True,         # NEW
        }
        # hydrate from URL query params
        qp = st.query_params
        if qp:
            code_to_label = {v[0]: k for k, v in INDICATORS.items()}
            iso_to_name = {v: k for k, v in PEERS.items()}

            ind = _get_qp_val(qp, "ind")
            yr1 = _get_qp_val(qp, "yr1")
            yr2 = _get_qp_val(qp, "yr2")
            peers = _get_qp_val(qp, "peers")
            theme = _get_qp_val(qp, "theme")
            median = _get_qp_val(qp, "median")

            if ind in code_to_label:
                st.session_state.controls["indicator_label"] = code_to_label[ind]
            if yr1 is not None:
                try: st.session_state.controls["yr1"] = max(MIN_YEAR, min(MAX_YEAR, int(yr1)))
                except Exception: pass
            if yr2 is not None:
                try: st.session_state.controls["yr2"] = max(MIN_YEAR, min(MAX_YEAR, int(yr2)))
                except Exception: pass
            if peers:
                iso_list = [iso.strip() for iso in peers.split(",") if iso.strip()]
                names = [iso_to_name[i] for i in iso_list if i in iso_to_name]
                st.session_state.controls["manual_peers"] = names
            if theme in ("Light", "Dark", "light", "dark"):
                st.session_state.controls["chart_theme"] = "Dark" if theme.lower() == "dark" else "Light"
            if median is not None:
                st.session_state.controls["show_median"] = str(median) not in ("0", "false", "False")

def controls_form() -> dict:
    init_defaults()
    c = st.session_state.controls

    with st.sidebar:
        st.header("Controls")
        with st.form("controls_form", clear_on_submit=False):
            indicator_label = st.selectbox("Indicator", list(INDICATORS.keys()),
                                           index=list(INDICATORS.keys()).index(c["indicator_label"]))
            preset_choice = st.selectbox("Peer preset (optional)", ["None"] + list(PRESETS.keys()),
                                         index=(["None"] + list(PRESETS.keys())).index(c["preset_choice"]))
            manual_peers = st.multiselect("Compare with (add/remove)", list(PEERS.keys()), default=c["manual_peers"])
            yr1, yr2 = st.slider("Year range", MIN_YEAR, MAX_YEAR, (c["yr1"], c["yr2"]), step=1)
            log_scale = st.toggle("Log scale (y)", value=c["log_scale"])
            smooth3 = st.toggle("3-year smoothing overlay", value=c["smooth3"],
                                help="Adds a 3-year moving average line to the trend chart.")
            chart_theme = st.selectbox("Chart theme", ["Light", "Dark"], index=(0 if c["chart_theme"]=="Light" else 1))
            show_median = st.toggle("Peer median reference line", value=c["show_median"],
                                    help="Adds per-year median of selected peers to trend charts.")
            apply_btn = st.form_submit_button("Apply")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Reset"):
                st.session_state.controls = {
                    "indicator_label": list(INDICATORS.keys())[0],
                    "preset_choice": "None",
                    "manual_peers": [],
                    "yr1": 2000,
                    "yr2": MAX_YEAR,
                    "log_scale": False,
                    "smooth3": False,
                    "chart_theme": "Light",
                    "show_median": True,
                }
                st.rerun()
        with col_b:
            if st.button("Permalink"):
                ind_code = INDICATORS[c["indicator_label"]][0]
                peers_iso = []
                if c["preset_choice"] != "None":
                    peers_iso += PRESETS[c["preset_choice"]]
                peers_iso += [PEERS[k] for k in c["manual_peers"]]
                seen = set(); peers_iso_clean = []
                for iso in peers_iso:
                    if iso not in seen:
                        peers_iso_clean.append(iso); seen.add(iso)

                params = {"ind": ind_code, "yr1": c["yr1"], "yr2": c["yr2"],
                          "theme": c["chart_theme"].lower(), "median": (1 if c["show_median"] else 0)}
                if peers_iso_clean:
                    params["peers"] = ",".join(peers_iso_clean)

                st.query_params = params
                st.toast("URL updated with your selection. Copy it from the address bar.", icon="🔗")

    if apply_btn:
        st.session_state.controls = {
            "indicator_label": indicator_label,
            "preset_choice": preset_choice,
            "manual_peers": manual_peers,
            "yr1": yr1,
            "yr2": yr2,
            "log_scale": log_scale,
            "smooth3": smooth3,
            "chart_theme": chart_theme,
            "show_median": show_median,
        }
        c = st.session_state.controls
    return c

# ======================
# Main App
# ======================
st.title("🇮🇳 India Indicators Dashboard")
st.caption("World Bank API • Cached • 3.8/3.9 compatible • Theme & peer-median options")

controls = controls_form()
indicator_label = controls["indicator_label"]
preset_choice = controls["preset_choice"]
manual_peers = controls["manual_peers"]
yr1, yr2 = controls["yr1"], controls["yr2"]
log_scale, smooth3 = controls["log_scale"], controls["smooth3"]
chart_theme = controls["chart_theme"]
show_median = controls["show_median"]

template = "plotly_dark" if chart_theme == "Dark" else "plotly"
ind_code, unit, _agg, _invert_axis = INDICATORS[indicator_label]

countries = [DEFAULT_COUNTRY]
if preset_choice != "None":
    countries += PRESETS[preset_choice]
countries += [PEERS[k] for k in manual_peers]
seen = set(); dedup = []
for c in countries:
    if c not in seen:
        dedup.append(c); seen.add(c)
countries = dedup

with st.spinner("Fetching data from World Bank…"):
    try:
        df_all = wb_fetch_multi(countries, ind_code)
    except Exception as e:
        st.error(f"Failed to retrieve data. Please try again or adjust your selection.\n\nError: {e}")
        st.stop()

df_all = df_all[(df_all["date"] >= yr1) & (df_all["date"] <= yr2)]
df_all["country"] = df_all["iso3"].map(COUNTRY_LABELS).fillna(df_all["country"])

if df_all.empty:
    st.warning("No data available for your current selection. Try changing the year range or peers.")
    st.stop()

df_ind = df_all[df_all["iso3"] == DEFAULT_COUNTRY]
df_peers = df_all[df_all["iso3"] != DEFAULT_COUNTRY]

latest_row = latest_non_null(df_ind)
yoy = yoy_change(df_ind)
cagr5 = cagr_from_last_n_years(df_ind, n=5)
latest_year = int(latest_row["date"]) if latest_row is not None else None
latest_val = latest_row["value"] if latest_row is not None else None

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Compare", "Forecast", "Data & Glossary"])

with tab1:
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Latest", format_val(latest_val, unit) + (f" {unit}" if unit in ("US$", "%", "t") else ""))
    with k2: st.metric("Year", latest_year if latest_year else "—")
    with k3: st.metric("YoY change", f"{yoy:.2f}%" if yoy is not None else "—")
    with k4: st.metric("5y CAGR", f"{cagr5*100:.2f}%" if cagr5 is not None else "—")

    st.markdown("#### Trend")
    plot_df = df_all.copy()

    # Base chart
    fig = px.line(plot_df, x="date", y="value", color="country",
                  labels={"date": "Year", "value": indicator_label},
                  template=template)
    # Optional smoothing overlay
    if smooth3:
        smoothed = (
            plot_df.sort_values(["country", "date"])
            .groupby("country", as_index=False)
            .apply(lambda g: g.assign(value_smooth=g["value"].rolling(window=3, min_periods=1).mean()))
            .reset_index(drop=True)
        )
        fig2 = px.line(smoothed, x="date", y="value_smooth", color="country", template=template)
        for tr in fig2.data:
            tr.update(line=dict(dash="dash"))
            fig.add_trace(tr)
    # Peer median reference line
    if show_median:
        med = peer_median_series(df_peers)
        if med is not None and not med.empty:
            fig.add_trace(go.Scatter(
                x=med["date"], y=med["value"], name="Peer median",
                mode="lines+markers", line=dict(width=3, dash="dot")
            ))

    if log_scale:
        fig.update_yaxes(type="log")

    height = 380 + 18 * max(0, len(countries) - 1)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=0), height=min(height, 640))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Quick insight")
    st.info(quick_insight(indicator_label, latest_year, format_val(latest_val, unit), yoy, cagr5, unit))

with tab2:
    st.subheader("Latest value comparison")
    latest_vals = (
        df_all.dropna(subset=["value"])
        .sort_values(["country", "date"])
        .groupby("country", as_index=False)
        .tail(1)[["country", "date", "value"]]
        .sort_values("value", ascending=False)
    )
    if latest_vals.empty:
        st.warning("No recent data available for selected countries.")
    else:
        fig2 = px.bar(latest_vals, x="country", y="value",
                      labels={"value": indicator_label, "country": "Country"},
                      template=template)
        if log_scale:
            fig2.update_yaxes(type="log")
        fig2.update_layout(margin=dict(l=10, r=10, t=10, b=0), height=420)
        st.plotly_chart(fig2, use_container_width=True)
        with st.expander("Latest values table"):
            st.dataframe(latest_vals.reset_index(drop=True), use_container_width=True)

with tab3:
    st.subheader("Simple forecast (CAGR-based)")
    years_ahead = st.slider("Years to project", 1, 10, 5, step=1)
    df_ind_ext = extend_forecast(df_ind, years_ahead, cagr5)
    df_for_plot = pd.concat([df_ind_ext, df_peers], ignore_index=True)
    fig3 = px.line(df_for_plot, x="date", y="value", color="country",
                   labels={"date": "Year", "value": indicator_label},
                   markers=True, template=template)
    # Optional peer median (no forecast for median)
    if show_median:
        med = peer_median_series(df_peers)
        if med is not None and not med.empty:
            fig3.add_trace(go.Scatter(
                x=med["date"], y=med["value"], name="Peer median",
                mode="lines+markers", line=dict(width=3, dash="dot")
            ))
    if log_scale:
        fig3.update_yaxes(type="log")
    fig3.update_layout(margin=dict(l=10, r=10, t=10, b=0), height=420)
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Uses India’s 5-year CAGR (if available) to extend the series. Peers are not forecasted.")

with tab4:
    st.subheader("Data & Downloads")
    csv_bytes = df_all.sort_values(["country", "date"]).to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered data (CSV)", data=csv_bytes,
                       file_name=f"india_indicators_{ind_code}_{yr1}_{yr2}.csv", mime="text/csv")
    st.markdown("**Source:** World Bank Open Data API")
    st.write(f"Indicator code: `{ind_code}`")
    st.markdown("**Glossary**")
    st.write(GLOSSARY.get(ind_code, "—"))
    with st.expander("Methodology"):
        st.markdown(
            "- Values come directly from the World Bank API (v2) and are cached for 1 hour.\n"
            "- KPI YoY compares the last two available points.\n"
            "- 5-year CAGR uses the first and last values available in the last 5-year window.\n"
            "- Forecast extends India’s series by compounding the 5-year CAGR.\n"
            "- ‘Log scale’, ‘3-year smoothing’, and ‘Chart theme’ affect the charts only (not KPIs)."
        )
