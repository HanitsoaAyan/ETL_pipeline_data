CREATE DATABASE IF NOT EXISTS operateur CHARACTER SET utf8mb4;
USE operateur;

CREATE TABLE IF NOT EXISTS utilisateurs (
    numero INT PRIMARY KEY,
    credit INT
);

INSERT INTO utilisateurs (numero, credit) VALUES
    (22, 20),
    (24, 860),
    (31, 0),
    (45, 1500),
    (52, -10),
    (67, 340),
    (78, 5000),
    (89, 15),
    (91, 200);

SELECT * FROM utilisateurs;