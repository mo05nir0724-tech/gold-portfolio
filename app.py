import csv
import os
import re
import requests
import streamlit as st

AKTIV_DATEI = "sammlung.csv"
VERKAUFT_DATEI = "verkauft.csv"

st.set_page_config(
    page_title="Edelmetall Portfolio & Verkauf", page_icon="🪙", layout="wide"
)


class PortfolioItem:

  def __init__(
      self, name, typ, gewicht_gramm, datum, kaufpreis, manueller_wert=0.0
  ):
    self.name = name
    self.typ = typ.upper()
    self.gewicht_gramm = float(gewicht_gramm)
    self.datum = datum
    self.kaufpreis = float(kaufpreis)
    self.manueller_wert = float(manueller_wert)

  def get_aktueller_wert(self, gold_preis, silber_preis):
    if self.typ == "GOLD":
      return self.gewicht_gramm * gold_preis
    elif self.typ == "SILBER":
      return self.gewicht_gramm * silber_preis
    return self.manueller_wert


class VerkaufsItem:

  def __init__(
      self, name, typ, gewicht_gramm, kaufdatum, kaufpreis, verkaufspreis, verkauf_datum
  ):
    self.name = name
    self.typ = typ.upper()
    self.gewicht_gramm = float(gewicht_gramm)
    self.kaufdatum = kaufdatum
    self.kaufpreis = float(kaufpreis)
    self.verkaufspreis = float(verkaufspreis)
    self.verkauf_datum = verkauf_datum

  def get_realisierter_gewinn(self):
    return self.verkaufspreis - self.kaufpreis

  def get_rendite(self):
    if self.kaufpreis <= 0:
      return 0.0
    return (self.get_realisierter_gewinn() / self.kaufpreis) * 100


@st.cache_data(ttl=60)
def hole_live_kurse():
  gold = 120.55
  silber = 1.79
  headers = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
  }
  try:
    r_g = requests.get("https://www.goldpreis.de/", headers=headers, timeout=4)
    m_g = re.search(
        r"1\s*Gramm[\s\S]*?(\d{1,3}(?:\.\d{3})*,\d{2})\s*EUR",
        r_g.text,
        re.IGNORECASE,
    )
    if m_g:
      gold = float(m_g.group(1).replace(".", "").replace(",", "."))

    r_s = requests.get(
        "https://www.goldpreis.de/silberpreis/", headers=headers, timeout=4
    )
    m_s = re.search(
        r"1\s*Gramm[\s\S]*?(\d{1,3}(?:\.\d{3})*,\d{2})\s*EUR",
        r_s.text,
        re.IGNORECASE,
    )
    if m_s:
      silber = float(m_s.group(1).replace(".", "").replace(",", "."))
  except Exception:
    pass
  return gold, silber


def lade_daten(datei, ist_verkauf=False):
  items = []
  if not os.path.exists(datei):
    return items
  try:
    with open(datei, "r", encoding="utf-8") as f:
      reader = csv.reader(f, delimiter=";")
      for row in reader:
        if ist_verkauf and len(row) >= 7:
          items.append(
              VerkaufsItem(
                  row[0], row[1], row[2], row[3], row[4], row[5], row[6]
              )
          )
        elif not ist_verkauf and len(row) >= 6:
          items.append(
              PortfolioItem(row[0], row[1], row[2], row[3], row[4], row[5])
          )
  except Exception:
    pass
  return items


def speichere_daten(datei, items, ist_verkauf=False):
  try:
    with open(datei, "w", encoding="utf-8", newline="") as f:
      writer = csv.writer(f, delimiter=";")
      for item in items:
        if ist_verkauf:
          writer.writerow([
              item.name,
              item.typ,
              item.gewicht_gramm,
              item.kaufdatum,
              item.kaufpreis,
              item.verkaufspreis,
              item.verkauf_datum,
          ])
        else:
          writer.writerow([
              item.name,
              item.typ,
              item.gewicht_gramm,
              item.datum,
              item.kaufpreis,
              item.manueller_wert,
          ])
  except Exception:
    pass


def main():
  st.title("🪙 Edelmetall Portfolio & Realisierte Gewinne")

  gold_g, silber_g = hole_live_kurse()
  aktive_items = lade_daten(AKTIV_DATEI, ist_verkauf=False)
  verkaufte_items = lade_daten(VERKAUFT_DATEI, ist_verkauf=True)

  col1, col2 = st.columns(2)
  col1.metric("Live-Goldpreis", f"{gold_g:,.2f} € / g".replace(".", ","))
  col2.metric("Live-Silberpreis", f"{silber_g:,.2f} € / g".replace(".", ","))

  st.divider()

  tab_aktiv, tab_verkauft = st.tabs(
      ["📦 Aktives Portfolio", "💰 Verkaufte Artikel (Realisiert)"]
  )

  with tab_aktiv:
    gesamt_kauf = sum(i.kaufpreis for i in aktive_items)
    gesamt_wert = sum(
        i.get_aktueller_wert(gold_g, silber_g) for i in aktive_items
    )
    gesamt_bilanz = gesamt_wert - gesamt_kauf

    c1, c2, c3 = st.columns(3)
    c1.metric("Kaufwert", f"{gesamt_kauf:,.2f} €".replace(".", ","))
    c2.metric("Aktueller Wert", f"{gesamt_wert:,.2f} €".replace(".", ","))
    c3.metric(
        "Gesamtbilanz",
        f"{gesamt_bilanz:,.2f} €".replace(".", ","),
        delta=(
            f"{(gesamt_bilanz/gesamt_kauf*100) if gesamt_kauf > 0 else 0:.2f} %"
        ),
    )

    st.subheader("Deine aktiven Stücke")
    if aktive_items:
      tab_daten = []
      for idx, item in enumerate(aktive_items):
        w = item.get_aktueller_wert(gold_g, silber_g)
        gv = w - item.kaufpreis
        rendite = (gv / item.kaufpreis * 100) if item.kaufpreis > 0 else 0
        tab_daten.append({
            "ID": idx,
            "Datum": item.datum,
            "Name": item.name,
            "Typ": item.typ,
            "Gewicht (g)": f"{item.gewicht_gramm:.2f}".replace(".", ","),
            "Kaufpreis": f"{item.kaufpreis:,.2f} €".replace(".", ","),
            "Akt. Wert": f"{w:,.2f} €".replace(".", ","),
            "Gewinn/Verlust": f"{gv:+,.2f} €".replace(".", ","),
            "Rendite": f"{rendite:+.2f} %".replace(".", ","),
        })
      st.dataframe(tab_daten, use_container_width=True, hide_index=True)

      st.markdown("### Eintrag bearbeiten / verkaufen")
      col_sel, col_p, col_d, col_btn = st.columns([2, 1, 1, 1])

      k_idx = col_sel.selectbox(
          "Eintrag auswählen:",
          options=range(len(aktive_items)),
          format_func=lambda x: f"{aktive_items[x].name} ({aktive_items[x].gewicht_gramm}g {aktive_items[x].typ})",
          key="select_aktiv",
      )
      verkaufspreis_input = col_p.number_input(
          "Verkaufspreis (€)", min_value=0.0, value=300.0, key="v_preis"
      )
      verkauf_datum_input = col_d.text_input(
          "Verkaufsdatum", "12.09.2026", key="v_datum"
      )

      if col_btn.button("💵 Als verkauft buchen", type="primary"):
        item_zu_verkaufen = aktive_items[k_idx]
        verkauftes_item = VerkaufsItem(
            name=item_zu_verkaufen.name,
            typ=item_zu_verkaufen.typ,
            gewicht_gramm=item_zu_verkaufen.gewicht_gramm,
            kaufdatum=item_zu_verkaufen.datum,
            kaufpreis=item_zu_verkaufen.kaufpreis,
            verkaufspreis=verkaufspreis_input,
            verkauf_datum=verkauf_datum_input,
        )
        verkaufte_items.append(verkauftes_item)
        del aktive_items[k_idx]

        speichere_daten(AKTIV_DATEI, aktive_items, ist_verkauf=False)
        speichere_daten(VERKAUFT_DATEI, verkaufte_items, ist_verkauf=True)
        st.success("Erfolgreich als verkauft verbucht!")
        st.rerun()

      if st.button("🗑️ Komplett löschen (ohne Verkauf)"):
        del aktive_items[k_idx]
        speichere_daten(AKTIV_DATEI, aktive_items, ist_verkauf=False)
        st.success("Eintrag gelöscht!")
        st.rerun()

    else:
      st.info("Keine aktiven Einträge vorhanden.")

  with tab_verkauft:
    realisierter_gesamt_gewinn = sum(
        i.get_realisierter_gewinn() for i in verkaufte_items
    )
    gesamter_erloes = sum(i.verkaufspreis for i in verkaufte_items)

    vc1, vc2 = st.columns(2)
    vc1.metric(
        "Gesamterlöse (Verkäufe)",
        f"{gesamter_erloes:,.2f} €".replace(".", ","),
    )
    vc2.metric(
        "Realisierter Gesamtgewinn",
        f"{realisierter_gesamt_gewinn:+,.2f} €".replace(".", ","),
        delta=f"{realisierter_gesamt_gewinn:,.2f} €",
    )

    st.subheader("Historie der Verkäufe")
    if verkaufte_items:
      v_tab_daten = []
      for idx, item in enumerate(verkaufte_items):
        rg = item.get_realisierter_gewinn()
        r = item.get_rendite()
        v_tab_daten.append({
            "ID": idx,
            "Kaufdatum": item.kaufdatum,
            "Verkaufsdatum": item.verkauf_datum,
            "Name": item.name,
            "Typ": item.typ,
            "Gewicht (g)": f"{item.gewicht_gramm:.2f}".replace(".", ","),
            "Kaufpreis": f"{item.kaufpreis:,.2f} €".replace(".", ","),
            "Verkaufspreis": f"{item.verkaufspreis:,.2f} €".replace(".", ","),
            "Realisierter Gewinn": f"{rg:+,.2f} €".replace(".", ","),
            "Rendite": f"{r:+.2f} %".replace(".", ","),
        })
      st.dataframe(v_tab_daten, use_container_width=True, hide_index=True)

      v_loesch_idx = st.selectbox(
          "Verkaufshistorie-Eintrag löschen:",
          options=range(len(verkaufte_items)),
          format_func=lambda x: f"{verkaufte_items[x].name} - Verkauf: {verkaufte_items[x].verkaufspreis}€",
          key="select_verkauft_del",
      )
      if st.button("🗑️ Aus Historie löschen"):
        del verkaufte_items[v_loesch_idx]
        speichere_daten(VERKAUFT_DATEI, verkaufte_items, ist_verkauf=True)
        st.success("Eintrag aus Historie entfernt!")
        st.rerun()
    else:
      st.info("Bisher wurden keine Artikel verkauft.")

  st.sidebar.header("➕ Neuer Eintrag")
  with st.sidebar.form("neuer_eintrag"):
    s_name = st.text_input("Name", "Maple Leaf")
    s_typ = st.selectbox("Typ", ["GOLD", "SILBER", "MANUELL"])
    s_gew = st.number_input(
        "Gewicht (g)", min_value=0.0, value=31.1, step=0.1
    )
    s_dat = st.text_input("Kaufdatum", "12.09.2026")
    s_kauf = st.number_input("Kaufpreis (€)", min_value=0.0, value=200.0)
    s_manuell = 0.0
    if s_typ == "MANUELL":
      s_manuell = st.number_input("Manueller Wert (€)", min_value=0.0)

    if st.form_submit_button("Speichern"):
      aktive_items.append(
          PortfolioItem(s_name, s_typ, s_gew, s_dat, s_kauf, s_manuell)
      )
      speichere_daten(AKTIV_DATEI, aktive_items, ist_verkauf=False)
      st.sidebar.success("Gespeichert!")
      st.rerun()


if __name__ == "__main__":
  main()