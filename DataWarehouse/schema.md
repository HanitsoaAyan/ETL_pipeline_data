# Schema du Data Warehouse

Modèle en **étoile** de la base `datawarehouse` (MySQL/MariaDB), alimentée
par le module `Load` à partir des données transformées (`clean/`).

## Diagramme

```
                    DIM_DATE
                       │
                       │ date_id
                       ▼
  DIM_CLIENT ───── FACT_ORDER
   (client_id)       (client_id, date_id, montant, statut)

  DIM_PRODUCT   (indépendant des faits : les commandes ne référencent
                 aucun produit dans les données réelles)
```

## Tables

### `dim_client`

Informations clients. Source : `clean/ customer_clean.csv`.

| Colonne | Type | Source | Notes |
|---|---|---|---|
| `client_id` | INT | `customer_id` | Clé primaire |
| `nom` | VARCHAR(100) | `name` | |
| `email` | VARCHAR(150) | `email` | Peut être NULL |
| `pays` | VARCHAR(100) | `country` | |
| `age` | INT | `age` | Peut être NULL |
| `date_inscription` | DATE | `signup_date` | |

### `dim_product`

Informations produits. Source : `clean/products_clean.csv`.

| Colonne | Type | Source | Notes |
|---|---|---|---|
| `product_id` | INT | `product_id` | Clé primaire |
| `nom` | VARCHAR(100) | `name` | |
| `categorie` | VARCHAR(100) | `category` | |
| `prix` | DECIMAL(10,2) | `price` | |
| `stock` | INT | `stock` | |

### `dim_date`

Permet les analyses temporelles. Construite à partir de toutes les dates
présentes dans les faits (`orders_clean.json` → `order_date`).

| Colonne | Type | Notes |
|---|---|---|
| `date_id` | INT | Clé primaire, format AAAAMMJJ (ex. 20230120) |
| `date_complete` | DATE | Date complète |
| `jour` | TINYINT | Jour du mois |
| `mois` | TINYINT | Mois |
| `annee` | SMALLINT | Année |

### `fact_order`

Table de faits principale. Source : `clean/orders_clean.json`.

| Colonne | Type | Source | Notes |
|---|---|---|---|
| `order_id` | INT | `order_id` | Clé primaire |
| `client_id` | INT | `customer_id` | FK → `dim_client` |
| `date_id` | INT | `order_date` | FK → `dim_date` |
| `montant` | DECIMAL(10,2) | `amount` | NULL autorisé |
| `statut` | VARCHAR(20) | `status` | |

## Relations

```
fact_order.client_id → dim_client.client_id
fact_order.date_id   → dim_date.date_id
```

## Règle des clés "inconnues" (id 0)

Chaque dimension reçoit une ligne *inconnue* (id `0`, autres colonnes NULL).
Toute référence présente dans un fait mais absente d'une dimension est
rattachée à cet id `0` lors du chargement. Résultat : aucune violation de
clé étrangère possible, quelle que soit la qualité des données.

## Note : absence de `product_id` dans `fact_order`

Les commandes (`orders_clean.json`) ne contiennent aucun lien vers les
produits. Conformément à la règle « ne jamais inventer les colonnes
d'entrée », `fact_order` ne référence pas `dim_product`. `dim_product` est
tout de même chargée pour l'analyse produit ; l'ajout d'un `product_id`
dans les faits est possible si une source ultérieure le fournit.
