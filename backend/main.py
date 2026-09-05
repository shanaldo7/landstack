from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import oracledb
import jwt


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="LandStack API",
    description="Integrated GIS-based Digital Public Infrastructure for Land Governance",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ORACLE CONFIGURATION
# ============================================================

ORACLE_CLIENT_PATH = r"E:\hackathon\oraclex64\instantclient_23_26"

oracledb.init_oracle_client(
    lib_dir=ORACLE_CLIENT_PATH
)


DB_USER = "scott"
DB_PASSWORD = "tiger"
DB_DSN = "localhost:1521/ORCL"


# ============================================================
# JWT CONFIGURATION
# ============================================================

SECRET_KEY = "LANDSTACK-SIH-2026-SECRET-CHANGE-LATER"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    return oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN
    )


# ============================================================
# MODELS
# ============================================================

class LoginRequest(BaseModel):

    username: str
    password: str


# ============================================================
# JWT TOKEN
# ============================================================

def create_access_token(
    username: str,
    role: str
):

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": username,
        "role": role,
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# ============================================================
# CURRENT USER
# ============================================================

def get_current_user(
    authorization: str = Header(None)
):

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail="Authorization header missing"
        )

    if not authorization.startswith("Bearer "):

        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format"
        )

    token = authorization.split(
        " ",
        1
    )[1]

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")
        role = payload.get("role")

        if not username or not role:

            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        return {
            "username": username,
            "role": role
        }

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=401,
            detail="Token expired"
        )

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


# ============================================================
# ROLE CHECK
# ============================================================

def require_roles(*allowed_roles):

    def role_checker(
        current_user=Depends(get_current_user)
    ):

        if current_user["role"] not in allowed_roles:

            raise HTTPException(
                status_code=403,
                detail="Access denied for this role"
            )

        return current_user

    return role_checker


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "message": "LandStack API is running"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# ============================================================
# TEST DATABASE
# ============================================================

@app.get("/test-db")
def test_db():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "SELECT COUNT(*) FROM LAND_PARCELS"
        )

        count = cursor.fetchone()[0]

        return {
            "database": "connected",
            "land_parcels_count": count
        }

    finally:

        cursor.close()
        conn.close()


# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
def login(
    login_data: LoginRequest
):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT username, role, active
            FROM USERS
            WHERE username = :username
            AND password = :password
            """,
            {
                "username": login_data.username,
                "password": login_data.password
            }
        )

        row = cursor.fetchone()

        if not row:

            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )

        username = row[0]
        role = row[1]
        active = row[2]

        if active != 1:

            raise HTTPException(
                status_code=403,
                detail="User account is inactive"
            )

        token = create_access_token(
            username,
            role
        )

        return {
            "success": True,
            "message": "Login successful",
            "username": username,
            "role": role,
            "access_token": token,
            "token_type": "bearer"
        }

    finally:

        cursor.close()
        conn.close()


# ============================================================
# ME
# ============================================================

@app.get("/me")
def me(
    current_user=Depends(
        require_roles(
            "CITIZEN",
            "OFFICER",
            "ADMIN"
        )
    )
):

    return current_user


# ============================================================
# SEARCH PARCEL
# ============================================================

@app.get("/search")
def search(
    term: str,
    current_user=Depends(
        require_roles(
            "CITIZEN",
            "OFFICER",
            "ADMIN"
        )
    )
):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        search_term = f"%{term}%"

        cursor.execute(
            """
            SELECT
                p.ULPIN,
                p.PARCEL_NO,
                p.DISTRICT,
                p.VILLAGE,
                p.STATE,
                p.AREA_ACRES,
                p.LATITUDE,
                p.LONGITUDE,
                p.LAND_USE,

                o.OWNER_NAME,
                o.OWNERSHIP_STATUS,

                r.REGISTRATION_STATUS,
                r.TRANSACTION_TYPE

            FROM LAND_PARCELS p

            LEFT JOIN OWNERSHIP o
                ON p.ULPIN = o.ULPIN

            LEFT JOIN REGISTRATION r
                ON p.ULPIN = r.ULPIN

            WHERE
                UPPER(p.ULPIN)
                    LIKE UPPER(:term)

                OR UPPER(p.PARCEL_NO)
                    LIKE UPPER(:term)

                OR UPPER(p.DISTRICT)
                    LIKE UPPER(:term)

                OR UPPER(p.VILLAGE)
                    LIKE UPPER(:term)

                OR UPPER(o.OWNER_NAME)
                    LIKE UPPER(:term)

            AND ROWNUM <= 10
            """,
            {
                "term": search_term
            }
        )

        rows = cursor.fetchall()

        results = []

        for row in rows:

            results.append({

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

                "tax_status": ""

            })

        return {
            "data": results
        }

    finally:

        cursor.close()
        conn.close()


# ============================================================
# SINGLE PARCEL
# ============================================================

@app.get("/parcel/{ulpin}")
def get_parcel(
    ulpin: str,
    current_user=Depends(
        require_roles(
            "CITIZEN",
            "OFFICER",
            "ADMIN"
        )
    )
):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                p.ULPIN,
                p.PARCEL_NO,
                p.DISTRICT,
                p.VILLAGE,
                p.STATE,
                p.AREA_ACRES,
                p.LATITUDE,
                p.LONGITUDE,
                p.LAND_USE,

                o.OWNER_NAME,
                o.OWNERSHIP_STATUS,

                r.REGISTRATION_STATUS,
                r.TRANSACTION_TYPE

            FROM LAND_PARCELS p

            LEFT JOIN OWNERSHIP o
                ON p.ULPIN = o.ULPIN

            LEFT JOIN REGISTRATION r
                ON p.ULPIN = r.ULPIN

            WHERE p.ULPIN = :ulpin
            """,
            {
                "ulpin": ulpin
            }
        )

        row = cursor.fetchone()

        if not row:

            raise HTTPException(
                status_code=404,
                detail="Land parcel not found"
            )

        return {

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

            "tax_status": ""

        }

    finally:

        cursor.close()
        conn.close()


# ============================================================
# CITIZEN DASHBOARD
# ============================================================

@app.get("/citizen/dashboard")
def citizen_dashboard(
    current_user=Depends(
        require_roles("CITIZEN")
    )
):

    return {

        "message": "Welcome to Citizen Dashboard",

        "username": current_user["username"],

        "role": current_user["role"],

        "permissions": [
            "Search land records",
            "View ownership",
            "View registration status"
        ]

    }


# ============================================================
# OFFICER DASHBOARD
# ============================================================

@app.get("/officer/dashboard")
def officer_dashboard(
    current_user=Depends(
        require_roles(
            "OFFICER",
            "ADMIN"
        )
    )
):

    return {

        "message": "Welcome to Officer Dashboard",

        "username": current_user["username"],

        "role": current_user["role"],

        "permissions": [
            "Parcel management",
            "Ownership management",
            "Registration management",
            "Planning",
            "Land risk",
            "GIS and satellite analysis"
        ]

    }


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.get("/admin/dashboard")
def admin_dashboard(
    current_user=Depends(
        require_roles("ADMIN")
    )
):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # --------------------------------------------
        # TOTAL LAND PARCELS
        # --------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM LAND_PARCELS
            """
        )

        total_parcels = cursor.fetchone()[0]


        # --------------------------------------------
        # VERIFIED OWNERS
        # --------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM OWNERSHIP
            WHERE UPPER(OWNERSHIP_STATUS) = 'VERIFIED'
            """
        )

        verified_owners = cursor.fetchone()[0]


        # --------------------------------------------
        # REGISTRATIONS
        # --------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM REGISTRATION
            """
        )

        registrations = cursor.fetchone()[0]


        # --------------------------------------------
        # ACTIVE USERS
        # --------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM USERS
            WHERE ACTIVE = 1
            """
        )

        active_users = cursor.fetchone()[0]


        return {

            "message": "Welcome to Admin Dashboard",

            "username": current_user["username"],

            "role": current_user["role"],

            "total_land_parcels": total_parcels,

            "verified_owners": verified_owners,

            "registrations": registrations,

            "active_users": active_users,

            "permissions": [

                "Full system access",

                "User management",

                "Role management",

                "System administration",

                "Audit management"

            ]

        }

    finally:

        cursor.close()
        conn.close()


# ============================================================
# ADMIN USERS
# ============================================================

@app.get("/admin/users")
def admin_users(
    current_user=Depends(
        require_roles("ADMIN")
    )
):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                USER_ID,
                USERNAME,
                ROLE,
                ACTIVE
            FROM USERS
            ORDER BY USER_ID
            """
        )

        rows = cursor.fetchall()

        users = []

        for row in rows:

            users.append({

                "user_id": row[0],

                "username": row[1],

                "role": row[2],

                "active": row[3]

            })

        return {
            "data": users
        }

    finally:

        cursor.close()
        conn.close()