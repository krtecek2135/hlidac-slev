import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Hlídač slev",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 Hlídač slev")

produkt = st.text_input(
    "Hledaný produkt",
    "Pampers"
)

if st.button("Vyhledat"):

    url = f"https://www.kupi.cz/hledej?f={produkt}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        st.write(f"Status: {response.status_code}")

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        st.write("Stránka načtena.")

    except Exception as e:
        st.error(str(e))
