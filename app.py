import streamlit as st
import pandas as pd
import requests
import re

from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
from datetime import datetime
from pathlib import Path


# ==================================================
# ZÁKLADNÍ NASTAVENÍ
# ==================================================

st.set_page_config(
    page_title="Hlídač slev",
    page_icon="🛒",
    layout="wide"
)

BASE_URL = "https://www.kupi.cz"

HISTORY_FILE = Path("history.csv")
WATCHLIST_FILE = Path("watchlist.csv")

POVOLENE_OBCHODY = [
    "lidl",
    "kaufland"
]

HISTORY_COLUMNS = [
    "datum",
    "hledany_produkt",
    "produkt",
    "obchod",
    "akcni_cena",
    "akcni_cena_text",
    "bezna_cena",
    "uspora_kc",
    "uspora_procent",
    "platnost",
    "poznamka",
    "odkaz"
]


# ==================================================
# POMOCNÉ FUNKCE
# ==================================================

def preved_cenu_na_cislo(cena_text):
    """
    Převede například '55,22 Kč' na číslo 55.22.
    """

    if not cena_text:
        return None

    nalezena_cena = re.search(
        r"(\d[\d\s\xa0]*[,.]\d{1,2}|\d[\d\s\xa0]*)",
        str(cena_text)
    )

    if nalezena_cena is None:
        return None

    vycistena_cena = (
        nalezena_cena.group(1)
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )

    try:
        return float(vycistena_cena)
    except ValueError:
        return None


def formatuj_cenu(cena):
    """
    Převede číslo na český formát ceny.
    """

    if cena is None or pd.isna(cena):
        return "Neuvedeno"

    return f"{cena:.2f} Kč".replace(".", ",")


# ==================================================
# HISTORIE
# ==================================================

def vytvor_nebo_oprav_historii():
    """
    Vytvoří history.csv nebo doplní chybějící sloupce.
    """

    if not HISTORY_FILE.exists() or HISTORY_FILE.stat().st_size == 0:
        pd.DataFrame(
            columns=HISTORY_COLUMNS
        ).to_csv(
            HISTORY_FILE,
            index=False,
            encoding="utf-8-sig"
        )
        return

    try:
        historie = pd.read_csv(HISTORY_FILE)

        for sloupec in HISTORY_COLUMNS:
            if sloupec not in historie.columns:
                historie[sloupec] = ""

        historie = historie[HISTORY_COLUMNS]

        historie.to_csv(
            HISTORY_FILE,
            index=False,
            encoding="utf-8-sig"
        )

    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError
    ):
        pd.DataFrame(
            columns=HISTORY_COLUMNS
        ).to_csv(
            HISTORY_FILE,
            index=False,
            encoding="utf-8-sig"
        )


def nacti_historii():
    """
    Bezpečně načte historii.
    """

    try:
        historie = pd.read_csv(HISTORY_FILE)

        for sloupec in HISTORY_COLUMNS:
            if sloupec not in historie.columns:
                historie[sloupec] = ""

        return historie[HISTORY_COLUMNS]

    except (
        FileNotFoundError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError
    ):
        return pd.DataFrame(
            columns=HISTORY_COLUMNS
        )


def uloz_do_historie(vysledky, hledany_produkt):
    """
    Uloží nabídky maximálně jednou za den.
    """

    if not vysledky:
        return 0

    historie = nacti_historii()

    datum_a_cas = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    dnes = datetime.now().strftime(
        "%Y-%m-%d"
    )

    nove_zaznamy = []

    for vysledek in vysledky:
        duplicita = False

        if not historie.empty:
            datum_historie = (
                historie["datum"]
                .astype(str)
                .str[:10]
            )

            akcni_ceny_historie = pd.to_numeric(
                historie["akcni_cena"],
                errors="coerce"
            )

            duplicita = (
                (datum_historie == dnes)
                & (
                    historie["hledany_produkt"]
                    .astype(str)
                    .str.lower()
                    == hledany_produkt.lower()
                )
                & (
                    historie["produkt"]
                    .astype(str)
                    == str(vysledek["Produkt"])
                )
                & (
                    historie["obchod"]
                    .astype(str)
                    == str(vysledek["Obchod"])
                )
                & (
                    akcni_ceny_historie
                    == vysledek["Akční cena (Kč)"]
                )
                & (
                    historie["platnost"]
                    .astype(str)
                    == str(vysledek["Platnost"])
                )
            ).any()

        if not duplicita:
            nove_zaznamy.append(
                {
                    "datum": datum_a_cas,
                    "hledany_produkt": hledany_produkt,
                    "produkt": vysledek["Produkt"],
                    "obchod": vysledek["Obchod"],
                    "akcni_cena": vysledek["Akční cena (Kč)"],
                    "akcni_cena_text": vysledek["Akční cena"],
                    "bezna_cena": vysledek["Běžná cena (Kč)"],
                    "uspora_kc": vysledek["Úspora (Kč)"],
                    "uspora_procent": vysledek["Úspora (%)"],
                    "platnost": vysledek["Platnost"],
                    "poznamka": vysledek["Poznámka"],
                    "odkaz": vysledek["Leták"]
                }
            )

    if not nove_zaznamy:
        return 0

    nove_df = pd.DataFrame(
        nove_zaznamy,
        columns=HISTORY_COLUMNS
    )

    historie = pd.concat(
        [historie, nove_df],
        ignore_index=True
    )

    historie.to_csv(
        HISTORY_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    return len(nove_df)


# ==================================================
# WATCHLIST
# ==================================================

def vytvor_watchlist():
    """
    Vytvoří watchlist.csv, pokud neexistuje.
    """

    if not WATCHLIST_FILE.exists() or WATCHLIST_FILE.stat().st_size == 0:
        pd.DataFrame(
            columns=["produkt", "limit"]
        ).to_csv(
            WATCHLIST_FILE,
            index=False,
            encoding="utf-8-sig"
        )


def nacti_watchlist():
    """
    Načte seznam sledovaných produktů.
    """

    try:
        watchlist = pd.read_csv(WATCHLIST_FILE)

        if "produkt" not in watchlist.columns:
            watchlist["produkt"] = ""

        if "limit" not in watchlist.columns:
            watchlist["limit"] = 0.0

        watchlist["limit"] = pd.to_numeric(
            watchlist["limit"],
            errors="coerce"
        ).fillna(0.0)

        return watchlist[
            ["produkt", "limit"]
        ]

    except (
        FileNotFoundError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError
    ):
        return pd.DataFrame(
            columns=["produkt", "limit"]
        )


# ==================================================
# ZÍSKÁNÍ DAT Z KUPI
# ==================================================

def ziskej_beznou_cenu(produktovy_kontejner):
    """
    Získá běžnou cenu ze stejného produktového kontejneru.
    """

    avg_price_element = produktovy_kontejner.select_one(
        ".avg_price"
    )

    if avg_price_element is None:
        return None, ""

    text_bezne_ceny = avg_price_element.get_text(
        " ",
        strip=True
    )

    bezna_cena = preved_cenu_na_cislo(
        text_bezne_ceny
    )

    if bezna_cena is not None and bezna_cena <= 0:
        bezna_cena = None

    return bezna_cena, text_bezne_ceny


def stahni_nabidky(hledany_produkt):
    """
    Načte produkty, běžné ceny a nabídky Lidlu a Kauflandu.
    """

    parametr_produktu = quote_plus(
        hledany_produkt.strip()
    )

    url = (
        BASE_URL
        + "/hledej?f="
        + parametr_produktu
    )

    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
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

    produktove_kontejnery = soup.select(
        ".group_discounts"
    )

    vysledky = []
    diagnostika = []

    for produktovy_kontejner in produktove_kontejnery:
        nazev_element = produktovy_kontejner.select_one(
            ".product_name strong"
        )

        if nazev_element is not None:
            nazev_produktu_kontejneru = nazev_element.get_text(
                " ",
                strip=True
            )
        else:
            nazev_produktu_kontejneru = hledany_produkt

        bezna_cena, bezna_cena_text = ziskej_beznou_cenu(
            produktovy_kontejner
        )

        diagnostika.append(
            {
                "Produkt": nazev_produktu_kontejneru,
                "Běžná cena": bezna_cena,
                "Původní text": bezna_cena_text
            }
        )

        bloky_akci = produktovy_kontejner.select(
            ".discount_row"
        )

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

            if obchod_element is None:
                continue

            if cena_element is None:
                continue

            obchod = obchod_element.get_text(
                " ",
                strip=True
            )

            if obchod.lower() not in POVOLENE_OBCHODY:
                continue

            akcni_cena_text = cena_element.get_text(
                " ",
                strip=True
            )

            akcni_cena = preved_cenu_na_cislo(
                akcni_cena_text
            )

            if produkt_element is not None:
                nazev_produktu = produkt_element.get(
                    "data-product",
                    nazev_produktu_kontejneru
                )
            else:
                nazev_produktu = nazev_produktu_kontejneru

            if platnost_element is not None:
                platnost = platnost_element.get_text(
                    " ",
                    strip=True
                )
            else:
                platnost = "Neuvedeno"

            if poznamka_element is not None:
                poznamka = poznamka_element.get_text(
                    " ",
                    strip=True
                )
            else:
                poznamka = ""

            if letak_element is not None:
                relativni_odkaz = letak_element.get(
                    "href",
                    ""
                )

                odkaz_na_letak = urljoin(
                    BASE_URL,
                    relativni_odkaz
                )
            else:
                odkaz_na_letak = ""

            uspora_kc = None
            uspora_procent = None

            if (
                akcni_cena is not None
                and bezna_cena is not None
                and bezna_cena > 0
            ):
                uspora_kc = round(
                    bezna_cena - akcni_cena,
                    2
                )

                uspora_procent = round(
                    uspora_kc / bezna_cena * 100,
                    1
                )

                if uspora_kc < 0:
                    uspora_kc = None
                    uspora_procent = None

            vysledky.append(
                {
                    "Produkt": nazev_produktu,
                    "Obchod": obchod,
                    "Akční cena (Kč)": akcni_cena,
                    "Akční cena": akcni_cena_text,
                    "Běžná cena (Kč)": bezna_cena,
                    "Běžná cena": formatuj_cenu(
                        bezna_cena
                    ),
                    "Úspora (Kč)": uspora_kc,
                    "Úspora": formatuj_cenu(
                        uspora_kc
                    ),
                    "Úspora (%)": uspora_procent,
                    "Platnost": platnost,
                    "Poznámka": poznamka,
                    "Leták": odkaz_na_letak
                }
            )

    return vysledky, diagnostika, len(produktove_kontejnery)


# ==================================================
# PŘÍPRAVA SOUBORŮ
# ==================================================

vytvor_nebo_oprav_historii()
vytvor_watchlist()


# ==================================================
# HLAVIČKA
# ==================================================

st.title("🛒 Hlídač slev")

st.caption(
    "Porovnání akčních a běžných cen v Lidlu a Kauflandu"
)


# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.header("📌 Sledované produkty")

watchlist = nacti_watchlist()

if not watchlist.empty:
    vybrany_produkt = st.sidebar.selectbox(
        "Vyber sledovaný produkt",
        watchlist["produkt"].tolist()
    )

    vybrany_radek = watchlist[
        watchlist["produkt"] == vybrany_produkt
    ].iloc[0]

    vybrany_limit = float(
        vybrany_radek["limit"]
    )

    if st.sidebar.button("Použít produkt"):
        st.session_state["produkt"] = vybrany_produkt
        st.session_state["limit"] = vybrany_limit
        st.rerun()

    st.sidebar.caption(
        f"Nastavený limit: {formatuj_cenu(vybrany_limit)}"
    )

    st.sidebar.dataframe(
        watchlist,
        hide_index=True,
        use_container_width=True,
        column_config={
            "produkt": "Produkt",
            "limit": st.column_config.NumberColumn(
                "Limit",
                format="%.2f Kč"
            )
        }
    )

else:
    st.sidebar.info(
        "Seznam sledovaných produktů je prázdný."
    )

st.sidebar.divider()
st.sidebar.subheader("Přidat sledovaný produkt")

novy_produkt = st.sidebar.text_input(
    "Nový produkt",
    key="novy_produkt"
)

novy_limit = st.sidebar.number_input(
    "Cenový limit nového produktu",
    min_value=0.0,
    value=100.0,
    step=10.0,
    key="novy_limit"
)

if st.sidebar.button("Přidat do sledovaných"):
    if not novy_produkt.strip():
        st.sidebar.warning(
            "Zadej název produktu."
        )
    else:
        novy_radek = pd.DataFrame(
            [
                {
                    "produkt": novy_produkt.strip(),
                    "limit": novy_limit
                }
            ]
        )

        watchlist = pd.concat(
            [watchlist, novy_radek],
            ignore_index=True
        )

        watchlist = watchlist.drop_duplicates(
            subset=["produkt"],
            keep="last"
        )

        watchlist.to_csv(
            WATCHLIST_FILE,
            index=False,
            encoding="utf-8-sig"
        )

        st.sidebar.success(
            "Produkt byl přidán."
        )

        st.rerun()


# ==================================================
# VSTUPNÍ ÚDAJE
# ==================================================

if "produkt" not in st.session_state:
    st.session_state["produkt"] = "Máslo"

if "limit" not in st.session_state:
    st.session_state["limit"] = 50.0

produkt = st.text_input(
    "Hledaný produkt",
    key="produkt"
)

limit = st.sidebar.number_input(
    "Upozornit při akční ceně nižší nebo rovné",
    min_value=0.0,
    step=5.0,
    key="limit"
)

hledat = st.button(
    "Najít akce",
    type="primary"
)


# ==================================================
# VYHLEDÁVÁNÍ
# ==================================================

if hledat:
    if not produkt.strip():
        st.warning(
            "Zadej název produktu."
        )
        st.stop()

    try:
        with st.spinner(
            "Načítám akční a běžné ceny..."
        ):
            vysledky, diagnostika, pocet_produktu = stahni_nabidky(
                produkt.strip()
            )

    except requests.Timeout:
        st.error(
            "Načítání trvalo příliš dlouho."
        )
        st.stop()

    except requests.RequestException as chyba:
        st.error(
            f"Nepodařilo se načíst data: {chyba}"
        )
        st.stop()

    if not vysledky:
        st.warning(
            "Pro zadaný produkt nebyla nalezena nabídka "
            "v Lidlu ani Kauflandu."
        )

        st.info(
            f"Na stránce bylo nalezeno "
            f"{pocet_produktu} produktových bloků."
        )

    else:
        df = pd.DataFrame(
            vysledky
        )

        ciselne_sloupce = [
            "Akční cena (Kč)",
            "Běžná cena (Kč)",
            "Úspora (Kč)",
            "Úspora (%)"
        ]

        for sloupec in ciselne_sloupce:
            df[sloupec] = pd.to_numeric(
                df[sloupec],
                errors="coerce"
            )

        df = df.drop_duplicates(
            subset=[
                "Produkt",
                "Obchod",
                "Akční cena (Kč)",
                "Platnost"
            ]
        )

        df = df.sort_values(
            by="Akční cena (Kč)",
            na_position="last"
        ).reset_index(
            drop=True
        )

        pocet_ulozenych = uloz_do_historie(
            df.to_dict("records"),
            produkt.strip()
        )

        st.success(
            f"Nalezeno nabídek: {len(df)}"
        )

        if pocet_ulozenych > 0:
            st.caption(
                f"Do historie bylo přidáno "
                f"{pocet_ulozenych} nových záznamů."
            )
        else:
            st.caption(
                "Dnešní nabídky již byly uložené."
            )

        platne_ceny = df.dropna(
            subset=["Akční cena (Kč)"]
        )

        if not platne_ceny.empty:
            nejlevnejsi = platne_ceny.iloc[0]

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Nejnižší akční cena",
                    nejlevnejsi["Akční cena"]
                )

            with col2:
                st.metric(
                    "Běžná cena",
                    nejlevnejsi["Běžná cena"]
                )

            with col3:
                if pd.notna(
                    nejlevnejsi["Úspora (%)"]
                ):
                    st.metric(
                        "Úspora",
                        f"{nejlevnejsi['Úspora (%)']:.1f} %"
                    )
                else:
                    st.metric(
                        "Úspora",
                        "Neuvedeno"
                    )

            with col4:
                st.metric(
                    "Nejlevnější obchod",
                    nejlevnejsi["Obchod"]
                )

            nejlevnejsi_cena = float(
                nejlevnejsi["Akční cena (Kč)"]
            )

            if nejlevnejsi_cena <= limit:
                st.success(
                    f"Akční cena {formatuj_cenu}
