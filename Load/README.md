# Load — Chargement des données transformées dans le Data Warehouse

Ce dossier correspond à la troisième étape du pipeline ETL :

```
Sources → Extract → Raw → Validation & Transform (clean/) → Load → Data Warehouse → Analyse / ML
```

Le module **Load** lit les données transformées produites dans `clean/`
(par le module Validation & Transform) et les charge dans une base
MySQL/MariaDB selon un **schéma en étoile** : `dim_client`, `dim_product`,
`dim_date`, `fact_order`.

## Fichiers

| Fichier | Rôle |
|---|---|
| `warehouse_schema.sql` | Crée la base `datawarehouse` et les 4 tables (clés primaires + étrangères) |
| `database.py` | Connexion SQLAlchemy, lue depuis l'environnement (`.env`), aucun identifiant en dur |
| `load_dw.py` | Chargeur : Transform → DataFrame → `to_sql()` → Data Warehouse |
| `requirements.txt` | Dépendances Python |
| `.env.example` | Modèle des variables d'environnement (sans valeurs réelles) |

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r Load/requirements.txt
```

## Configuration

Copier `Load/.env.example` vers `.env` à la racine du dépôt et renseigner
les valeurs. Le fichier `.env` est exclu de Git (il contient les identifiants).

| Variable | Défaut | Rôle |
|---|---|---|
| `DATABASE_URL` | *(vide)* | URL de connexion complète — prioritaire si fournie |
| `DW_DB_HOST` | `localhost` | Hôte MySQL |
| `DW_DB_PORT` | `3306` | Port MySQL |
| `DW_DB_USER` | `root` | Utilisateur |
| `DW_DB_PASSWORD` | *(vide)* | Mot de passe |
| `DW_DB_NAME` | `datawarehouse` | Base cible |
| `CLEAN_DIR` | `clean` | Dossier des données transformées |
| `DW_RESET` | `1` | `1` = vider les tables avant chaque chargement (idempotent) |

## Créer le schéma (une fois)

```bash
mysql -u root -p < Load/warehouse_schema.sql
```

Le script crée la base `datawarehouse` et les tables `dim_client`,
`dim_product`, `dim_date`, `fact_order`. `extract_db` ne lit que la base
`operateur` ; le Data Warehouse est une base séparée.

## Lancer le chargement

```bash
python Load/load_dw.py
```

Sortie attendue :

```
[1/4] Loading clients...
OK 8 rows inserted
[2/4] Loading products...
OK 9 rows inserted
[3/4] Loading dates...
OK 7 rows inserted
[4/4] Loading orders...
OK 6 rows inserted

=== VERIFICATION FINALE DATAWAREHOUSE ===
dim_client: 8 lignes
dim_product: 9 lignes
dim_date: 7 lignes
fact_order: 6 lignes
```

> Les compteurs incluent la ligne *(inconnue)* d'id 0 ajoutée à chaque
> dimension : elle garantit que toute référence inconnue dans un fait
> respecte les clés étrangères.

## Vérifier

```sql
USE datawarehouse;
SELECT COUNT(*) FROM dim_client;
SELECT COUNT(*) FROM dim_product;
SELECT COUNT(*) FROM dim_date;
SELECT COUNT(*) FROM fact_order;
```

## Architecture

```
clean/ (données transformées)
   │
   │ customers / products / orders
   ▼
load_dw.py  (pandas, colonnes non inventées, valeurs manquantes -> NULL)
   │
   ▼
      DIM_CLIENT ───── FACT_ORDER ───── DIM_DATE
                              │
                        DIM_PRODUCT (non relié aux faits : les commandes
                                     ne référencent aucun produit)
```

**Pourquoi `fact_order` n'a pas de `product_id` :** les données réelles
(`orders_clean.json`) ne contiennent aucun lien commande→produit. La mission
interdit d'inventer des colonnes ; le schéma reflète donc les données réelles.
Le chargeur est flexible : si une future source fournit un `product_id`, il
suffit d'ajouter la colonne au schéma et au mapping `ORDER_COLUMNS`.

## Robustesse du chargeur

- Lit uniquement les colonnes réellement présentes (aucune colonne inventée).
- Tolère : noms de colonnes avec espaces/majuscules, CSV `,` ou `;`,
  JSON liste ou objet, doublons de clés, dates illisibles, valeurs manquantes.
- Toute référence inconnue (client/date absent d'une dimension) est rattachée
  à la clé *(inconnue)* id 0 : plus jamais de violation de clé étrangère.
- Re-lancement sans risque : `DW_RESET=1` vide puis recharge les tables.
- Erreurs (fichier manquant, SQL) affichées clairement et code de sortie ≠ 0.
