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

HISTORY_FILE = Path("history.csv")

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
    """
    Vytvoří history.csv, pokud soubor neexistuje nebo je prázdný.
    Pokud soubor existuje, doplní případné chybějící sloupce.
    """

    if not HISTORY_FILE.exists() or HISTORY_FILE.stat().st_size == 0:
        prazdna_historie = pd.DataFrame(
            columns=HISTORY_COLUMNS
        )

        prazdna_historie.to_csv(
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
        prazdna_historie = pd.DataFrame(
            columns=HISTORY_COLUMNS
        )

        prazdna_historie.to_csv(
            HISTORY_FILE,
            index=False,
            encoding="utf-8-sig"
        )


def nacti_historii():
    """
    Načte history.csv.
    Pokud nastane problém, vrátí prázdnou tabulku.
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
    Uloží nalezené nabídky do history.csv.

    Stejná nabídka se uloží maximálně jednou za den.
    Kontroluje se produkt, obchod, cena a platnost.
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
# PŘÍPRAVA SOUBORU HISTORY.CSV
# ==================================================

vytvor_nebo_oprav_historii()


# ==================================================
# HLAVIČKA APLIKACE
# ==================================================

st.title("🛒 Hlídač slev")

st.caption(
    "Vyhledávání akčních nabídek v Lidlu a Kauflandu"
)


# ==================================================
# VSTUPNÍ ÚDAJE
# ==================================================

produkt = st.text_input(
    "Hledaný produkt",
    value="Kuřecí prsní"
)

cenovy_limit = st.sidebar.number_input(
    "Upozornit při ceně nižší nebo rovné",
    min_value=0.0,
    value=150.0,
    step=10.0,
    format="%.2f",
    help=(
        "Pokud bude nejnižší nalezená cena stejná "
        "nebo nižší než tento limit, aplikace zobrazí upozornění."
    )
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
        st.warning("Zadej název produktu.")
        st.stop()

    hledany_produkt = produkt.strip()
    parametr_produktu = quote_plus(hledany_produkt)

    url = (
        "https://www.kupi.cz/hledej?"
        f"f={parametr_produktu}"
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
            f"Nepodařilo se načíst data z Kupi.cz: {chyba}"
        )
        st.stop()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

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

        # Zobrazujeme pouze nabídky Lidlu a Kauflandu.
        if obchod.lower() not in [
            "lidl",
            "kaufland"
        ]:
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
                "href"
            )

            odkaz_na_letak = urljoin(
                "https://www.kupi.cz",
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

        df = df.sort_values(
            by="Cena (Kč)",
            na_position="last"
        ).reset_index(
            drop=True
        )

        pocet_ulozenych = uloz_do_historie(
            vysledky,
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

        # Odstranění řádků bez číselné ceny
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

            # ==========================================
            # HLÍDÁNÍ CENOVÉHO LIMITU
            # ==========================================

            if nejlevnejsi_cena <= cenovy_limit:
                rozdil = cenovy_limit - nejlevnejsi_cena

                st.success(
                    f"Produkt je pod nastaveným limitem. "
                    f"Nejnižší cena je "
                    f"{nejlevnejsi_cena:.2f} Kč, "
                    f"tedy o {rozdil:.2f} Kč méně "
                    f"než nastavený limit."
                )
            else:
                rozdil = nejlevnejsi_cena - cenovy_limit

                st.info(
                    f"Produkt zatím není pod nastaveným limitem. "
                    f"Nejnižší cena je "
                    f"{nejlevnejsi_cena:.2f} Kč, "
                    f"tedy o {rozdil:.2f} Kč více "
                    f"než nastavený limit."
                )

        else:
            st.warning(
                "Nabídky byly nalezeny, ale jejich ceny "
                "se nepodařilo převést na čísla."
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
                    display_text="Otevřít leták"                )
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
        "Historie je zatím prázdná. "
        "Po prvním úspěšném hledání se sem uloží nabídky."
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

    vybrany_produkt = st.selectbox(
        "Filtrovat historii podle produktu",
        options=["Všechny produkty"] + dostupne_produkty
    )

    historie_filtrovana = historie.copy()

    if vybrany_produkt != "Všechny produkty":
        historie_filtrovana = historie_filtrovana[
            historie_filtrovana[
                "hledany_produkt"
            ] == vybrany_produkt
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

    # ==================================================
    # GRAF HISTORIE
    # ==================================================

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

    # ==================================================
    # STAŽENÍ HISTORIE
    # ==================================================

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
        "Soubor existuje:",
        HISTORY_FILE.exists()
    )

    if HISTORY_FILE.exists():
        st.write(
            "Velikost souboru:",
            f"{HISTORY_FILE.stat().st_size} bajtů"
        )
