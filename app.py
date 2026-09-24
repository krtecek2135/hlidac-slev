import streamlit as st
import requests
from bs4 import BeautifulSoup

st.title("Kupi diagnostika")

produkt = st.text_input("Produkt", "Pampers")

if st.button("Analyzovat"):

    url = f"https://www.kupi.cz/hledej?f={produkt}"

    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    ceny = soup.find_all(
        "strong",
        class_="discount_price_value"
    )

    st.write("Počet cen:", len(ceny))

    if ceny:

        st.subheader("První nalezený blok")

        prvek = ceny[0]

        rodic = prvek.parent

        st.code(
            rodic.prettify()
        )

        st.subheader("Celý nadřazený blok")

        blok = rodic.parent

        st.code(
            blok.prettify()
        )
