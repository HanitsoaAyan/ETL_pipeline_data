"""Chargement des donnees transformees dans le Data Warehouse.

Flux :
    Transform (clean/) -> pandas.DataFrame -> df.to_sql() -> Data Warehouse

Le chargeur est volontairement FLEXIBLE :
- il lit uniquement les colonnes presentes dans les fichiers sources
  (aucune colonne inventee);
- les colonnes manquantes sont ignorees (valeurs NULL dans la base);
- les valeurs manquantes / non convertibles sont remplacees par NULL
  (jamais un 0 ou valeur invraisemblable invente);
- chaque cle dimension inconnue referencee par un fait est remplacee
  par la cle "inconnue" (id 0), ce qui garantit le respect des cles
  etrangeres quelle que soit la qualite des donnees;
- un relance efface puis recharge la base (operation idempotente).

Variables d'environnement (.env) :
    CLEAN_DIR : dossier des donnees transformees (defaut : clean)
    DW_RESET  : "1" pour vider les tables avant chargement (defaut : 1)
"""

import json
import os
import sys

import pandas as pd
from sqlalchemy import text

from database import get_engine

CLEAN_DIR = os.getenv("CLEAN_DIR", "clean")
RESET = os.getenv("DW_RESET", "1") == "1"

# Mapping colonnes sources (transformees) -> colonnes Data Warehouse.
# Chaque colonne DW accepte plusieurs synonymes de nom source (EN et FR),
# afin de rester robuste quel que soit le fichier fourni par Transform.
CLIENT_COLUMNS = {
    "client_id": ["customer_id", "client_id"],
    "nom": ["name", "nom"],
    "email": ["email"],
    "pays": ["country", "pays"],
    "age": ["age"],
    "date_inscription": ["signup_date", "date_inscription", "date_naissance"],
}
PRODUCT_COLUMNS = {
    "product_id": ["product_id"],
    "nom": ["name", "nom"],
    "categorie": ["category", "categorie"],
    "prix": ["price", "prix"],
    "stock": ["stock"],
}
ORDER_COLUMNS = {
    "order_id": ["order_id"],
    "client_id": ["customer_id", "client_id"],
    "montant": ["amount", "montant"],
    "statut": ["status", "statut"],
    "date": ["order_date", "date", "date_commande"],
}

UNKNOWN_ID = 0
UNKNOWN_LABEL = "(inconnu)"


# ---------------------------------------------------------------------
# Lecture / nettoyage
# ---------------------------------------------------------------------

def find_file(filename: str) -> str:
    """Localise un fichier dans le dossier des donnees transformees.

    Tolere un eventuel espace de tete dans le nom reellement present sur le
    disque (ex. ' customer_clean.csv').
    """
    direct = os.path.join(CLEAN_DIR, filename)
    if os.path.exists(direct):
        return direct

    stripped = filename.lstrip()
    try:
        entries = os.listdir(CLEAN_DIR)
    except OSError:
        entries = []
    for entry in entries:
        path = os.path.join(CLEAN_DIR, entry)
        if entry.strip() == stripped and os.path.isfile(path):
            return path
    return direct


def detect_delimiter(path: str) -> str:
    """Detecte le separateur de colonnes (premiere ligne du fichier)."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        first_line = f.readline()
    counts = {sep: first_line.count(sep) for sep in (",", ";", "\t")}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def read_csv_robust(path: str) -> pd.DataFrame:
    """Lit un CSV en detectant le separateur : ',', ';' ou tabulation."""
    try:
        return pd.read_csv(path, sep=detect_delimiter(path), encoding="utf-8", dtype="string")
    except UnicodeDecodeError:
        return pd.read_csv(path, sep=detect_delimiter(path), encoding="latin-1", dtype="string")
    except Exception:
        raise ValueError(f"[ERREUR] Impossible de lire le CSV : {path}")


def read_json_robust(path: str):
    """Lit un JSON (liste d'objets OU objet contenant une liste)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return value
        return [data]
    raise ValueError(f"[ERREUR] Format JSON inattendu : {path}")


def _to_str(series: pd.Series) -> list:
    values = []
    for v in series.tolist():
        if v is None or pd.isna(v):
            values.append(None)
        else:
            text = str(v).strip()
            values.append(text if text else None)
    return values


def _to_int(series: pd.Series) -> list:
    numeric = pd.to_numeric(series, errors="coerce")
    values = []
    for v in numeric.tolist():
        if v is None or pd.isna(v):
            values.append(None)
        else:
            values.append(int(v))
    return values


def _to_float(series: pd.Series) -> list:
    numeric = pd.to_numeric(series, errors="coerce")
    values = []
    for v in numeric.tolist():
        if v is None or pd.isna(v):
            values.append(None)
        else:
            values.append(float(v))
    return values


def _to_date(series: pd.Series, fmt: str = "iso") -> list:
    parsed = pd.to_datetime(series, errors="coerce")
    values = []
    for ts in parsed.tolist():
        if ts is None or pd.isna(ts) or pd.isnull(ts):
            values.append(None)
        else:
            date = ts.date()
            if fmt == "iso":
                values.append(date.isoformat())
            else:
                values.append(date.year * 10000 + date.month * 100 + date.day)
    return values


def _normalize(name: str) -> str:
    """Normalise un nom de colonne : minuscules, espaces -> '_'."""
    return str(name).strip().lower().replace(" ", "_")


def records_to_columns(records: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Selectionne uniquement les colonnes sources presentes et les renomme.

    mapping : {colonne_dw : [synonymes source]} (EN et FR tolerees).
    La recherche de colonnes tolere la casse / espaces ('Customer ID' == 'customer_id').
    """
    available = {_normalize(col): col for col in records.columns}
    result = {}
    unavailable = []
    for dw_col, aliases in mapping.items():
        if isinstance(aliases, str):
            aliases = [aliases]
        actual = next((available[a] for a in aliases if a in available), None)
        if actual is not None:
            result[dw_col] = records[actual]
        else:
            unavailable.append(dw_col)
    if unavailable:
        print(f"  [INFO] colonnes absentes des donnees, ignorees (NULL) : {', '.join(unavailable)}")
    return pd.DataFrame(result)


# ---------------------------------------------------------------------
# Construction des dataframes dimensionnels / de fait
# ---------------------------------------------------------------------

def build_dim_client(df: pd.DataFrame) -> pd.DataFrame:
    cols = records_to_columns(df, CLIENT_COLUMNS)
    frame = pd.DataFrame(dict(
        client_id=_to_int(cols["client_id"]) if "client_id" in cols else [None] * len(cols),
        nom=_to_str(cols["nom"]) if "nom" in cols else [None] * len(cols),
        email=_to_str(cols["email"]) if "email" in cols else [None] * len(cols),
        pays=_to_str(cols["pays"]) if "pays" in cols else [None] * len(cols),
        age=_to_int(cols["age"]) if "age" in cols else [None] * len(cols),
        date_inscription=_to_date(cols["date_inscription"]) if "date_inscription" in cols else [None] * len(cols),
    ))
    frame = frame.dropna(subset=["client_id"])
    frame = frame.drop_duplicates(subset=["client_id"], keep="first")
    return frame


def build_dim_product(df: pd.DataFrame) -> pd.DataFrame:
    cols = records_to_columns(df, PRODUCT_COLUMNS)
    frame = pd.DataFrame(dict(
        product_id=_to_int(cols["product_id"]) if "product_id" in cols else [None] * len(cols),
        nom=_to_str(cols["nom"]) if "nom" in cols else [None] * len(cols),
        categorie=_to_str(cols["categorie"]) if "categorie" in cols else [None] * len(cols),
        prix=_to_float(cols["prix"]) if "prix" in cols else [None] * len(cols),
        stock=_to_int(cols["stock"]) if "stock" in cols else [None] * len(cols),
    ))
    frame = frame.dropna(subset=["product_id"])
    frame = frame.drop_duplicates(subset=["product_id"], keep="first")
    return frame


def build_dim_date(orders: pd.DataFrame) -> pd.DataFrame:
    """Construit DIM_DATE a partir de toutes les dates presentes dans les faits."""
    available = {_normalize(col): col for col in orders.columns}
    src_col = next((available[a] for a in ORDER_COLUMNS["date"] if a in available), None)
    rows = []
    if src_col is not None:
        for iso in _to_date(orders[src_col], fmt="iso"):
            if iso is None:
                continue
            year, month, day = map(int, iso.split("-"))
            rows.append((year * 10000 + month * 100 + day, iso, day, month, year))

    frame = pd.DataFrame(
        rows,
        columns=["date_id", "date_complete", "jour", "mois", "annee"],
    ).drop_duplicates(subset=["date_id"], keep="first")
    return frame


def build_fact_order(orders: pd.DataFrame, dim_client: pd.DataFrame, dim_date: pd.DataFrame) -> pd.DataFrame:
    cols = records_to_columns(orders, ORDER_COLUMNS)
    n = len(orders)

    order_id = _to_int(cols["order_id"]) if "order_id" in cols else [None] * n
    customer_id = _to_int(cols["client_id"]) if "client_id" in cols else [None] * n
    montant = _to_float(cols["montant"]) if "montant" in cols else [None] * n
    statut = _to_str(cols["statut"]) if "statut" in cols else [None] * n
    date_iso = _to_date(cols["date"]) if "date" in cols else [None] * n

    # Cles connues dans les dimensions : toute reference hors de cet ensemble
    # pointe vers la cle (inconnue) d'id 0 -> jamais de violation de FK.
    valid_client_ids = set(dim_client["client_id"].tolist())
    valid_date_ids = set(dim_date["date_id"].tolist())

    date_ids = []
    for iso in date_iso:
        if iso is None:
            date_ids.append(UNKNOWN_ID)
            continue
        year, month, day = map(int, iso.split("-"))
        date_id = year * 10000 + month * 100 + day
        date_ids.append(date_id if date_id in valid_date_ids else UNKNOWN_ID)

    frame = pd.DataFrame(dict(
        order_id=[c if c is not None else UNKNOWN_ID for c in order_id],
        client_id=[c if c in valid_client_ids else UNKNOWN_ID for c in customer_id],
        date_id=date_ids,
        montant=montant,
        statut=statut,
    ))
    frame = frame.drop_duplicates(subset=["order_id"], keep="first")
    return frame


# ---------------------------------------------------------------------
# Chargement
# ---------------------------------------------------------------------

def add_unknown_row(frame: pd.DataFrame, key: str) -> pd.DataFrame:
    """Retourne la dimension complete avec la cle (inconnue) d'id 0 si absente.

    La ligne inconnue contient 0 pour la cle et NULL pour toutes les autres
    colonnes, afin de rester compatible avec les types de la base.
    """
    if not frame.empty and UNKNOWN_ID in frame[key].astype(object).tolist():
        return frame
    row = {key: UNKNOWN_ID}
    row.update({col: None for col in frame.columns if col != key})
    return pd.concat([frame, pd.DataFrame([row])], ignore_index=True)


def load_table(engine, table: str, frame: pd.DataFrame) -> int:
    if frame.empty:
        print(f"  [SKIP] {table} : aucune ligne a charger")
        return 0
    frame.to_sql(table, engine, if_exists="append", index=False, chunksize=1000)
    return len(frame)


def reset_tables(engine) -> None:
    with engine.begin() as conn:
        for table in ("fact_order", "dim_date", "dim_product", "dim_client"):
            conn.execute(text(f"DELETE FROM {table}"))


def check_source_present() -> dict:
    """Verifie la presence des fichiers sources, renvoie leurs chemins."""
    files = {
        "clients": find_file("customer_clean.csv"),
        "products": find_file("products_clean.csv"),
        "orders": find_file("orders_clean.json"),
    }
    missing = [label for label, path in files.items() if not os.path.exists(path)]
    if missing:
        raise FileNotFoundError(
            f"[ERREUR] Fichiers sources absents dans '{CLEAN_DIR}' : {', '.join(missing)}"
        )
    return files


def main() -> int:
    engine = get_engine()
    print(f"Connexion : {engine.url}")
    print(f"Dossier des donnees transformees : {CLEAN_DIR}")

    try:
        files = check_source_present()
    except FileNotFoundError as exc:
        print(exc)
        return 1

    try:
        # Lecture des donnees transformees
        clients = pd.DataFrame(read_json_robust(files["clients"])) if files["clients"].endswith(".json") \
            else read_csv_robust(files["clients"])
        products = read_csv_robust(files["products"])
        orders = pd.DataFrame(read_json_robust(files["orders"]))

        # Battery de controles
        dim_client = build_dim_client(clients)
        dim_product = build_dim_product(products)
        dim_date = build_dim_date(orders)
        fact_order = build_fact_order(orders, dim_client, dim_date)

        if fact_order.empty:
            print("[ERREUR] aucune commande (fact_order) a charger.")
            return 1

        if RESET:
            print("Reinitialisation des tables (relance idempotente)...")
            reset_tables(engine)

        print("\n[1/4] Loading clients...")
        dim_client = add_unknown_row(dim_client, "client_id")
        n1 = load_table(engine, "dim_client", dim_client)
        print(f"OK {n1} rows inserted")

        print("\n[2/4] Loading products...")
        dim_product = add_unknown_row(dim_product, "product_id")
        n2 = load_table(engine, "dim_product", dim_product)
        print(f"OK {n2} rows inserted")

        print("\n[3/4] Loading dates...")
        dim_date = add_unknown_row(dim_date, "date_id")
        n3 = load_table(engine, "dim_date", dim_date)
        print(f"OK {n3} rows inserted")

        print("\n[4/4] Loading orders...")
        n4 = load_table(engine, "fact_order", fact_order)
        print(f"OK {n4} rows inserted")

        # Verification finale
        with engine.connect() as conn:
            counts = {
                table: conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                for table in ("dim_client", "dim_product", "dim_date", "fact_order")
            }
        print("\n=== VERIFICATION FINALE DATAWAREHOUSE ===")
        for table, count in counts.items():
            print(f"{table}: {count} lignes")
        return 0

    except Exception as exc:
        print(f"[ERREUR SQL / traitement] {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())