import streamlit as st
import requests
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Hlídač slev",
    page_icon="🛒"
)

st.title("🛒 Hlídač slev")

produkt = st.text_input(
    "Produkt",
    "Pampers"
)

if st.button("Najít akce"):

    url = f"https://www.kupi.cz/hledej?f={produkt}"

    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    st.success(f"Status: {response.status_code}")

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    ceny = soup.select(".discount_price_value")

    st.subheader("Nalezené ceny")

    if ceny:

        for cena in ceny[:30\]:
            text = cena.get_text(strip=True)
            st.write(text)

    else:
        st.error(
            "Třída discount_price_value nebyla nalezena"
        )

    with st.expander("Diagnostika HTML"):

        for element in soup.select(
            ".discount_price_value"
        )[:5\]:

            st.code(
                str(
                    element.parent
                )
            )
