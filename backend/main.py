from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import oracledb


# ============================================================
# ORACLE INSTANT CLIENT
# ============================================================

ORACLE_CLIENT_PATH = r"E:\hackathon\oraclex64\instantclient_23_26"

oracledb.init_oracle_client(
    lib_dir=ORACLE_CLIENT_PATH
)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="Land Stack API",
    version="1.0.0"
)


# ============================================================
# CORS
# Allows your HTML frontend to communicate with FastAPI
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ORACLE CONNECTION
# ============================================================

def get_connection():
    return oracledb.connect(
        user="scott",
        password="tiger",
        dsn="localhost:1521/ORCL"
    )


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "message": "Land Stack API is running"
    }


# ============================================================
# TEST DATABASE
# ============================================================

@app.get("/test-db")
def test_database():

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM land_parcels"
        )

        count = cursor.fetchone()[0]

        return {
            "database": "connected",
            "land_parcels_count": count
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# SEARCH
#
# Used by your index.html:
# /search?term=ULPIN-WB-0001
#
# Searches:
# - ULPIN
# - Parcel / survey number
# - Owner name
# - Village
# ============================================================

@app.get("/search")
def search_parcels(term: str):

    search_term = term.strip()

    if not search_term:
        return {
            "data": []
        }

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor()

        query = """
            SELECT
                lp.ulpin,
                lp.parcel_no,
                lp.district,
                lp.village,
                lp.state,
                lp.area_acres,
                lp.latitude,
                lp.longitude,
                lp.land_use,
                o.owner_name,
                o.ownership_status,
                r.registration_status,
                r.transaction_type
            FROM land_parcels lp

            LEFT JOIN ownership o
                ON lp.ulpin = o.ulpin

            LEFT JOIN registration r
                ON lp.ulpin = r.ulpin

            WHERE
                UPPER(lp.ulpin) = UPPER(:term)
                OR UPPER(lp.parcel_no) = UPPER(:term)
                OR UPPER(o.owner_name) LIKE UPPER(:owner_term)
                OR UPPER(lp.village) LIKE UPPER(:village_term)

            AND ROWNUM <= 10
        """

        cursor.execute(
            query,
            {
                "term": search_term,
                "owner_term": f"%{search_term}%",
                "village_term": f"%{search_term}%"
            }
        )

        rows = cursor.fetchall()

        data = []

        for row in rows:

            data.append({
                "ulpin": row[0],
                "survey_number": row[1],
                "district": row[2],
                "village": row[3],
                "state": row[4],

                "area": row[5],

                "latitude": row[6],
                "longitude": row[7],

                "land_use": row[8],

                "owner_name": row[9] or "",
                "ownership_status": row[10] or "",

                "registration_status": row[11] or "",
                "transaction_type": row[12] or "",

                # Tax table doesn't exist yet
                "tax_status": ""
            })

        return {
            "data": data
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# GET ONE PARCEL
#
# Example:
# /parcel/ULPIN-WB-0001
# ============================================================

@app.get("/parcel/{ulpin}")
def get_parcel(ulpin: str):

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor()

        query = """
            SELECT
                ulpin,
                parcel_no,
                district,
                village,
                state,
                area_acres,
                latitude,
                longitude,
                land_use
            FROM land_parcels
            WHERE UPPER(ulpin) = UPPER(:ulpin)
        """

        cursor.execute(
            query,
            {
                "ulpin": ulpin.strip()
            }
        )

        row = cursor.fetchone()

        if row is None:

            raise HTTPException(
                status_code=404,
                detail="Parcel not found"
            )

        return {
            "ulpin": row[0],
            "parcel_no": row[1],
            "district": row[2],
            "village": row[3],
            "state": row[4],
            "area_acres": row[5],
            "latitude": row[6],
            "longitude": row[7],
            "land_use": row[8]
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }