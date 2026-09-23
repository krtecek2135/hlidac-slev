import streamlit as st
import requests
import re
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Hlídač slev",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 Hlídač slev - diagnostika")

produkt = st.text_input(
    "Hledaný produkt",
    "Pampers"
)

if st.button("Analyzovat"):

    url = f"https://www.kupi.cz/hledej?f={produkt}"

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20
        )

        html = response.text

        st.success(f"Status: {response.status_code}")

        soup = BeautifulSoup(html, "html.parser")

        st.subheader("Titulek stránky")

        if soup.title:
            st.write(soup.title.text)

        st.subheader("Statistiky")

        st.write("Počet znaků HTML:", len(html))
        st.write("Počet výskytů 'Kč':", html.count("Kč"))
        st.write("Počet výskytů 'Albert':", html.count("Albert"))
        st.write("Počet výskytů 'Kaufland':", html.count("Kaufland"))
        st.write("Počet výskytů 'Tesco':", html.count("Tesco"))

        st.subheader("Ukázky textu obsahující Kč")

        matches = re.findall(
            r".{0,100}Kč.{0,100}",
            html,
            flags=re.IGNORECASE
        )

        if matches:
            for i, m in enumerate(matches[:20], start=1):
                st.text(f"{i}. {m}")
        else:
            st.warning("Nenalezen žádný text obsahující Kč")

        st.subheader("Vyhledání důležitých slov")

        keywords = [
            produkt,
            "Pampers",
            "Premium",
            "Care",
            "Albert",
            "Kaufland",
            "Tesco",
            "Billa",
            "Penny"
        ]

        for word in keywords:
            if word.lower() in html.lower():
                st.success(f"Nalezeno: {word}")
            else:
                st.error(f"Nenalezeno: {word}")

        with st.expander("Prvních 5000 znaků HTML"):
            st.code(html[:5000])

    except Exception as e:
        st.error(str(e))
