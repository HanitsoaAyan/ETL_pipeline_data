# Clean — Module de contrôle qualité et transformation (ETL)

## Contexte

Ce dossier correspond à la deuxième étape du pipeline ETL du projet, juste après l'extraction :

```
Sources de données → Extract → Raw Data → Validation & Data Quality → Transform → Load → Data Warehouse → Analyse / ML
```

Ce module couvre les étapes **Validation & Data Quality** et **Transform**. Il prend en entrée les données brutes produites par le module `Extract` (voir `raw/` et son [README](../README.md)), les contrôle, les nettoie, et produit des données propres et documentées, destinées à être reprises par l'étape suivante : **le chargement dans le Data Warehouse**.

Chaque source est traitée indépendamment, avec la même méthode en deux temps :
1. **`quality_check_*`** : mesure les anomalies (valeurs manquantes, doublons, valeurs invalides, volumes suspects) sans rien modifier.
2. **`transform_*`** : applique uniquement les corrections justifiées par une règle métier claire ; ce qui ne peut pas être corrigé sans inventer une donnée est conservé tel quel et documenté ci-dessous.

## Structure du dossier

```
clean/
├── customers_clean.csv       # clients nettoyés
├── orders_clean.json         # commandes nettoyées
├── products_clean.csv        # produits (aucune anomalie détectée)
├── reviews_clean.json        # avis produits (aucune anomalie détectée)
├── utilisateurs_clean.json   # utilisateurs (base MySQL) — ⚠️ voir anomalies
├── relations_clean.json      # relations client-commande (Neo4j) — ⚠️ voir anomalies
└── README.md                 # ce fichier
```

Le notebook contenant les fonctions `quality_check_*` / `transform_*` et leur exécution sur chaque source se trouve à `notebooks/quality_transformation.ipynb`.

## Résumé par source

### `customers_clean.csv`
- 1 doublon supprimé (client dupliqué avec le même email).
- 1 âge invalide (120 ans) remplacé par une valeur vide plutôt que conservé tel quel.
- 1 email manquant, 1 date d'inscription manquante : **conservés vides**, non corrigés (aucune valeur fiable à déduire).

### `orders_clean.json`
- 1 montant manquant sur une commande **annulée** : mis à 0 (règle métier — une commande annulée n'a pas de montant réel).
- 1 montant élevé (9999) sur une commande `completed` : **laissé tel quel**, à vérifier manuellement si besoin — ce n'est pas nécessairement une erreur.

### `products_clean.csv`
- Aucune anomalie détectée (pas de valeur manquante, pas de doublon, pas de prix/stock invalide).

### `reviews_clean.json`
- Aucune anomalie détectée. Tous les `product_id` référencés existent bien dans `products_clean.csv`. Toutes les notes sont valides (entre 1 et 5).

### `utilisateurs_clean.json` ⚠️
- Seulement 2 lignes extraites, alors que la base source (`basededonner.sql`) en contient 9. **Extraction probablement incomplète** — à vérifier avant toute utilisation pour de l'analyse ou du reporting.
- Aucun crédit négatif détecté sur les lignes présentes (la colonne `credit_negatif` est ajoutée pour un futur contrôle si le volume est corrigé).

### `relations_clean.json` ⚠️
- Seulement 2 lignes extraites, alors qu'`orders_clean.json` contient 6 commandes. **Extraction probablement incomplète** — même remarque que pour `utilisateurs_clean.json`.

## Comment utiliser ces fichiers

Ces fichiers sont prêts à être chargés directement (`pandas.read_csv` / `pandas.read_json`) par l'étape de chargement dans le Data Warehouse. **Avant de les utiliser pour une analyse ou un modèle**, prendre en compte les points ⚠️ ci-dessus, en particulier le volume suspect de `utilisateurs_clean.json` et `relations_clean.json`.

## Prochaine étape du pipeline

Les données de ce dossier sont destinées à être reprises par l'étape suivante : **le chargement (Load)** dans le Data Warehouse.
