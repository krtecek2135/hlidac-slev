import streamlit as st
import pandas as pd
import requests

from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin

HISTORY_FILE = "history.csv"

if not Path(HISTORY_FILE).exists():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        f.write("datum,produkt,cena\n")

st.set_page_config(
    page_title="Hlídač slev",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 Hlídač slev")
st.caption("Vyhledávání akčních nabídek v Lidlu a Kauflandu")

produkt = st.text_input(
    "Hledaný produkt",
    value="Pampers"
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

    # Každý tento blok představuje jednu obchodní nabídku.
    bloky_akci = soup.select(".discount_row")

    vysledky = []

    for blok in bloky_akci:

        obchod_element = blok.select_one(
            ".discounts_shop_name"
        )

        cena_element = blok.select_one(
            ".discount_price_value"
        )

        platnost_element = blok.select_one(
            ".discounts_validity"
        )

        poznamka_element = blok.select_one(
            ".discount_note"
        )

        produkt_element = blok.select_one(
            ".btn_list_add[data-product]"
        )

        letak_element = blok.select_one(
            ".btn_link_leaflet[href]"
        )

        if obchod_element is None or cena_element is None:
            continue

        obchod = obchod_element.get_text(
            " ",
            strip=True
        )

        # Zobrazíme pouze Lidl a Kaufland.
        if obchod.lower() not in ["lidl", "kaufland"]:
            continue

        cena_text = cena_element.get_text(
            " ",
            strip=True
        )

        cena_cislo = (
            cena_text
            .replace("Kč", "")
            .replace("\xa0", "")
            .replace(" ", "")
            .replace(",", ".")
            .strip()
        )

        try:
            cena_cislo = float(cena_cislo)
        except ValueError:
            cena_cislo = None

        if produkt_element:
            nazev_produktu = produkt_element.get(
                "data-product",
                produkt
            )
        else:
            nazev_produktu = produkt

        if platnost_element:
            platnost = platnost_element.get_text(
                " ",
                strip=True
            )
        else:
            platnost = "Neuvedeno"

        if poznamka_element:
            poznamka = poznamka_element.get_text(
                " ",
                strip=True
            )
        else:
            poznamka = ""

        if letak_element:
            odkaz_na_letak = urljoin(
                "https://www.kupi.cz",
                letak_element.get("href")
            )
        else:
            odkaz_na_letak = ""

        vysledky.append(
            {
                "Produkt": nazev_produktu,
                "Obchod": obchod,
                "Cena (Kč)": cena_cislo,
                "Cena": cena_text,
                "Platnost": platnost,
                "Poznámka": poznamka,
                "Leták": odkaz_na_letak
            }
        )

    if not vysledky:
        st.warning(
            "Pro zadaný produkt nebyla nalezena nabídka "
            "v Lidlu ani Kauflandu."
        )

        st.info(
            f"Celkem bylo na stránce nalezeno "
            f"{len(bloky_akci)} nabídkových bloků, "
            "ale žádný nepatřil Lidlu nebo Kauflandu."
        )

    else:
        df = pd.DataFrame(vysledky)

        df = df.sort_values(
            by="Cena (Kč)",
            na_position="last"
        )

        st.success(
            f"Nalezeno nabídek: {len(df)}"
        )

        nejlevnejsi = df.iloc[0]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Nejnižší cena",
                nejlevnejsi["Cena"]
            )

        with col2:
            st.metric(
                "Nejlevnější obchod",
                nejlevnejsi["Obchod"]
            )

        with col3:
            st.metric(
                "Počet nabídek",
                len(df)
            )

        st.subheader("Nalezené nabídky")

        st.dataframe(
            df[
                [
                    "Produkt",
                    "Obchod",
                    "Cena",
                    "Platnost",
                    "Poznámka",
                    "Leták"
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Leták": st.column_config.LinkColumn(
                    "Odkaz na leták",
                    display_text="Otevřít leták"
                )
            }
        )
