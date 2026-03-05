import io
import re
from datetime import datetime, date

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# ============================================================
# WHALER — V1 (Clean + Premium)
# GitHub-ready Streamlit app
# ============================================================

st.set_page_config(page_title="WHALER", page_icon="🐋", layout="wide")

# ---------- Brand ----------
BRAND = {
    "blue": "#2F80ED",
    "blue2": "#56A0FF",
    "green": "#27AE60",
    "aqua": "#2DDAE3",
    "bg": "#07131f",
    "bg2": "#061826",
    "card": "rgba(255,255,255,0.045)",
    "stroke": "rgba(255,255,255,0.10)",
    "text": "rgba(255,255,255,0.92)",
    "muted": "rgba(255,255,255,0.68)",
}
STACK_COLORS = [BRAND["blue"], BRAND["blue2"], BRAND["green"], BRAND["aqua"]]

# ---------- Premium CSS ----------
st.markdown(
    f"""
<style>
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding-top: 1.6rem; padding-bottom: 2.4rem; max-width: 1200px; }}

:root {{
  --bg: {BRAND["bg"]};
  --bg2: {BRAND["bg2"]};
  --card: {BRAND["card"]};
  --stroke: {BRAND["stroke"]};
  --text: {BRAND["text"]};
  --muted: {BRAND["muted"]};
  --brand: {BRAND["blue"]};
}}

html, body, [class*="css"] {{
  background: radial-gradient(1000px 600px at 20% 0%, var(--bg2) 0%, var(--bg) 55%);
  color: var(--text);
}}

.h1 {{
  font-size: 30px;
  font-weight: 750;
  letter-spacing: 0.4px;
  line-height: 1.1;
  margin: 0;
}}
.sub {{
  color: var(--muted);
  margin-top: 6px;
  font-size: 14px;
}}

.card {{
  background: var(--card);
  border: 1px solid var(--stroke);
  border-radius: 18px;
  padding: 16px 16px;
}}

.card-tight {{
  background: var(--card);
  border: 1px solid var(--stroke);
  border-radius: 18px;
  padding: 12px 14px;
}}

.kpi-label {{
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.3px;
}}
.kpi-value {{
  font-size: 26px;
  font-weight: 800;
  margin-top: 2px;
}}
.kpi-sub {{
  color: var(--muted);
  font-size: 12px;
  margin-top: 4px;
}}

.pill {{
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(47,128,237,0.14);
  border: 1px solid rgba(47,128,237,0.22);
  color: rgba(255,255,255,0.9);
  font-size: 12px;
}}

hr {{
  border: none;
  height: 1px;
  background: rgba(255,255,255,0.08);
  margin: 10px 0 14px 0;
}}

.stDownloadButton, .stButton {{ display: none !important; }}
</style>
""",
    unsafe_allow_html=True,
)

# ---------- Helpers ----------
def money(x: float) -> str:
    try:
        return "${:,.0f}".format(float(x))
    except Exception:
        return "$0"

def safe_num(x) -> float:
    try:
        if pd.isna(x):
            return 0.0
        return float(x)
    except Exception:
        return 0.0

def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    return df

def find_col(df: pd.DataFrame, candidates):
    cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    # fuzzy contains
    for c in df.columns:
        cl = c.lower()
        for cand in candidates:
            if cand.lower() in cl:
                return c
    return None

def parse_date_series(s: pd.Series) -> pd.Series:
    # robust parse; works with many CSV exports
    return pd.to_datetime(s, errors="coerce", infer_datetime_format=True).dt.date

def classify_type(text: str) -> str:
    """
    Map line item descriptions into WHALER buckets:
    chat, video, gifts, other
    """
    t = (text or "").lower()

    # video-ish
    if any(k in t for k in ["video", "cam", "call", "phone", "live", "1:1", "one-on-one"]):
        return "Video"

    # chat-ish
    if any(k in t for k in ["chat", "message", "msg", "text", "dm", "conversation"]):
        return "Chat"

    # gifts-ish
    if any(k in t for k in ["gift", "rose", "tip", "present", "token", "sticker"]):
        return "Gifts"

    return "Other"

def blur_name(name: str, idx: int) -> str:
    # idx is 1-based rank
    if idx <= 3:
        return name
    # blur-ish: keep first letter and last letter (if any)
    n = (name or "").strip()
    if len(n) <= 2:
        return "•••"
    return n[0] + "•" * max(3, len(n) - 2) + n[-1]

def kpi_card(label: str, value: str, sub: str = ""):
    st.markdown(
        f"""
<div class="card-tight">
  <div class="kpi-label">{label}</div>
  <div class="kpi-value">{value}</div>
  <div class="kpi-sub">{sub}</div>
</div>
""",
        unsafe_allow_html=True,
    )

def stacked_bar_top3(top3_breakdown: pd.DataFrame):
    """
    top3_breakdown columns: Name, Chat, Video, Gifts, Other, Total
    """
    labels = top3_breakdown["Name"].tolist()
    categories = ["Chat", "Video", "Gifts", "Other"]
    vals = {cat: top3_breakdown[cat].astype(float).values for cat in categories}

    fig, ax = plt.subplots(figsize=(8.8, 3.8), dpi=150)

    bottom = np.zeros(len(labels))
    for i, cat in enumerate(categories):
        ax.bar(labels, vals[cat], bottom=bottom)
        bottom += vals[cat]

    ax.set_title("Top 3 Whale Breakdown", fontsize=12, fontweight="bold")
    ax.set_ylabel("Earnings ($)")
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_alpha(0.15)
    ax.spines["right"].set_alpha(0.15)
    ax.spines["left"].set_alpha(0.15)
    ax.spines["bottom"].set_alpha(0.15)
    ax.tick_params(axis="x", rotation=0)

    # Legend
    ax.legend(categories, loc="upper right", frameon=False)

    st.pyplot(fig, use_container_width=True)

def line_daily(daily: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8.8, 3.0), dpi=150)
    ax.plot(daily["Date"], daily["Total"].values)
    ax.set_title("Daily Earnings", fontsize=12, fontweight="bold")
    ax.set_ylabel("Earnings ($)")
    ax.grid(axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=0)
    st.pyplot(fig, use_container_width=True)

# ---------- Header ----------
left, right = st.columns([0.72, 0.28], vertical_alignment="center")

with left:
    st.markdown('<div class="h1">WHALER</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub">Upload your earnings report. Get instant clarity on who actually pays you.</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div style="text-align:right"><span class="pill">V1 — Free</span></div>', unsafe_allow_html=True)

st.markdown("<hr/>", unsafe_allow_html=True)

# ---------- Upload ----------
st.markdown(
    """
<div class="card">
  <div style="font-weight:700; font-size:16px;">Drop your CSV export</div>
  <div class="sub">We’ll dedupe automatically and show the whales that fund your income.</div>
</div>
""",
    unsafe_allow_html=True,
)

files = st.file_uploader(
    "",
    type=["csv"],
    accept_multiple_files=True,
    help="Upload one or multiple CSV files (we dedupe across them).",
)

if not files:
    st.stop()

# ---------- Load + Combine ----------
dfs = []
for f in files:
    try:
        content = f.read()
        # try utf-8 then fallback
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception:
            df = pd.read_csv(io.BytesIO(content), encoding="latin-1")
        dfs.append(normalize_cols(df))
    except Exception:
        pass

if not dfs:
    st.error("Couldn’t read any CSVs. Try exporting again and re-uploading.")
    st.stop()

raw = pd.concat(dfs, ignore_index=True)

# ---------- Column detection (export-agnostic) ----------
col_date = find_col(raw, ["date", "created", "timestamp", "time"])
col_desc = find_col(raw, ["description", "details", "type", "note", "memo"])
col_credit = find_col(raw, ["credit", "credits", "amount", "earned", "earnings", "gross", "total"])
col_debit = find_col(raw, ["debit", "debits", "fee", "fees"])
col_user = find_col(raw, ["user", "username", "from", "payer", "sender", "customer", "name"])

# Minimum requirements
if col_date is None or col_credit is None:
    st.error(
        "This CSV format is missing required columns. I need at least a Date column and an Amount/Credit column."
    )
    st.stop()

df = raw.copy()

# Parse
df["Date"] = parse_date_series(df[col_date])
df["Description"] = df[col_desc].astype(str) if col_desc else ""
df["Whale"] = df[col_user].astype(str) if col_user else "Unknown"

# Credits/Debits
df["Credits"] = df[col_credit].apply(safe_num)
df["Debits"] = df[col_debit].apply(safe_num) if col_debit else 0.0

# If "Amount" exists but includes negatives, normalize into Credits/Debits
# (we keep it simple: negative -> debit)
neg_mask = df["Credits"] < 0
if neg_mask.any():
    df.loc[neg_mask, "Debits"] = df.loc[neg_mask, "Credits"].abs()
    df.loc[neg_mask, "Credits"] = 0.0

# Type buckets
df["Category"] = df["Description"].apply(classify_type)

# ---------- Dedupe Rule (your locked rule) ----------
# Composite key: Date + Description + Credits + Debits
df["__key__"] = (
    df["Date"].astype(str)
    + "||"
    + df["Description"].astype(str)
    + "||"
    + df["Credits"].round(2).astype(str)
    + "||"
    + df["Debits"].round(2).astype(str)
)
df = df.drop_duplicates(subset="__key__", keep="first").drop(columns=["__key__"])

# Clean date nulls
df = df[df["Date"].notna()].copy()

# Period bounds
min_d = df["Date"].min()
max_d = df["Date"].max()

# Total earnings (revenue only, per your instruction)
total_earnings = df["Credits"].sum()

# Daily aggregates
daily = (
    df.groupby("Date", as_index=False)["Credits"]
    .sum()
    .rename(columns={"Credits": "Total"})
    .sort_values("Date")
)

# Days in sample for projections
days_in_sample = (pd.to_datetime(max_d) - pd.to_datetime(min_d)).days + 1
days_in_sample = max(1, int(days_in_sample))
daily_avg = total_earnings / days_in_sample

monthly_projection = daily_avg * 30.0
yearly_projection = daily_avg * 365.0

# Whale rollup
whales = (
    df.groupby("Whale", as_index=False)["Credits"]
    .sum()
    .rename(columns={"Credits": "Total"})
    .sort_values("Total", ascending=False)
)
total_whales = int(whales.shape[0])

# If you have separate "calls" and "chats" columns in some exports, we can count events by category:
total_chats = int((df["Category"] == "Chat").sum())
total_calls = int((df["Category"] == "Video").sum())

# Top 10 whales table (blur 4-10)
top10 = whales.head(10).copy()
top10["Rank"] = np.arange(1, len(top10) + 1)
top10["Whale (blurred)"] = [
    blur_name(n, r) for n, r in zip(top10["Whale"].tolist(), top10["Rank"].tolist())
]
top10["Earnings"] = top10["Total"].apply(money)
top10_display = top10[["Rank", "Whale (blurred)", "Earnings"]]

# Top 3 breakdown (stacked by category)
top3_names = whales.head(3)["Whale"].tolist()
df_top3 = df[df["Whale"].isin(top3_names)].copy()

pivot = (
    df_top3.pivot_table(
        index="Whale",
        columns="Category",
        values="Credits",
        aggfunc="sum",
        fill_value=0.0,
    )
    .reset_index()
)

for col in ["Chat", "Video", "Gifts", "Other"]:
    if col not in pivot.columns:
        pivot[col] = 0.0

pivot["Total"] = pivot[["Chat", "Video", "Gifts", "Other"]].sum(axis=1)

# Keep in same order as whales top3
pivot["__order__"] = pivot["Whale"].apply(lambda x: top3_names.index(x) if x in top3_names else 999)
pivot = pivot.sort_values("__order__").drop(columns="__order__")
pivot = pivot.rename(columns={"Whale": "Name"})

# ---------- Layout ----------
# Top KPI row (clean, Stripe-ish)
k1, k2, k3, k4, k5 = st.columns([1.35, 1, 1, 1, 1])

with k1:
    kpi_card("Total Earnings this Period", money(total_earnings), f"{min_d} → {max_d}")
with k2:
    kpi_card("Daily Average", money(daily_avg), f"Based on {days_in_sample} day(s)")
with k3:
    kpi_card("Monthly Projection", money(monthly_projection), "If continued at this rate")
with k4:
    kpi_card("Yearly Projection", money(yearly_projection), "If continued at this rate")
with k5:
    kpi_card("Total Whales", f"{total_whales:,}", "Unique paying users")

st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

# Second KPI row: calls/chats + quick context
a1, a2, a3 = st.columns([1, 1, 1])
with a1:
    kpi_card("Total Chats", f"{total_chats:,}", "Chat-type transactions")
with a2:
    kpi_card("Total Calls", f"{total_calls:,}", "Video/call-type transactions")
with a3:
    # show top whale concentration
    top3_total = whales.head(3)["Total"].sum()
    concentration = (top3_total / total_earnings * 100.0) if total_earnings > 0 else 0.0
    kpi_card("Top 3 Concentration", f"{concentration:,.1f}%", "How much 3 whales drive")

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# Main body: left table, right charts
left_col, right_col = st.columns([0.92, 1.08], gap="large")

with left_col:
    st.markdown(
        """
<div class="card">
  <div style="font-weight:750; font-size:16px;">Top 10 Whales</div>
  <div class="sub">#4–#10 are blurred in WHALER V1.</div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.dataframe(
        top10_display,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
<div class="card">
  <div style="font-weight:750; font-size:16px;">Upgrade teasers</div>
  <div class="sub">Sprinkle these CTAs without being spammy.</div>
  <div style="margin-top:10px;">
    <div class="pill">Unlock whales #4–#10 → Whaler Plus</div>
    <div style="height:8px;"></div>
    <div class="pill">See concentration % per whale → Whaler Pro</div>
    <div style="height:8px;"></div>
    <div class="pill">Identify time-wasters → Leach’s List (Plus)</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

with right_col:
    st.markdown(
        """
<div class="card">
  <div style="font-weight:750; font-size:16px;">Top 3 Whale Breakdown</div>
  <div class="sub">Where the money actually comes from (Chat / Video / Gifts / Other).</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Chart
    stacked_bar_top3(pivot[["Name", "Chat", "Video", "Gifts", "Other", "Total"]])

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
<div class="card">
  <div style="font-weight:750; font-size:16px;">Trend</div>
  <div class="sub">Daily earnings over the uploaded period.</div>
</div>
""",
        unsafe_allow_html=True,
    )
    line_daily(daily)

# Footer note
st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
st.markdown(
    f"""
<div class="sub" style="text-align:center;">
  Dedupe rule: Date + Description + Credits + Debits • Revenue only • WHALER V1
</div>
""",
    unsafe_allow_html=True,
)
