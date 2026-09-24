import streamlit as st
import pandas as pd
import requests
import plotly.express as px

from bs4 import BeautifulSoup
from datetime import date
from pathlib import Path
from urllib.parse import quote_plus, urljoin


HISTORY_FILE = Path("history.csv")
POVOLENE_OBCHODY = ["lidl", "kaufland"]


st.set_page_config(
    page_title="Hlídač slev",
    page_icon="🛒",
    layout="wide"
)


def preved_cenu_na_cislo(cena_text):
    """
    Převede například '179,90 Kč' na číslo 179.90.
    Pokud převod selže, vrátí None.
    """

    if not cena_text:
        return None

    vycistena_cena = (
        cena_text
        .replace("Kč", "")
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )

    try:
        return float(vycistena_cena)
    except ValueError:
        return None


def nacti_historii():
    """
    Bezpečně načte historii.
    Zvládne také situaci, kdy soubor neexistuje nebo je prázdný.
    """

    pozadovane_sloupce = [
        "Datum",
        "Hledaný výraz",
        "Produkt",
        "Obchod",
        "Cena (Kč)",
        "Cena",
        "Platnost",
        "Poznámka",
        "Leták"
    ]

    if not HISTORY_FILE.exists():
        return pd.DataFrame(columns=pozadovane_sloupce)

    if HISTORY_FILE.stat().st_size == 0:
        return pd.DataFrame(columns=pozadovane_sloupce)

    try:
        historie = pd.read_csv(HISTORY_FILE)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame(columns=pozadovane_sloupce)

    for sloupec in pozadovane_sloupce:
        if sloupec not in historie.columns:
            historie[sloupec] = ""

    historie["Cena (Kč)"] = pd.to_numeric(
        historie["Cena (Kč)"],
        errors="coerce"
    )

    return historie[pozadovane_sloupce]


def uloz_historii(df, hledany_vyraz):
    """
    Přidá nalezené nabídky do historie.
    Stejná nabídka se ve stejný den neuloží opakovaně.
    """

    if df.empty:
        return 0

    nova_historie = df.copy()

    nova_historie.insert(
        0,
        "Datum",
        date.today().isoformat()
    )

    nova_historie.insert(
        1,
        "Hledaný výraz",
        hledany_vyraz.strip()
    )

    stara_historie = nacti_historii()

    pocet_pred_ulozenim = len(stara_historie)

    kompletni_historie = pd.concat(
        [stara_historie, nova_historie],
        ignore_index=True
    )

    kompletni_historie["Cena (Kč)"] = pd.to_numeric(
        kompletni_historie["Cena (Kč)"],
        errors="coerce"
    )

    kompletni_historie = kompletni_historie.drop_duplicates(
        subset=[
            "Datum",
            "Produkt",
            "Obchod",
            "Cena (Kč)",
            "Platnost"
        ],
        keep="last"
    )

    kompletni_historie = kompletni_historie.sort_values(
        by=["Datum", "Produkt", "Obchod"],
        ascending=[True, True, True]
    )

    kompletni_historie.to_csv(
        HISTORY_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    return len(kompletni_historie) - pocet_pred_ulozenim


def stahni_nabidky(hledany_produkt):
    """
    Načte nabídky a vybere pouze Lidl a Kaufland.
    """

    zakodovany_produkt = quote_plus(hledany_produkt.strip())
    url = f"https://www.kupi.cz/hledej?f={zakodovany_produkt}"

    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },
        timeout=20
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

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

        if obchod.lower() not in POVOLENE_OBCHODY:
            continue

        cena_text = cena_element.get_text(
            " ",
            strip=True
        )

        cena_cislo = preved_cenu_na_cislo(
            cena_text
        )

        if produkt_element:
            nazev_produktu = produkt_element.get(
                "data-product",
                hledany_produkt
            )
        else:
            nazev_produktu = hledany_produkt

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
                letak_element.get("href", "")
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

    df = pd.DataFrame(vysledky)

    if not df.empty:
        df = df.drop_duplicates(
            subset=[
                "Produkt",
                "Obchod",
                "Cena (Kč)",
                "Platnost"
            ]
        )

        df = df.sort_values(
            by="Cena (Kč)",
            na_position="last"
        )

    return df, len(bloky_akci)


def zobraz_historii(hledany_vyraz):
    """
    Zobrazí historii odpovídající aktuálnímu hledanému výrazu.
    """

    historie = nacti_historii()

    if historie.empty:
        st.info(
            "Historie zatím neobsahuje žádné záznamy."
        )
        return

    historie["Datum"] = pd.to_datetime(
        historie["Datum"],
        errors="coerce"
    )

    historie["Cena (Kč)"] = pd.to_numeric(
        historie["Cena (Kč)"],
        errors="coerce"
    )

    maska_vyrazu = historie["Hledaný výraz"].str.contains(
        hledany_vyraz,
        case=False,
        na=False,
        regex=False
    )

    maska_produktu = historie["Produkt"].str.contains(
        hledany_vyraz,
        case=False,
        na=False,
        regex=False
    )

    filtrovana_historie = historie[
        maska_vyrazu | maska_produktu
    ].copy()

    filtrovana_historie = filtrovana_historie.dropna(
        subset=["Datum", "Cena (Kč)"]
    )

    if filtrovana_historie.empty:
        st.info(
            "Pro tento hledaný výraz zatím není dostupná historie."
        )
        return

    st.subheader("📈 Historie cen")

    col1, col2, col3 = st.columns(3)

    historicke_minimum = filtrovana_historie["Cena (Kč)"].min()
    historicky_prumer = filtrovana_historie["Cena (Kč)"].mean()
    pocet_zaznamu = len(filtrovana_historie)

    with col1:
        st.metric(
            "Historické minimum",
            f"{historicke_minimum:.2f} Kč".replace(".", ",")
        )

    with col2:
        st.metric(
            "Průměrná zaznamenaná cena",
            f"{historicky_prumer:.2f} Kč".replace(".", ",")
        )

    with col3:
        st.metric(
            "Počet historických záznamů",
            pocet_zaznamu
        )

    grafova_data = (
        filtrovana_historie
        .groupby(
            ["Datum", "Obchod"],
            as_index=False
        )["Cena (Kč)"]
        .min()
    )

    fig = px.line(
        grafova_data,
        x="Datum",
        y="Cena (Kč)",
        color="Obchod",
        markers=True,
        title=f"Vývoj nejnižší ceny pro výraz: {hledany_vyraz}",
        labels={
            "Datum": "Datum",
            "Cena (Kč)": "Cena v Kč",
            "Obchod": "Obchod"
        }
    )

    fig.update_yaxes(
        rangemode="tozero"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    with st.expander("Zobrazit uloženou historii"):
        zobrazena_historie = filtrovana_historie.sort_values(
            by="Datum",
            ascending=False
        ).copy()

        zobrazena_historie["Datum"] = zobrazena_historie[
            "Datum"
        ].dt.strftime("%d. %m. %Y")

        st.dataframe(
            zobrazena_historie[
                [
                    "Datum",
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


st.title("🛒 Hlídač slev")
st.caption("Vyhledávání akčních nabídek v Lidlu a Kauflandu")

produkt = st.text_input(
    "Hledaný produkt",
    value="Kuřecí prsní"
)

hledat = st.button(
    "Najít akce",
    type="primary"
)

if hledat:
    if not produkt.strip():
        st.warning(
            "Zadej název produktu."
        )
        st.stop()

    try:
        with st.spinner("Vyhledávám aktuální nabídky..."):
            df, pocet_bloku = stahni_nabidky(
                produkt
            )

    except requests.Timeout:
        st.error(
            "Načítání trvalo příliš dlouho. Zkus hledání zopakovat."
        )
        st.stop()

    except requests.RequestException as chyba:
        st.error(
            f"Nepodařilo se načíst data: {chyba}"
        )
        st.stop()

    except Exception as chyba:
        st.error(
            f"Při zpracování dat nastala chyba: {chyba}"
        )
        st.stop()

    if df.empty:
        st.warning(
            "Pro zadaný produkt nebyla nalezena nabídka "
            "v Lidlu ani Kauflandu."
        )

        st.info(
            f"Na zdrojové stránce bylo nalezeno "
            f"{pocet_bloku} nabídkových bloků, "
            "ale žádný nepatřil Lidlu nebo Kauflandu."
        )

    else:
        pocet_novych_zaznamu = uloz_historii(
            df,
            produkt
        )

        st.success(
            f"Nalezeno nabídek: {len(df)}"
        )

        if pocet_novych_zaznamu > 0:
            st.caption(
                f"Do historie bylo přidáno "
                f"{pocet_novych_zaznamu} nových záznamů."
            )
        else:
            st.caption(
                "Dnešní nabídky už byly v historii uloženy."
            )

                nejlevnejsi = df.dropna(
            subset=["Cena (Kč)"]
        ).head(1)

        col1, col2, col3 = st.columns(3)

        if not nejlevnejsi.empty:
            nejlevnejsi_radek = nejlevnejsi.iloc[0]

            with col1:
                st.metric(
                    "Nejnižší cena",
                    nejlevnejsi_radek["Cena"]
                )

            with col2:
                st.metric(
                    "Nejlevnější obchod",
                    nejlevnejsi_radek["Obchod"]
                )
        else:
            with col1:
                st.metric(
                    "Nejnižší cena",
                    "Neuvedeno"
                )

            with col2:
                st.metric(
                    "Nejlevnější obchod",
                    "Neuvedeno"
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

        zobraz_historii(produkt)

else:
    historie = nacti_historii()

    if historie.empty:
        st.caption(
            "Historie zatím neobsahuje žádné záznamy."
        )
    else:
        st.caption(
            f"V historii je aktuálně uloženo "
            f"{len(historie)} záznamů."
        )
