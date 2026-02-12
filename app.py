import io
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# ---------------------------
# Page setup + premium styling
# ---------------------------
st.set_page_config(page_title="WHALER", layout="centered")

st.markdown(
    """
<style>
/* Hide Streamlit chrome */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Layout tightening */
.block-container {
    padding-top: 2.25rem;
    padding-bottom: 2.5rem;
    max-width: 860px;
}

/* Typography */
h1, h2, h3 { letter-spacing: -0.02em; }
.small-muted { color: rgba(255,255,255,0.65); font-size: 0.9rem; }

/* Cards */
.card {
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 18px;
    padding: 18px 18px;
    background: rgba(255,255,255,0.03);
    box-shadow: 0 8px 30px rgba(0,0,0,0.14);
}
.card-tight { padding: 14px 16px; }
hr.soft {
    border: 0;
    height: 1px;
    background: rgba(255,255,255,0.10);
    margin: 18px 0;
}

/* Whale list */
.whale-row {
    display:flex;
    justify-content: space-between;
    padding: 10px 12px;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.10);
    background: rgba(255,255,255,0.02);
    margin-bottom: 8px;
}
.whale-blur {
    filter: blur(7px);
    opacity: 0.75;
}
.lock {
    font-weight: 600;
    color: rgba(255,255,255,0.70);
}
.badge {
    display:inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.14);
    background: rgba(255,255,255,0.05);
    font-size: 0.85rem;
    margin-right: 6px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------
# Helpers
# ---------------------------
def money_to_float(x):
    if pd.isna(x):
        return 0.0
    s = str(x).strip().replace("$", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0

def extract_user(description: str) -> str:
    # First token from Description
    if not isinstance(description, str) or not description.strip():
        return "Unknown"
    return description.strip().split(" ")[0]

def fig_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=200)
    buf.seek(0)
    return buf

def currency(x: float) -> str:
    return f"${x:,.2f}"

# ---------------------------
# Header
# ---------------------------
st.markdown("<span class='badge'>V1</span><span class='badge'>CSV → Whale Clarity</span>", unsafe_allow_html=True)
st.title("WHALER")
st.markdown(
    "<div class='small-muted'>Upload your earnings CSV → get instant clarity on who funds your income. "
    "<strong>No logins.</strong> <strong>We don’t store your file.</strong></div>",
    unsafe_allow_html=True,
)

st.write("")

# Upload card
st.markdown("<div class='card'>", unsafe_allow_html=True)
uploaded = st.file_uploader("Drop your CSV here", type=["csv"])
st.markdown(
    "<div class='small-muted'>Privacy-first: your CSV is processed in-session and not saved.</div>",
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# Main logic
# ---------------------------
if uploaded:
    df = pd.read_csv(uploaded)

    # Required columns
    required = {"Date", "Description", "Credits"}
    if not required.issubset(df.columns):
        st.error("CSV must include columns: Date, Description, Credits")
        st.stop()

    # Normalize
    df["amount"] = df["Credits"].apply(money_to_float)
    df["user"] = df["Description"].apply(extract_user)
    df["dt"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["dt"])
    df["day"] = df["dt"].dt.date

    # Deduplicate rule: Date + Description + Credits + Debits (if present)
    debits = df["Debits"].astype(str) if "Debits" in df.columns else ""
    df["dedupe_key"] = (
        df["Date"].astype(str) + "||" +
        df["Description"].astype(str) + "||" +
        df["Credits"].astype(str) + "||" +
        debits
    )
    pre = len(df)
    df = df.drop_duplicates("dedupe_key")
    post = len(df)

    # Compute whales
    whales = df.groupby("user")["amount"].sum().sort_values(ascending=False)
    top3 = whales.head(3)
    top10 = whales.head(10)

    total = float(df["amount"].sum())
    top1_amt = float(top3.iloc[0]) if len(top3) >= 1 else 0.0
    top3_amt = float(top3.sum()) if len(top3) >= 1 else 0.0
    top3_pct = (top3_amt / total * 100.0) if total > 0 else 0.0

    # Daily totals
    daily = df.groupby("day")["amount"].sum().sort_index()

    st.write("")
    st.markdown("<div class='card'>", unsafe_allow_html=True)

    # Punchline metrics (holy shit moment)
    st.subheader("Your income is concentrated")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total (this file)", currency(total))
    c2.metric("Top whale", currency(top1_amt))
    c3.metric("Top 3 share", f"{top3_pct:.0f}%")

    st.markdown(
        "<div class='small-muted'>"
        f"Deduped transactions: <strong>{pre-post}</strong> removed (kept {post})."
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    # Whale ranking card (top 3 visible, rest blurred)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Whale ranking")

    if len(top10) == 0:
        st.info("No earnings found in this file after cleaning.")
    else:
        # show top 3 clean
        for i, (u, amt) in enumerate(top10.items(), start=1):
            if i <= 3:
                st.markdown(
                    f"<div class='whale-row'><div><strong>#{i}</strong> {u}</div><div><strong>{currency(float(amt))}</strong></div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='whale-row whale-blur'><div><strong>#{i}</strong> {u}</div><div><strong>{currency(float(amt))}</strong></div></div>",
                    unsafe_allow_html=True,
                )

        st.markdown(
            "<div class='lock'>🔒 Blurring ranks 4+ is the V2 upsell hook. V1: prove the point fast.</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    # Charts card (clean, minimal)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Visuals")

    st.markdown("<hr class='soft'/>", unsafe_allow_html=True)

    st.markdown("<div class='small-muted'><strong>AFTER:</strong> whales fund the business</div>", unsafe_allow_html=True)
    fig_after = plt.figure()
    top10.plot(kind="bar")
    plt.xlabel("User")
    plt.ylabel("Total ($)")
    plt.tight_layout()
    st.pyplot(fig_after)

    st.markdown("<hr class='soft'/>", unsafe_allow_html=True)

    st.markdown("<div class='small-muted'><strong>BEFORE:</strong> earnings feel random</div>", unsafe_allow_html=True)
    fig_before = plt.figure()
    daily.plot(kind="bar")
    plt.xlabel("Day")
    plt.ylabel("Total ($)")
    plt.tight_layout()
    st.pyplot(fig_before)

    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    # Downloads
    st.markdown("<div class='card card-tight'>", unsafe_allow_html=True)
    st.markdown("<strong>Downloads</strong>", unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    d1.download_button("Download AFTER (PNG)", fig_png(fig_after), "after_whaler.png", "image/png")
    d2.download_button("Download BEFORE (PNG)", fig_png(fig_before), "before_whaler.png", "image/png")
    st.markdown("</div>", unsafe_allow_html=True)
