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
st.caption("Vyhledávání nabídek v řetězcích Lidl a Kaufland")

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
    ceny = soup.select(".discount_price_value")

    st.success(
        f"Stránka byla načtena. Nalezeno cenových údajů: {len(ceny)}"
    )

    st.subheader("Nalezené ceny")

    if ceny:
        nalezene_ceny = []

        for cena in ceny[:30\]:
            text_ceny = cena.get_text(" ", strip=True)

            # Hledání většího rodičovského bloku
            rodic = cena

            for _ in range(8):
                if rodic.parent is None:
                    break

                rodic = rodic.parent
                obsah = rodic.get_text(" ", strip=True).lower()

                if "lidl" in obsah or "kaufland" in obsah:
                    obchod = (
                        "Lidl"
                        if "lidl" in obsah
                        else "Kaufland"
                    )

                    nalezene_ceny.append(
                        {
                            "Obchod": obchod,
                            "Cena": text_ceny
                        }
                    )
                    break

        if nalezene_ceny:
            st.dataframe(
                nalezene_ceny,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(
                "Ceny byly nalezeny, ale v jejich okolí se nepodařilo "
                "jednoznačně určit Lidl nebo Kaufland."
            )

            for cena in ceny[:10\]:
                st.write(cena.get_text(" ", strip=True))

    else:
        st.error(
            "Na stránce nebyly nalezeny žádné prvky "
            "s třídou discount_price_value."
        )

    with st.expander("Diagnostika prvního výsledku"):

        if ceny:
            rodic = ceny[0]

            for uroven in range(1, 9):
                if rodic.parent is None:
                    break

                rodic = rodic.parent

                st.markdown(f"#### Nadřazená úroveň {uroven}")
                st.code(
                    str(rodic)[:8000],
                    language="html"
                )
`
