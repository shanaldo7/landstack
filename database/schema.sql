-- ============================================
-- LAND STACK DEMO DATABASE
-- ============================================

-- ============================================
-- 1. DELETE OLD TABLES
-- ============================================

BEGIN
    FOR t IN (
        SELECT table_name
        FROM user_tables
        WHERE table_name IN (
            'REGISTRATION',
            'OWNERSHIP',
            'LAND_PARCELS'
        )
    ) LOOP
        EXECUTE IMMEDIATE
            'DROP TABLE "' || t.table_name || '" CASCADE CONSTRAINTS';
    END LOOP;
END;
/

-- ============================================
-- 2. CREATE LAND_PARCELS TABLE
-- ============================================

CREATE TABLE land_parcels (
    ulpin VARCHAR2(30) PRIMARY KEY,
    parcel_no VARCHAR2(30),
    district VARCHAR2(100),
    village VARCHAR2(100),
    state VARCHAR2(100),
    area_acres NUMBER(10,2),
    latitude NUMBER(10,6),
    longitude NUMBER(10,6),
    land_use VARCHAR2(50)
);

-- ============================================
-- 3. INSERT LAND PARCELS
-- ============================================

INSERT INTO land_parcels
VALUES (
    'ULPIN-WB-0001',
    'P-101',
    'Kolkata',
    'Demo Village',
    'West Bengal',
    2.50,
    22.572600,
    88.363900,
    'Residential'
);

INSERT INTO land_parcels
VALUES (
    'ULPIN-WB-0002',
    'P-102',
    'Kolkata',
    'Demo Village',
    'West Bengal',
    1.80,
    22.573000,
    88.364500,
    'Agricultural'
);

COMMIT;

-- ============================================
-- 4. CREATE OWNERSHIP TABLE
-- ============================================

CREATE TABLE ownership (
    ownership_id NUMBER PRIMARY KEY,
    ulpin VARCHAR2(30),
    owner_name VARCHAR2(100),
    ownership_status VARCHAR2(30),
    FOREIGN KEY (ulpin)
        REFERENCES land_parcels(ulpin)
);

-- ============================================
-- 5. INSERT OWNERS
-- ============================================

INSERT INTO ownership
VALUES (
    1,
    'ULPIN-WB-0001',
    'Rahul Sharma',
    'Verified'
);

INSERT INTO ownership
VALUES (
    2,
    'ULPIN-WB-0002',
    'Amit Das',
    'Verified'
);

COMMIT;

-- ============================================
-- 6. CREATE REGISTRATION TABLE
-- ============================================

CREATE TABLE registration (
    registration_id NUMBER PRIMARY KEY,
    ulpin VARCHAR2(30),
    registration_status VARCHAR2(30),
    transaction_type VARCHAR2(30),
    FOREIGN KEY (ulpin)
        REFERENCES land_parcels(ulpin)
);

-- ============================================
-- 7. INSERT REGISTRATION DATA
-- ============================================

INSERT INTO registration
VALUES (
    1,
    'ULPIN-WB-0001',
    'Registered',
    'Sale'
);

INSERT INTO registration
VALUES (
    2,
    'ULPIN-WB-0002',
    'Pending',
    'Sale'
);

COMMIT;

-- ============================================
-- 8. CHECK ALL DATA
-- ============================================

SELECT * FROM land_parcels;

SELECT * FROM ownership;

SELECT * FROM registration;

SELECT table_name
FROM user_tables
ORDER BY table_name;