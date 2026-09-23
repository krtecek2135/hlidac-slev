import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Hlídač slev",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 Hlídač slev")

# Načtení dat
df = pd.read_csv("products.csv")

# Výběr produktu
produkt = st.selectbox(
    "Vyber produkt",
    sorted(df["produkt"].unique())
)

# Filtrace
filtrovano = df[df["produkt"] == produkt]

st.subheader("Aktuální nabídky")

st.dataframe(
    filtrovano.sort_values("cena"),
    use_container_width=True
)

# Nejlevnější nabídka
nejlevnejsi = filtrovano.loc[filtrovano["cena"].idxmin()]

st.success(
    f"Nejlepší nabídka: {nejlevnejsi['obchod']} za {nejlevnejsi['cena']} Kč"
)
