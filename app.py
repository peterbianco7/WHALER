import io
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="WHALER", layout="centered")

st.title("WHALER")
st.caption("Upload an earnings CSV → get whale clarity. No logins. No account access.")

uploaded = st.file_uploader("Drop your CSV here", type=["csv"])

def money_to_float(x):
    if pd.isna(x):
        return 0.0
    s = str(x).strip().replace("$", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0

def extract_user(description: str) -> str:
    if not isinstance(description, str) or not description.strip():
        return "Unknown"
    # first word in the Description
    return description.strip().split(" ")[0]

if uploaded:
    df = pd.read_csv(uploaded)

    # Required columns in your export
    if not {"Date", "Description", "Credits"}.issubset(df.columns):
        st.error("CSV must include columns: Date, Description, Credits")
        st.stop()

    df["amount"] = df["Credits"].apply(money_to_float)
    df["user"] = df["Description"].apply(extract_user)
    df["dt"] = pd.to_datetime(df["Date"], errors="coerce")
    df["day"] = df["dt"].dt.date

    # Deduplicate: Date + Description + Credits + Debits (if present)
    debits = df["Debits"].astype(str) if "Debits" in df.columns else ""
    df["dedupe_key"] = (
        df["Date"].astype(str) + "||" +
        df["Description"].astype(str) + "||" +
        df["Credits"].astype(str) + "||" +
        debits
    )
    df = df.drop_duplicates("dedupe_key")

    total = df["amount"].sum()
    st.metric("Total earnings in file", f"${total:,.2f}")

    # AFTER: whales (top 10)
    whales = df.groupby("user")["amount"].sum().sort_values(ascending=False)
    top10 = whales.head(10)

    st.subheader("AFTER: Whales fund the business")
    fig_after = plt.figure()
    top10.plot(kind="bar")
    plt.xlabel("User")
    plt.ylabel("Total ($)")
    plt.tight_layout()
    st.pyplot(fig_after)

    # BEFORE: daily totals
    daily = df.groupby("day")["amount"].sum().sort_index()

    st.subheader("BEFORE: Earnings feel random")
    fig_before = plt.figure()
    daily.plot(kind="bar")
    plt.xlabel("Day")
    plt.ylabel("Total ($)")
    plt.tight_layout()
    st.pyplot(fig_before)

    # Downloads
    def fig_png(fig):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=200)
        buf.seek(0)
        return buf

    st.download_button("Download AFTER image (PNG)", fig_png(fig_after), "after_whaler.png", "image/png")
    st.download_button("Download BEFORE image (PNG)", fig_png(fig_before), "before_whaler.png", "image/png")
