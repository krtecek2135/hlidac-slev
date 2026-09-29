import streamlit as st
import pandas as pd
import requests

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
    "cena",
    "cena_text",
    "platnost",
    "poznamka",
    "odkaz"
]


# ==================================================
# FUNKCE PRO HISTORII
# ==================================================

def vytvor_nebo_oprav_historii():
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
        cena = vysledek["Cena (Kč)"]
        duplicita = False

        if not historie.empty:
            datum_historie = (
                historie["datum"]
                .astype(str)
                .str[:10]
            )

            ceny_historie = pd.to_numeric(
                historie["cena"],
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
                    ceny_historie == cena
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
                    "cena": cena,
                    "cena_text": vysledek["Cena"],
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
# FUNKCE PRO WATCHLIST
# ==================================================

def vytvor_watchlist():
    if not WATCHLIST_FILE.exists() or WATCHLIST_FILE.stat().st_size == 0:
        pd.DataFrame(
            columns=["produkt", "limit"]
        ).to_csv(
            WATCHLIST_FILE,
            index=False,
            encoding="utf-8-sig"
        )


def nacti_watchlist():
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
# PŘÍPRAVA SOUBORŮ
# ==================================================

vytvor_nebo_oprav_historii()
vytvor_watchlist()


# ==================================================
# HLAVIČKA APLIKACE
# ==================================================

st.title("🛒 Hlídač slev")

st.caption(
    "Vyhledávání akčních nabídek v Lidlu a Kauflandu"
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
        f"Nastavený limit: {vybrany_limit:.2f} Kč"
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
    st.session_state["produkt"] = "Kuřecí prsní"

if "limit" not in st.session_state:
    st.session_state["limit"] = 150.0

produkt = st.text_input(
    "Hledaný produkt",
    key="produkt"
)

limit = st.sidebar.number_input(
    "Upozornit při ceně nižší nebo rovné",
    min_value=0.0,
    step=10.0,
    key="limit"
)

hledat = st.button(
    "Najít akce",
    type="primary"
)


# ==================================================
# VYHLEDÁVÁNÍ NABÍDEK
# ==================================================

if hledat:
    if not produkt.strip():
        st.warning(
            "Zadej název produktu."
        )
        st.stop()

    hledany_produkt = produkt.strip()
    parametr_produktu = quote_plus(
        hledany_produkt
    )

    url = (
        BASE_URL
        + "/hledej?f="
        + parametr_produktu
    )

    try:
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
            timeout=15
        )

        response.raise_for_status()

    except requests.RequestException as chyba:
        st.error(
            f"Nepodařilo se načíst data: {chyba}"
        )
        st.stop()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # ==================================================
    # DIAGNOSTIKA AVG_PRICE
    # ==================================================

    avg_price_bloky = soup.select(
        ".avg_price"
    )

    with st.expander(
        "🔍 Diagnostika běžné ceny .avg_price"
    ):
        st.write(
            f"Nalezeno bloků .avg_price: "
            f"{len(avg_price_bloky)}"
        )

        if not avg_price_bloky:
            st.info(
                "Na stránce nebyl nalezen žádný blok "
                "s třídou .avg_price."
            )

        for poradi, avg_blok in enumerate(
            avg_price_bloky[:20],
            start=1
        ):
            text_bezne_ceny = avg_blok.get_text(
                " ",
                strip=True
            )

            produktovy_kontejner = avg_blok.find_parent(
                class_="group_discounts"
            )

            nazev_avg_produktu = "Produkt nezjištěn"

            if produktovy_kontejner is not None:
                nazev_element = produktovy_kontejner.select_one(
                    ".product_name strong"
                )

                if nazev_element is not None:
                    nazev_avg_produktu = nazev_element.get_text(
                        " ",
                        strip=True
                    )

            st.markdown(
                f"**Blok {poradi}: {nazev_avg_produktu}**"
            )

            st.code(
                text_bezne_ceny
            )

            with st.expander(
                f"HTML bloku avg_price {poradi}"
            ):
                st.code(
                    avg_blok.prettify(),
                    language="html"
                )

    # ==================================================
    # NAČTENÍ AKČNÍCH NABÍDEK
    # ==================================================

    bloky_akci = soup.select(
        ".discount_row"
    )

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

        cena_text = cena_element.get_text(
            " ",
            strip=True
        )

        cena_cislo_text = (
            cena_text
            .replace("Kč", "")
            .replace("\xa0", "")
            .replace(" ", "")
            .replace(",", ".")
            .strip()
        )

        try:
            cena_cislo = float(
                cena_cislo_text
            )
        except ValueError:
            cena_cislo = None

        if produkt_element is not None:
            nazev_produktu = produkt_element.get(
                "data-product",
                hledany_produkt
            )
        else:
            nazev_produktu = hledany_produkt

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

    # ==================================================
    # VÝSLEDKY VYHLEDÁVÁNÍ
    # ==================================================

    if not vysledky:
        st.warning(
            "Pro zadaný produkt nebyla nalezena nabídka "
            "v Lidlu ani Kauflandu."
        )

        st.info(
            f"Na stránce bylo nalezeno "
            f"{len(bloky_akci)} nabídkových bloků."
        )

    else:
        df = pd.DataFrame(
            vysledky
        )

        df["Cena (Kč)"] = pd.to_numeric(
            df["Cena (Kč)"],
            errors="coerce"
        )

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
        ).reset_index(
            drop=True
        )

        pocet_ulozenych = uloz_do_historie(
            df.to_dict("records"),
            hledany_produkt
        )

        st.success(
            f"Nalezeno nabídek: {len(df)}"
        )

        if pocet_ulozenych > 0:
            st.write(
                f"Do historie bylo přidáno "
                f"{pocet_ulozenych} nových záznamů."
            )
        else:
            st.write(
                "Dnešní nabídky už byly v historii uložené."
            )

        platne_ceny = df.dropna(
            subset=["Cena (Kč)"]
        )

        if not platne_ceny.empty:
            nejlevnejsi = platne_ceny.iloc[0]

            nejlevnejsi_cena = float(
                nejlevnejsi["Cena (Kč)"]
            )

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

            if nejlevnejsi_cena <= limit:
                rozdil = limit - nejlevnejsi_cena

                st.success(
                    f"Produkt je pod nastaveným limitem. "
                    f"Nejnižší cena je "
                    f"{nejlevnejsi_cena:.2f} Kč. "
                    f"Rozdíl proti limitu je "
                    f"{rozdil:.2f} Kč."
                )
            else:
                rozdil = nejlevnejsi_cena - limit

                st.info(
                    f"Produkt zatím není pod limitem. "
                    f"Nejnižší cena je "
                    f"{nejlevnejsi_cena:.2f} Kč. "
                    f"Do limitu chybí "
                    f"{rozdil:.2f} Kč."
                )

        st.subheader(
            "Nalezené nabídky"
        )

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


# ==================================================
# HISTORIE
# ==================================================

st.divider()
st.subheader("Historie cen")

historie = nacti_historii()

st.caption(
    f"Celkový počet záznamů: {len(historie)}"
)

if historie.empty:
    st.info(
        "Historie je zatím prázdná."
    )

else:
    historie["cena"] = pd.to_numeric(
        historie["cena"],
        errors="coerce"
    )

    historie["datum_parsed"] = pd.to_datetime(
        historie["datum"],
        errors="coerce"
    )

    historie = historie.sort_values(
        by="datum_parsed",
        ascending=False
    )

    dostupne_produkty = sorted(
        historie["hledany_produkt"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    vybrany_produkt_historie = st.selectbox(
        "Filtrovat historii podle produktu",
        options=[
            "Všechny produkty"
        ] + dostupne_produkty
    )

    historie_filtrovana = historie.copy()

    if vybrany_produkt_historie != "Všechny produkty":
        historie_filtrovana = historie_filtrovana[
            historie_filtrovana["hledany_produkt"]
            == vybrany_produkt_historie
        ]

    st.dataframe(
        historie_filtrovana[
            [
                "datum",
                "hledany_produkt",
                "produkt",
                "obchod",
                "cena_text",
                "platnost",
                "poznamka",
                "odkaz"
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "datum": "Datum kontroly",
            "hledany_produkt": "Hledaný výraz",
            "produkt": "Produkt",
            "obchod": "Obchod",
            "cena_text": "Cena",
            "platnost": "Platnost",
            "poznamka": "Poznámka",
            "odkaz": st.column_config.LinkColumn(
                "Leták",
                display_text="Otevřít"
            )
        }
    )

    graf_data = historie_filtrovana.dropna(
        subset=[
            "datum_parsed",
            "cena"
        ]
    ).copy()

    if not graf_data.empty:
        st.subheader(
            "Vývoj nalezených cen"
        )

        graf_data = graf_data.sort_values(
            by="datum_parsed"
        )

        st.line_chart(
            graf_data,
            x="datum_parsed",
            y="cena",
            color="obchod"
        )

    export_historie = historie.drop(
        columns=["datum_parsed"],
        errors="ignore"
    )

    csv_data = export_historie.to_csv(
        index=False,
        encoding="utf-8-sig"
    )

    st.download_button(
        label="Stáhnout historii jako CSV",
        data=csv_data,
        file_name="history.csv",
        mime="text/csv"
    )


# ==================================================
# TECHNICKÉ INFORMACE
# ==================================================

with st.expander(
    "Technické informace"
):
    st.write(
        "Umístění souboru historie:"
    )

    st.code(
        str(HISTORY_FILE.resolve())
    )

    st.write(
        "Soubor historie existuje:",
        HISTORY_FILE.exists()
    )

    st.write(
        "Počet nalezených avg_price bloků "
        "se zobrazí po spuštění hledání."
    )
