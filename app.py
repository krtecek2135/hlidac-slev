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
st.caption("Vyhledávání slev na Kupi.cz")

produkt = st.text_input(
    "Hledaný produkt",
    "Pampers"
)

if st.button("Najít akce", type="primary"):

    if not produkt.strip():
        st.warning("Zadej název produktu.")
        st.stop()

    hledany_produkt = quote_plus(produkt.strip())
    url = f"https://www.kupi.cz/hledej?f={hledany_produkt}"

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

    except requests.RequestException as chyba:
        st.error(f"Nepodařilo se načíst data: {chyba}")
        st.stop()

    soup = BeautifulSoup(response.text, "html.parser")

    ceny = soup.find_all(
        "strong",
        class_="discount_price_value"
    )

    st.success(
        f"Stránka byla načtena. Nalezeno cen: {len(ceny)}"
    )

    if ceny:

        vysledky = []

        for cena in ceny[:30]:
            vysledky.append({
                "Cena": cena.get_text(strip=True)
            })

        st.subheader("Nalezené ceny")

        st.dataframe(
            vysledky,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.warning(
            "Nebyla nalezena žádná cena."
        )

    with st.expander("Diagnostika prvního výsledku"):

        if ceny:

            prvek = ceny[0]

            st.write("Text ceny:")
            st.write(prvek.get_text(strip=True))

            rodic = prvek

            for uroven in range(1, 9):

                if rodic.parent is None:
                   break

                rodic = rodic.parent

                st.markdown(
                    f"### Nadřazená úroveň {uroven}"
                )

                st.code(
                    str(rodic)[:5000],
                    language="html"
                )
