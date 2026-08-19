"""Connexion SQLAlchemy au Data Warehouse.

Les identifiants de connexion sont lus depuis l'environnement
(fichier `.env`, charge par python-dotenv). Aucun mot de passe,
utilisateur ou hote n'est code en dur dans le code.

Variables supportees :
- DATABASE_URL : URL de connexion complete (prioritaire si fournie)
- DW_DB_HOST   : hote (defaut : localhost)
- DW_DB_PORT   : port (defaut : 3306)
- DW_DB_USER   : utilisateur (defaut : root)
- DW_DB_PASSWORD : mot de passe (defaut : vide)
- DW_DB_NAME   : nom de la base (defaut : datawarehouse)
"""

import os

from dotenv import dotenv_values, load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

load_dotenv()

# Valeurs du fichier .env uniquement (jamais les variables d'environnement
# d'autres projets qui peuvent "fuir" dans la session courante).
FILE_ENV = dotenv_values()


def get_database_url() -> str:
    """Retourne l'URL de connexion, a partir de DATABASE_URL ou des DW_DB_*.

    DATABASE_URL n'est pris en compte que s'il est declare explicitement
    dans le fichier .env. Sinon, la connexion est construite depuis les
    variables DW_DB_* (shell puis .env, puis valeurs par defaut).
    """
    if FILE_ENV.get("DATABASE_URL"):
        return FILE_ENV["DATABASE_URL"]

    url = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DW_DB_USER") or FILE_ENV.get("DW_DB_USER", "root"),
        password=os.getenv("DW_DB_PASSWORD") or FILE_ENV.get("DW_DB_PASSWORD", ""),
        host=os.getenv("DW_DB_HOST") or FILE_ENV.get("DW_DB_HOST", "localhost"),
        port=int(os.getenv("DW_DB_PORT") or FILE_ENV.get("DW_DB_PORT", "3306")),
        database=os.getenv("DW_DB_NAME") or FILE_ENV.get("DW_DB_NAME", "datawarehouse"),
    )
    return url.render_as_string(hide_password=False)


def get_engine():
    """Cree et retourne le moteur SQLAlchemy."""
    return create_engine(get_database_url(), pool_pre_ping=True)


if __name__ == "__main__":
    engine = get_engine()
    print(f"Engine cree : {engine.url}")