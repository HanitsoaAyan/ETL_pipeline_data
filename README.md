Extract — Module d'extraction de données (ETL)

Contexte

Ce projet s'inscrit dans la mise en place d'un pipeline ETL complet (Extract, Transform, Load) permettant de collecter, transformer, contrôler et charger des données dans l'entrepôt de données (Data Warehouse) de la plateforme, en vue de leur exploitation pour l'analyse et le Machine Learning.
Le pipeline complet suit cette architecture :

Sources de données → Extract → Raw Data → Validation & Data Quality
→ Transform → Load → Data Warehouse → Analyse / ML

Ce module couvre uniquement la première étape : l'extraction. Son objectif est d'identifier les sources de données du projet, de s'y connecter, et d'en récupérer les données brutes, quel que soit leur format (fichier CSV, fichier JSON, base de données relationnelle, base de données graphe), tout en conservant une copie de ces données brutes pour assurer leur traçabilité.
Les données extraites par ce module sont destinées à être reprises par la personne en charge de l'étape suivante (validation et transformation), avant chargement final dans le Data Warehouse.

Structure du projet
Extract/
├── extract.py           # script principal, contient les 4 fonctions d'extraction
├── customers.csv         # source d'exemple (CSV)
├── orders.json            # source d'exemple (JSON)
├── products.csv            # source d'exemple (CSV)
├── reviews.json             # source d'exemple (JSON)
├── basededonner.sql          # script de création de la base MySQL "operateur"
├── .env                        # identifiants de connexion (NE JAMAIS COMMITER)
├── .env.example                 # modèle du fichier .env, sans les vrais identifiants
├── .gitignore                    # exclut .env et raw/ du dépôt Git
└── raw/                            # copies brutes générées à chaque exécution

Installation

1. Créer et activer un environnement virtuel (isole les dépendances du projet)

bash
python3 -m venv venv
source venv/bin/activate        # Linux / Mac
# venv\Scripts\activate         # Windows

2. Installer les dépendances

bash
pip install pandas sqlalchemy pymysql neo4j python-dotenv

3. Créer la base de données MySQL (obligatoire avant de tester la source base de données)

⚠️ Important : extract_db() ne fait que lire des données déjà existantes — il ne crée ni la base, ni la table, ni les données. Il faut donc que la base MySQL operateur existe avant de lancer extract.py, sinon vous aurez une erreur du type Unknown database 'operateur' ou Table 'operateur.utilisateurs' doesn't exist.

bash
mysql -u root -p < basededonner.sql

Cette commande exécute le script basededonner.sql, qui :

Crée la base operateur (si elle n'existe pas déjà)
Crée la table utilisateurs (colonnes numero, credit)
Insère quelques lignes de données de test

Vérifier que ça a fonctionné avant de continuer :

bash
mysql -u root -p -e "USE operateur; SELECT * FROM utilisateurs;"

Si ça affiche les lignes de la table, la base est prête et extract_db() pourra s'y connecter.

4. Configurer les identifiants — copier .env.example en .env et remplir avec vos vraies valeurs :

bash
cp .env.example .env
Configuration (.env)
env
# MySQL
DB_USER=votre_utilisateur
DB_PASSWORD=votre_mot_de_passe

# Neo4j Aura
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=xxxxxxxx
NEO4J_PASSWORD=votre_mot_de_passe_neo4j
NEO4J_DATABASE=neo4j

⚠️ Le fichier .env ne doit jamais être poussé sur GitHub — il contient de vrais mots de passe. Le .gitignore fourni l'exclut automatiquement. Seul .env.example (sans les vraies valeurs) est versionné, pour que toute personne qui clone le projet sache quelles variables renseigner.

Les 4 fonctions d'extraction
Fonction	Source	Principe
extract_csv()	Fichier .csv	Lecture directe avec pandas.read_csv()
extract_json()	Fichier .json	Chargement puis mise à plat avec pandas.json_normalize()
extract_db()	Base de données MySQL	Connexion via SQLAlchemy, exécution d'une requête SQL — nécessite que la base existe déjà (voir basededonner.sql)
extract_neo4j()	Base de données Neo4j	Connexion via le driver officiel, exécution d'une requête Cypher — nécessite que l'instance Neo4j existe et contienne des données

⚠️ Contrairement au CSV et au JSON (des fichiers autonomes qui existent tels quels), les sources base de données doivent être créées et peuplées au préalable — le script d'extraction ne fait que lire, jamais créer.

Chaque fonction suit le même principe, quel que soit le format d'origine :

Se connecter / lire la source
Récupérer les données dans un DataFrame pandas (tableau)
Sauvegarder une copie brute dans raw/<run_id>/ (traçabilité)
Retourner le DataFrame pour les étapes suivantes du pipeline (validation, transformation)
Exécuter le script
bash
python extract.py

Chaque source est extraite et son résultat affiché dans le terminal, avec le nombre de lignes récupérées et le chemin de la copie brute sauvegardée.

Traçabilité des données

À chaque exécution, un dossier est créé dans raw/, nommé d'après le run_id (un identifiant propre à cette extraction), contenant une copie exacte de la donnée récupérée à cet instant :

raw/
├── run-customers/customers.csv
├── run-orders/orders.json
├── run-utilisateurs/utilisateurs.json
└── run-relations/relations.json

Cela permet de retrouver, pour n'importe quelle exécution passée, exactement quelles données avaient été récupérées — utile en cas d'erreur en aval ou pour un audit.

Sources de données utilisées
Source	Type	Contenu
customers.csv	CSV	Clients (id, nom, email, date d'inscription, pays, âge)
orders.json	JSON	Commandes (id, client, montant, statut, date)
products.csv	CSV	Produits (id, nom, catégorie, prix, stock)
reviews.json	JSON	Avis produits (id, produit, note, commentaire, date)
Base MySQL operateur	Base de données	Utilisateurs (numéro, crédit)
Base Neo4j	Graphe	Clients et commandes reliés par une relation PLACED
Prochaine étape du pipeline

Les données extraites par ce module sont destinées à être reprises par l'étape suivante : validation et transformation (contrôle qualité, nettoyage, standardisation), avant chargement dans le Data Warehouse.
