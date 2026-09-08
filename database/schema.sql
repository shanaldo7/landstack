-- ============================================
-- LAND STACK USERS - CLEAN RESET
-- ============================================

-- Delete existing USERS table if it exists
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE users CASCADE CONSTRAINTS';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -942 THEN
            RAISE;
        END IF;
END;
/

-- Create USERS table
CREATE TABLE users (
    user_id NUMBER PRIMARY KEY,
    username VARCHAR2(50) UNIQUE NOT NULL,
    password VARCHAR2(100) NOT NULL,
    role VARCHAR2(30) NOT NULL,
    active NUMBER(1) DEFAULT 1
);

-- Create Officer account
INSERT INTO users
(user_id, username, password, role, active)
VALUES
(1, 'officer', 'officer123', 'OFFICER', 1);

-- Create Admin account
INSERT INTO users
(user_id, username, password, role, active)
VALUES
(2, 'admin', 'admin123', 'ADMIN', 1);

-- Create Citizen account
INSERT INTO users
(user_id, username, password, role, active)
VALUES
(3, 'citizen', 'citizen123', 'CITIZEN', 1);

-- Save changes
COMMIT;

-- Verify users
SELECT user_id, username, role, active
FROM users
ORDER BY user_id;
-- Remove officer if an incomplete/old officer record exists
DELETE FROM users
WHERE username = 'officer'
   OR user_id = 1;

-- Create officer account
INSERT INTO users
(user_id, username, password, role, active)
VALUES
(1, 'officer', 'officer123', 'OFFICER', 1);

COMMIT;

-- Check all users
SELECT user_id, username, role, active
FROM users
ORDER BY user_id;
SELECT user_id, username, role, active
FROM users
ORDER BY user_id;
SELECT username, role, active
FROM users
WHERE username = 'admin';


SELECT a.table_name,
       a.constraint_name,
       a.r_constraint_name
FROM user_constraints a
WHERE a.constraint_type = 'R'
AND a.r_constraint_name IN (
    SELECT constraint_name
    FROM user_constraints
    WHERE table_name = 'LAND_PARCELS'
);

SELECT table_name
FROM user_tables
ORDER BY table_name;
DESC land_parcels;
DESC users;
DESC transactions;          -- if it exists
DESC service_requests;      -- if it exists
DESC department_links;      -- or any cross-dept table
DESC ror;                   -- if you have a separate RoR table
DESC parcel_details;        -- or similar
SELECT table_name
FROM user_tables
ORDER BY table_name;
DESC OWNERSHIP;
DESC REGISTRATION;
SELECT table_name
FROM user_tables
WHERE UPPER(table_name) LIKE '%ENCUM%'
   OR UPPER(table_name) LIKE '%MORTG%';
   SELECT * FROM LAND_PARCELS;
   SELECT COUNT(*) FROM LAND_PARCELS;
   SELECT COUNT(*) FROM OWNERSHIP;
   SELECT ULPIN, OWNER_NAME, OWNERSHIP_STATUS
FROM OWNERSHIP;
CREATE TABLE TAX_DUES (
    TAX_ID NUMBER PRIMARY KEY,
    ULPIN VARCHAR2(30) NOT NULL,
    TAX_YEAR NUMBER(4) NOT NULL,
    AMOUNT_DUE NUMBER(12,2) NOT NULL,
    DUE_DATE DATE,
    STATUS VARCHAR2(20) DEFAULT 'PENDING' NOT NULL,
    PAYMENT_ID VARCHAR2(40),
    PAID_AT TIMESTAMP
);
CREATE TABLE REGISTRATION_APPLICATIONS (
    APPLICATION_ID VARCHAR2(30) PRIMARY KEY,
    ULPIN VARCHAR2(30) NOT NULL,
    APPLICANT_USERNAME VARCHAR2(100) NOT NULL,
    TRANSACTION_TYPE VARCHAR2(30) NOT NULL,
    BUYER_NAME VARCHAR2(100) NOT NULL,
    BUYER_MOBILE VARCHAR2(20) NOT NULL,
    BUYER_ADDRESS VARCHAR2(500) NOT NULL,
    DOCUMENT_NAME VARCHAR2(255),
    REGISTRATION_FEE NUMBER(12,2) NOT NULL,
    STATUS VARCHAR2(30) DEFAULT 'SUBMITTED' NOT NULL,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);
INSERT INTO TAX_DUES
(TAX_ID, ULPIN, TAX_YEAR, AMOUNT_DUE, DUE_DATE, STATUS)
VALUES
(1, 'ULPIN-WB-0001', 2026, 2500, DATE '2026-09-30', 'PENDING');

COMMIT;
SELECT * FROM TAX_DUES;
SELECT * FROM REGISTRATION_APPLICATIONS;
SELECT * FROM TAX_DUES;
INSERT INTO TAX_DUES
(TAX_ID, ULPIN, TAX_YEAR, AMOUNT_DUE, DUE_DATE, STATUS)
VALUES
(1, 'ULPIN-WB-0001', 2026, 2500, DATE '2026-09-30', 'PENDING');

COMMIT;
CONNECT scott/tiger
INSERT INTO TAX_DUES
VALUES (1, 'ULPIN-WB-0001', 2026, 2500, DATE '2026-09-30', 'PENDING', NULL, NULL);
COMMIT;
SELECT TAX_ID, ULPIN, TAX_YEAR, AMOUNT_DUE, DUE_DATE, STATUS
FROM TAX_DUES;
SELECT TAX_ID, ULPIN, TAX_YEAR, AMOUNT_DUE, DUE_DATE, STATUS
FROM TAX_DUES
WHERE ULPIN = 'ULPIN-WB-0001';