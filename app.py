import streamlit as st
import requests
from bs4 import BeautifulSoup

produkt = st.text_input("Produkt", "Pampers")

if st.button("Vyhledat"):

    url = f"https://www.kupi.cz/hledej?f={produkt}"

    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    st.write("Status:", response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")

    st.subheader("Titulek stránky")

    st.write(soup.title.text if soup.title else "Nenalezen")

    st.subheader("Prvních 3000 znaků HTML")

    st.code(response.text[:3000])
