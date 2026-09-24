import streamlit as st
import pandas as pd
import requests

from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
from datetime import datetime
from pathlib import Path


# --------------------------------------------------
# Nastavení historie
# --------------------------------------------------

HISTORY_FILE = Path("history.csv")

HISTORY_COLUMNS = [
    "datum",
    "hledany_produkt",
    "produkt",
    "obchod",
    "cena",
    "cena_text",
    "platnost",
    "odkaz"
]


def vytvor_nebo_oprav_historii():
    """
    Vytvoří history.csv, pokud neexistuje nebo je prázdný.
    Pokud má soubor starší strukturu, doplní chybějící sloupce.
    """

    if not HISTORY_FILE.exists() or HISTORY_FILE.stat().st_size == 0:
        pd.DataFrame(columns=HISTORY_COLUMNS).to_csv(
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

    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        pd.DataFrame(columns=HISTORY_COLUMNS).to_csv(
            HISTORY_FILE,
            index=False,
            encoding="utf-8-sig"
        )


def uloz_do_historie(vysledky, hledany_produkt):
    """
    Přidá nalezené nabídky do history.csv.
    """

    if not vysledky:
        return 0

    cas_hledani = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    nove_zaznamy = []

    for vysledek in vysledky:
        nove_zaznamy.append(
            {
                "datum": cas_hledani,
                "hledany_produkt": hledany_produkt,
                "produkt": vysledek["Produkt"],
                "obchod": vysledek["Obchod"],
                "cena": vysledek["Cena (Kč)"],
                "cena_text": vysledek["Cena"],
                "platnost": vysledek["Platnost"],
                "odkaz": vysledek["Leták"]
            }
        )

    df_nove = pd.DataFrame(
        nove_zaznamy,
        columns=HISTORY_COLUMNS
    )

    try:
        historie = pd.read_csv(HISTORY_FILE)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        historie = pd.DataFrame(columns=HISTORY_COLUMNS)

    for sloupec in HISTORY_COLUMNS:
        if sloupec not in historie.columns:
            historie[sloupec] = ""

    historie = historie[HISTORY_COLUMNS]

    historie = pd.concat(
        [historie, df_nove],
        ignore_index=True
    )

    historie.to_csv(
        HISTORY_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    return len(df_nove)


def nacti_historii():
    """
    Bezpečně načte celý soubor historie.
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
        return pd.DataFrame(columns=HISTORY_COLUMNS)


# Vytvoření nebo oprava history.csv při spuštění aplikace
vytvor_nebo_oprav_historii()


# --------------------------------------------------
# Nastavení aplikace
# --------------------------------------------------

st.set_page_config(
    page_title="Hlídač slev",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 Hlídač slev")
st.caption(
    "Vyhledávání akčních nabídek v Lidlu a Kauflandu"
)


# --------------------------------------------------
# Vyhledávání
# --------------------------------------------------

produkt = st.text_input(
    "Hledaný produkt",
    value="Pampers"
)

if st.button("Najít akce", type="primary"):

    if not produkt.strip():
        st.warning("Zadej název produktu.")
        st.stop()

    hledany_produkt = produkt.strip()
    parametr_produktu = quote_plus(hledany_produkt)

    url = (
        f"https://www.kupi.cz/hledej?"
        f"f={parametr_produktu}"
    )

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
        st.error(
            f"Nepodařilo se načíst data: {chyba}"
        )
        st.stop()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # Každý blok představuje jednu obchodní nabídku
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

        # Ponecháme pouze Lidl a Kaufland
        if obchod.lower() not in ["lidl", "kaufland"\]:
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
            cena_cislo = float(cena_cislo_text)
        except ValueError:
            cena_cislo = None

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
            f"Na stránce bylo nalezeno "
            f"{len(bloky_akci)} nabídkových bloků, "
            "ale žádný odpovídající blok nebyl přiřazen "
            "Lidlu nebo Kauflandu."
        )

    else:
        df = pd.DataFrame(vysledky)

        df = df.sort_values(
            by="Cena (Kč)",
            na_position="last"
        ).reset_index(drop=True)

        pocet_ulozenych = uloz_do_historie(
            vysledky,
            hledany_produkt
        )

        st.success(
            f"Nalezeno nabídek: {len(df)}. "
            f"Do historie bylo uloženo záznamů: "
            f"{pocet_ulozenych}."
        )

        platne_ceny = df.dropna(
            subset=["Cena (Kč)"]
        )

        if not platne_ceny.empty:
            nejlevnejsi = platne_ceny.iloc[0]

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


# --------------------------------------------------
# Zobrazení historie
# --------------------------------------------------

st.divider()
st.subheader("Historie hledání")

historie = nacti_historii()

st.write(
    f"Řádků v historii: {len(historie)}"
)

if historie.empty:
    st.info(
        "Historie je zatím prázdná. "
        "Vyhledej produkt a nalezené nabídky se uloží."
    )

else:
    historie_zobrazeni = historie.copy()

    historie_zobrazeni["cena"] = pd.to_numeric(
        historie_zobrazeni["cena"],
        errors="coerce"
    )

    historie_zobrazeni = historie_zobrazeni.sort_values(
        by="datum",
        ascending=False
    )

    vyber_produktu = st.selectbox(
        "Produkt z historie",
        options=["Všechny"] + sorted(
            historie_zobrazeni[
                "hledany_produkt"
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
    )

    if vyber_produktu != "Všechny":
        historie_zobrazeni = historie_zobrazeni[
            historie_zobrazeni[
                "hledany_produkt"
            ] == vyber_produktu
        ]

    st.dataframe(
        historie_zobrazeni[
            [
                "datum",
                "hledany_produkt",
                "produkt",
                "obchod",
                "cena_text",
                "platnost,
                "odkaz"
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "datum": "Datum kontroly",
            "hledany_produkt": "Hledaný produkt",
            "produkt": "Nalezený produkt",
            "obchod": "Obchod",
            "cena_text": "Cena",
            "platnost": "Platnost",
            "odkaz": st.column_config.LinkColumn(
                "Leták",
                display_text="Otevřít"
            )
        }
    )

    st.download_button(
        label="Stáhnout historii jako CSV",
        data=historie.to_csv(
            index=False,
            encoding="utf-8-sig"
        ),
        file_name="history.csv",
        mime="text/csv"
    )
