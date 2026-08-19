-- ============================================================
-- Data Warehouse - Schéma en étoile
-- Base : datawarehouse
-- Tables : dim_client, dim_product, dim_date, fact_order
-- ============================================================

CREATE DATABASE IF NOT EXISTS datawarehouse
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE datawarehouse;

-- ------------------------------------------------------------
-- DIM_CLIENT
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_client (
    client_id        INT          PRIMARY KEY,
    nom              VARCHAR(100),
    email            VARCHAR(150),
    pays             VARCHAR(100),
    age              INT,
    date_inscription DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- DIM_PRODUCT
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_product (
    product_id INT           PRIMARY KEY,
    nom        VARCHAR(100),
    categorie  VARCHAR(100),
    prix       DECIMAL(10,2),
    stock      INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- DIM_DATE
-- date_id au format AAAAMMJJ : 20230120 -> 2023-01-20
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_date (
    date_id       INT    PRIMARY KEY,
    date_complete DATE,
    jour          TINYINT,
    mois          TINYINT,
    annee         SMALLINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- FACT_ORDER
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_order (
    order_id INT,
    client_id INT,
    date_id   INT,
    montant   DECIMAL(10,2),
    statut    VARCHAR(20),
    PRIMARY KEY (order_id),
    CONSTRAINT fk_fact_order_client
        FOREIGN KEY (client_id) REFERENCES dim_client(client_id),
    CONSTRAINT fk_fact_order_date
        FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;