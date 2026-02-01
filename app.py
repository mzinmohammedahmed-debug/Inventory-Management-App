import streamlit as st
import pandas as pd
import db
import os
import time
import re

# =========================================================
# 0. INITIALISATION
# =========================================================
db.init_db()

FICHIER_MARQUES = "marques.txt"
MARQUES_DEFAUT = "TERRE DU NIL, ALWATANIA, GOLDEN RIVER, TRI-C, JUHAYNA, BEST, ELNASR, SAMSUNG, APPLE, NIKE, HARVEST, EL MALIKA, CHEZ ZOLL"


def charger_marques():
    if os.path.exists(FICHIER_MARQUES):
        with open(FICHIER_MARQUES, "r", encoding="utf-8") as f:
            c = f.read().strip()
            if c:
                return c
    return MARQUES_DEFAUT


def sauvegarder_nouvelles_marques(anciennes, nouvelles):
    s = set(m.strip().upper() for m in anciennes.split(",") if m.strip())
    for m in nouvelles:
        if m and isinstance(m, str):
            s.add(m.strip().upper())
    txt = ", ".join(sorted(list(s)))
    with open(FICHIER_MARQUES, "w", encoding="utf-8") as f:
        f.write(txt)
    return txt


# =========================================================
# 1. UTILITAIRES DE NETTOYAGE
# =========================================================
def nettoyer_prix(valeur):
    """Transforme '12,50 €' ou 12.5 en float 12.5"""
    if pd.isna(valeur) or valeur == "":
        return 0.0
    s = str(valeur).replace("€", "").strip()
    # On garde chiffres, point, virgule, moins
    s = re.sub(r"[^0-9.,-]", "", s)
    s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0


def nettoyer_qte(valeur):
    """Transforme '10 cartons' en 10"""
    if pd.isna(valeur) or valeur == "":
        return 1
    s = str(valeur).replace(",", ".")
    match = re.search(r"[-+]?\d*\.?\d+", s)
    if match:
        return float(match.group())
    return 1


# =========================================================
# 2. CONFIGURATION PAGE
# =========================================================
st.set_page_config(page_title="Gestion Stock Excel", layout="wide")
st.title("📊 Gestion de Stock")

menu = [
    "Afficher le stock",
    "Ajouter un produit",
    "Modifier le stock",
    "Supprimer Produit",
    "Importer Excel",
]
choix = st.sidebar.radio("Navigation", menu)

# =========================================================
# PAGE : AFFICHER STOCK
# =========================================================
if choix == "Afficher le stock":
    st.header("État du stock")
    df = db.lire_tous_produits()
    if not df.empty:
        col_p = "prix_vente_unite"
        if col_p in df.columns:
            df[col_p] = pd.to_numeric(df[col_p], errors="coerce").fillna(0.0)
            df["quantite"] = pd.to_numeric(df["quantite"], errors="coerce").fillna(0)
            df.insert(0, "N°", range(1, 1 + len(df)))

            st.dataframe(
                df, width="stretch", hide_index=True, column_config={"id": None}
            )

            tot = df["quantite"].sum()
            val = (df["quantite"] * df[col_p]).sum()
            c1, c2 = st.columns(2)
            c1.metric("Articles", int(tot))
            c2.metric("Valeur Stock", f"{val:.2f} €")
    else:
        st.info("Le stock est vide.")

# =========================================================
# PAGE : AJOUT MANUEL
# =========================================================
elif choix == "Ajouter un produit":
    st.header("Nouveau Produit")
    with st.form("new"):
        c1, c2 = st.columns(2)
        with c1:
            m = st.text_input("Marque").upper()
            n = st.text_input("Nom").upper()
            o = st.text_input("Origine", "SOUDAN").upper()
        with c2:
            c = st.text_input("Conditionnement").upper()
            p = st.number_input("Prix", 0.0, step=0.5)
            q = st.number_input("Stock", 0, step=1)
        if st.form_submit_button("Enregistrer"):
            if m and n and c:
                db.ajouter_produit(m, n, p, c, q, o)
                st.success("Ajouté !")
                time.sleep(0.5)
                st.rerun()

# =========================================================
# PAGE : MODIFIER
# =========================================================
elif choix == "Modifier le stock":
    st.header("Mouvements")
    df = db.lire_tous_produits()
    if not df.empty:
        df["quantite"] = (
            pd.to_numeric(df["quantite"], errors="coerce").fillna(0).astype(int)
        )
        df["lbl"] = df["marque"] + " " + df["nom"] + " [" + df["conditionnement"] + "]"
        sel = st.selectbox("Produit", df["lbl"].unique())
        row = df[df["lbl"] == sel].iloc[0]
        st.metric("Stock Actuel", int(row["quantite"]))
        c1, c2 = st.columns(2)
        with c1:
            a = st.number_input("Ajouter", 0)
            if st.button("➕"):
                db.modifier_stock(row["id"], int(row["quantite"]) + a)
                st.rerun()
        with c2:
            r = st.number_input("Retirer", 0)
            if st.button("➖"):
                if int(row["quantite"]) - r >= 0:
                    db.modifier_stock(row["id"], int(row["quantite"]) - r)
                    st.rerun()
                else:
                    st.error("Impossible")

# =========================================================
# PAGE : SUPPRIMER
# =========================================================
elif choix == "Supprimer Produit":
    st.header("Suppression")
    df = db.lire_tous_produits()
    if not df.empty:
        df["lbl"] = str(df["id"]) + " | " + df["marque"] + " " + df["nom"]
        sel = st.selectbox("Produit", df["lbl"].unique())
        if st.button("SUPPRIMER 🚨", type="primary"):
            db.supprimer_produit(int(sel.split("|")[0]))
            st.success("Fait.")
            time.sleep(1)
            st.rerun()

# =========================================================
# PAGE : IMPORT EXCEL AVANCÉ
# =========================================================
elif choix == "Importer Excel":
    st.header("📂 Importation Excel")

    sens = st.radio(
        "Type d'opération :",
        ["Achat (Entrée Stock +)", "Vente (Sortie Stock -)"],
        horizontal=True,
    )
    if "preview" not in st.session_state:
        st.session_state.preview = None

    up = st.file_uploader(
        "Glissez votre fichier Excel (.xlsx, .xls)", type=["xlsx", "xls"]
    )

    if up:
        df_src = None
        try:
            # 1. LECTURE INTELLIGENTE (HEADER HUNTER)
            # On lit d'abord sans en-tête pour trouver où commence le tableau
            raw_preview = pd.read_excel(up, header=None, nrows=20)

            idx_header = 0
            # Mots-clés pour trouver la ligne des titres
            keywords = [
                "DESIGNATION",
                "LIBELLE",
                "DESCRIPTION",
                "ITEM",
                "PRODUCT",
                "ARTICLE",
                "NOM",
                "PRIX",
                "QTE",
                "QTÉ",
            ]

            found = False
            for i, row in raw_preview.iterrows():
                row_str = " ".join([str(x).upper() for x in row if pd.notna(x)])
                if any(k in row_str for k in keywords):
                    idx_header = i
                    found = True
                    break

            # On recharge le fichier avec le bon header
            if found:
                df_src = pd.read_excel(up, header=idx_header)
                st.success(f"Tableau détecté à la ligne {idx_header + 1}")
            else:
                # Si rien trouvé, on suppose ligne 0
                df_src = pd.read_excel(up, header=0)
                st.warning("En-tête non détecté automatiquement. Vérification ligne 1.")

            # Nettoyage des noms de colonnes (espaces vides)
            df_src.columns = [str(c).strip() for c in df_src.columns]

        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")

        # 2. MAPPING ET TRAITEMENT
        if df_src is not None and not df_src.empty:
            if st.session_state.preview is None:
                st.divider()
                st.write("### 🛠️ Configuration des colonnes")
                st.dataframe(df_src.head(3))

                cols = list(df_src.columns)

                def get_idx(lst):
                    for i, c in enumerate(cols):
                        if any(x in c.upper() for x in lst):
                            return i
                    return 0

                idx_n = get_idx(["DES", "LIB", "PROD", "ITEM", "NOM", "ART", "البيان"])
                idx_q = get_idx(["QTE", "QTY", "QUA", "NBR", "الكمية", "العدد"])
                idx_p = get_idx(["PRIX", "PRI", "PU", "AMO", "السعر", "HT"])
                idx_c = get_idx(["COND", "COL", "PACK", "CARTON", "التعبئة"])
                idx_o = get_idx(["ORIG", "PAY", "SOUR", "المنشأ"])

                with st.form("map"):
                    c1, c2 = st.columns(2)
                    with c1:
                        sel_n = st.selectbox("Colonne DESCRIPTION", cols, index=idx_n)
                        sel_p = st.selectbox("Colonne PRIX", cols, index=idx_p)
                        sel_c = st.selectbox(
                            "Colonne CONDITIONNEMENT",
                            ["-- EXTRACTION AUTO --"] + cols,
                            index=0,
                        )
                    with c2:
                        sel_q = st.selectbox(
                            "Colonne QUANTITÉ",
                            ["1 par défaut"] + cols,
                            index=(idx_q + 1),
                        )
                        sel_o = st.selectbox(
                            "Colonne ORIGINE",
                            ["Soudan (Défaut)"] + cols,
                            index=(idx_o + 1),
                        )
                        do_clean = st.checkbox(
                            "Extraction Intelligente (Sépare Marque/Cond du nom)", True
                        )
                        txt_m = st.text_area(
                            "Marques connues (pour nettoyage)", charger_marques()
                        )

                    if st.form_submit_button("Lancer l'analyse 🚀"):
                        res = []
                        marques = sorted(
                            [x.strip().upper() for x in txt_m.split(",") if x.strip()],
                            key=len,
                            reverse=True,
                        )

                        bar = st.progress(0)
                        for i, (_, r) in enumerate(df_src.iterrows()):
                            try:
                                # 1. TEXTE
                                raw = str(r[sel_n]).strip()
                                work = raw.upper()
                                m_final, c_final, n_final = "", "", raw

                                # 2. COND (Colonne ou Auto)
                                if sel_c != "-- EXTRACTION AUTO --" and sel_c in r:
                                    v = str(r[sel_c]).strip()
                                    if v and v.upper() not in ["NAN", "NONE", "NULL"]:
                                        c_final = v

                                if do_clean:
                                    # Regex Cond (ex: 6x2kg, 12x500ml)
                                    pat = r"(\d+\s*[xX]\s*\d+\s*[a-zA-Z]+|\d+\s*[xX]\s*\d+|\d+\s*(?:KG|G|L|ML))"
                                    mat = re.search(pat, work)
                                    if mat:
                                        found = mat.group(0)
                                        if not c_final:
                                            c_final = found
                                        work = work.replace(found, "").strip()

                                    # Marque
                                    for m in marques:
                                        if m in work:
                                            m_final = m
                                            work = work.replace(m, "").strip()
                                            break
                                    # Si pas de marque, tente le 1er mot
                                    if not m_final and work:
                                        spl = work.split(" ")
                                        if spl and not spl[0][0].isdigit():
                                            m_final = spl[0]

                                    n_final = work.replace("  ", " ").strip(" -")
                                else:
                                    n_final = raw

                                # 3. PRIX / QTE / ORIGINE
                                val_p = nettoyer_prix(r[sel_p]) if sel_p in r else 0.0
                                val_q = (
                                    nettoyer_qte(r[sel_q])
                                    if sel_q != "1 par défaut" and sel_q in r
                                    else 1
                                )
                                val_q = -abs(val_q) if "Vente" in sens else abs(val_q)

                                val_o = (
                                    str(r[sel_o]).upper()
                                    if sel_o != "Soudan (Défaut)" and sel_o in r
                                    else "SOUDAN"
                                )

                                # On ignore les lignes vides ou sans nom
                                if (
                                    n_final
                                    and len(n_final) > 1
                                    and n_final.upper() != "NAN"
                                ):
                                    res.append(
                                        {
                                            "Marque": m_final,
                                            "Nom": n_final,
                                            "Conditionnement": c_final,
                                            "Prix Unitaire": val_p,
                                            "Quantité": val_q,
                                            "Origine": val_o,
                                        }
                                    )
                            except:
                                pass
                            bar.progress((i + 1) / len(df_src))

                        st.session_state.preview = pd.DataFrame(res)
                        st.rerun()
            else:
                st.info("👇 Vérifiez les données avant validation")
                edited = st.data_editor(
                    st.session_state.preview,
                    num_rows="dynamic",
                    use_container_width=True,
                )
                c1, c2 = st.columns([1, 4])
                if c1.button("Annuler"):
                    st.session_state.preview = None
                    st.rerun()
                if c2.button("Valider l'import ✅", type="primary"):
                    new_m = edited["Marque"].unique().tolist()
                    sauvegarder_nouvelles_marques(charger_marques(), new_m)

                    cnt_new, cnt_upd = 0, 0
                    bar = st.progress(0)
                    for i, (_, r) in enumerate(edited.iterrows()):
                        p_ok = nettoyer_prix(r["Prix Unitaire"])
                        ret = db.importer_stock_intelligent(
                            r["Marque"],
                            r["Nom"],
                            r["Conditionnement"],
                            p_ok,
                            r["Quantité"],
                            r["Origine"],
                        )
                        if ret == "cree":
                            cnt_new += 1
                        else:
                            cnt_upd += 1
                        bar.progress((i + 1) / len(edited))
                    st.success(f"Terminé ! (Nouveaux: {cnt_new}, Maj: {cnt_upd})")
                    time.sleep(1.5)
                    st.session_state.preview = None
                    st.rerun()
