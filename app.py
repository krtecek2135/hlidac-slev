import re

if st.button("Analyzovat HTML"):

    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    html = response.text

    st.write("Počet výskytů 'Kč':", html.count("Kč"))

    matches = re.findall(r".{0,50}Kč.{0,50}", html)

    for m in matches[:20\]:
        st.text(m)
