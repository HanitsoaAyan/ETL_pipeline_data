import os
import shutil
import json
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text

RAW_DATA_DIR = "raw"


def extract_csv(file_path: str, run_id: str, delimiter: str = ",") -> pd.DataFrame:
    df = pd.read_csv(file_path, delimiter=delimiter, encoding="utf-8")

    raw_dir = os.path.join(RAW_DATA_DIR, run_id)
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, os.path.basename(file_path))
    shutil.copy(file_path, raw_path)

    print(f"[CSV] {file_path} -> {len(df)} lignes extraites | copie brute : {raw_path}")
    return df


def extract_json(file_path: str, run_id: str, record_path: str = None) -> pd.DataFrame:
    with open(file_path, "r", encoding="utf-8") as f:
        raw_json = json.load(f)

    data = raw_json[record_path] if record_path else raw_json
    df = pd.json_normalize(data)

    raw_dir = os.path.join(RAW_DATA_DIR, run_id)
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, os.path.basename(file_path))
    shutil.copy(file_path, raw_path)

    print(f"[JSON] {file_path} -> {len(df)} lignes extraites | copie brute : {raw_path}")
    return df

def extract_db(connection_string: str, query: str, run_id: str, raw_filename: str) -> pd.DataFrame:
    engine = create_engine(connection_string)
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    raw_dir = os.path.join(RAW_DATA_DIR, run_id)
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, raw_filename)
    df.to_json(raw_path, orient="records", force_ascii=False)

    print(f"[DB] requête exécutée -> {len(df)} lignes extraites | copie brute : {raw_path}")
    return df

if __name__ == "__main__":
    df_utilisateurs = extract_db(
        connection_string="mysql+pymysql://ayan:Ayan123!@localhost:3306/operateur",
        query="SELECT * FROM utilisateurs",
        run_id="run-utilisateurs",
        raw_filename="utilisateurs.json",
    )
    print(df_utilisateurs)
