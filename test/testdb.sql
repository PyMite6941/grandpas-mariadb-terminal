-- Grandpa's MariaDB Terminal -- test database
-- =========================================
--
-- Creates a small "grandpas_test" database with a variety of column
-- types, so you can try the terminal (and see all the color coding)
-- without touching any real data.
--
-- Load it once:
--     mysql -u root -p < test/testdb.sql
--   or, if your server has no password:
--     mysql -u root < test/testdb.sql
--
-- Then copy .config.example.toml -> config.toml (it already points at
-- this database) and run the tool.

DROP DATABASE IF EXISTS grandpas_test;
CREATE DATABASE grandpas_test CHARACTER SET utf8mb4;
USE grandpas_test;

-- A little of everything: ints, decimals, text, dates, booleans, NULLs, blobs.
CREATE TABLE fish (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(50)   NOT NULL,
    species     VARCHAR(50),
    weight_kg   DECIMAL(6,2),
    is_favorite BOOLEAN       DEFAULT FALSE,
    caught_on   DATE,
    caught_at   DATETIME,
    notes       TEXT,
    photo       BLOB
);

INSERT INTO fish
    (name, species, weight_kg, is_favorite, caught_on, caught_at, notes, photo)
VALUES
    ('Big Bertha', 'Largemouth Bass', 4.20, TRUE,  '2025-06-14', '2025-06-14 06:32:00', 'Fought for 10 minutes!', 0x89504E47),
    ('Slippery Sam', 'Rainbow Trout', 1.35, FALSE, '2025-06-15', '2025-06-15 07:05:00', NULL, NULL),
    ('The One',     'Catfish',       9.80, TRUE,  '2025-06-20', '2025-06-20 19:47:00', 'Grandpa''s record 🎣', NULL),
    ('Tiddler',     NULL,            0.05, FALSE, '2025-06-21', '2025-06-21 08:00:00', 'Tiny', NULL);

-- A second table so \d shows more than one, and joins are possible.
CREATE TABLE lakes (
    id      INT PRIMARY KEY AUTO_INCREMENT,
    name    VARCHAR(80) NOT NULL,
    depth_m INT,
    stocked BOOLEAN DEFAULT TRUE
);

INSERT INTO lakes (name, depth_m, stocked) VALUES
    ('Clearwater Pond', 12,  TRUE),
    ('Old Mill Lake',   45,  TRUE),
    ('Secret Spot',     NULL, FALSE);

-- A view, to prove SHOW TABLES / DESCRIBE handle more than base tables.
CREATE VIEW favorite_fish AS
    SELECT name, species, weight_kg FROM fish WHERE is_favorite = TRUE;

SELECT 'grandpas_test is ready!' AS status;
