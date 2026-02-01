import sqlite3
import pandas as pd

DB_NAME = "stock.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS produits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origine TEXT NOT NULL DEFAULT 'SOUDAN',
            marque TEXT NOT NULL,
            nom TEXT NOT NULL,
            conditionnement TEXT NOT NULL,
            prix_vente_unite REAL DEFAULT 0,
            quantite INTEGER DEFAULT 0,
            UNIQUE(marque, nom, conditionnement)
        )
    """)

    conn.commit()
    conn.close()


def ajouter_produit(marque, nom, prix, conditionnement, quantite=0, origine="SOUDAN"):
    try:
        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            INSERT INTO produits 
            (marque, nom, conditionnement, prix_vente_unite, quantite, origine)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            marque.strip().upper(),
            nom.strip().upper(),
            conditionnement.strip().upper(),
            float(prix),
            int(quantite),
            origine.strip().upper()
        ))

        conn.commit()
        return True
    except Exception as e:
        print("Erreur ajout :", e)
        return False
    finally:
        conn.close()


def lire_tous_produits():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM produits", conn)
    conn.close()
    return df


def modifier_stock(id_produit, nouvelle_quantite):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "UPDATE produits SET quantite = ? WHERE id = ?",
            (int(nouvelle_quantite), int(id_produit))
        )
        conn.commit()
        return True
    except Exception as e:
        print("Erreur modification stock :", e)
        return False
    finally:
        conn.close()


def supprimer_produit(id_produit):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM produits WHERE id = ?", (int(id_produit),))
        conn.commit()
    except Exception as e:
        print("Erreur suppression :", e)
    finally:
        conn.close()


def importer_stock_intelligent(marque, nom, conditionnement, prix, mouvement_stock, origine):
    """
    - Nettoie toutes les entrées
    - Quantité = ENTIER
    - Met à jour le prix si le produit existe
    """

    try:
        marque = str(marque or "").strip().upper()
        nom = str(nom or "").strip().upper()
        conditionnement = str(conditionnement or "").strip().upper()
        origine = str(origine or "SOUDAN").strip().upper()

        if not nom or not conditionnement:
            return "ignore"

        # Sécurisation prix
        try:
            prix = float(str(prix).replace(",", ".").replace("€", "").strip())
        except:
            prix = 0.0

        # Sécurisation quantité
        try:
            mouvement_stock = int(float(mouvement_stock))
        except:
            mouvement_stock = 0

        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            SELECT id, quantite FROM produits
            WHERE marque = ? AND nom = ? AND conditionnement = ?
        """, (marque, nom, conditionnement))

        row = c.fetchone()

        if row:
            new_qte = row["quantite"] + mouvement_stock
            c.execute("""
                UPDATE produits 
                SET quantite = ?, prix_vente_unite = ?
                WHERE id = ?
            """, (new_qte, prix, row["id"]))
            conn.commit()
            return "mis_a_jour"

        else:
            c.execute("""
                INSERT INTO produits
                (marque, nom, conditionnement, prix_vente_unite, quantite, origine)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (marque, nom, conditionnement, prix, mouvement_stock, origine))
            conn.commit()
            return "cree"

    except Exception as e:
        print("Erreur import intelligent :", e)
        return "erreur"
    finally:
        conn.close()
