import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

st.set_page_config(
    page_title="Hlídač slev",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 Hlídač slev")
st.caption("Test napojení na Kupi.cz")

produkt = st.text_input(
    "Hledaný produkt",
    "Pampers"
)

if st.button("Najít akce", type="primary"):

    if not produkt.strip():
        st.warning("Zadej název produktu.")
        st.stop()

    url = f"https://www.kupi.cz/hledej?f={quote_plus(produkt)}"

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            },
            timeout=15
        )

        response.raise_for_status()

    except Exception as e:
        st.error(f"Chyba při načítání: {e}")
        st.stop()

    soup = BeautifulSoup(response.text, "html.parser")

    ceny = soup.find_all(
        "strong",
        class_="discount_price_value"
    )

    st.success(
        f"Nalezeno {len(ceny)} cen"
    )

    st.subheader("Nalezené ceny")

    for cena in ceny[:20]:
        st.write(cena.get_text(strip=True))

    if ceny:

        st.divider()

        st.subheader("Diagnostika prvního výsledku")

        aktualni = ceny[0]

        st.write(
            "První nalezená cena:",
            aktualni.get_text(strip=True)
        )

        rodic = aktualni

        for uroven in range(1, 7):

            if rodic.parent is None:
                break

            rodic = rodic.parent

            with st.expander(
                f"Nadřazená úroveň {uroven}"
            ):
                st.code(
                    rodic.prettify()[:10000],
                    language="html"
                )
