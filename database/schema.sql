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