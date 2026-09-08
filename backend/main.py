from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import oracledb
import jwt
import json
import urllib.request
import urllib.error
import os
from dotenv import load_dotenv

load_dotenv()
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")


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
        authorization: str = Header(None)
    ):


        if not authorization:

            raise HTTPException(
                status_code=401,
                detail="Authorization header missing"
            )

        if not authorization.startswith(
            "Bearer "
        ):

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

            if role not in allowed_roles:

                raise HTTPException(
                    status_code=403,
                    detail="Access denied for this role"
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

        # Accept both frontend demo ULPINs (WB000001)
        # and database ULPINs (ULPIN-WB-0001).
        normalized_term = term.strip().upper()

        if normalized_term.startswith("WB") and normalized_term[2:].isdigit():
            normalized_term = "ULPIN-WB-" + normalized_term[2:].zfill(4)

        search_term = f"%{normalized_term}%"

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

                OR UPPER(p.OWNER_NAME)
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
# CITIZEN SERVICE MODELS
# ============================================================
class TaxPaymentRequest(BaseModel):
    tax_id: int


class RegistrationApplicationRequest(BaseModel):
    ulpin: str
    transaction_type: str
    buyer_name: str
    buyer_mobile: str
    buyer_address: str
    document_name: str = ""


# ============================================================
# AI LAND GOVERNANCE ASSISTANT
# ============================================================
class AIChatRequest(BaseModel):
    message: str
    ulpin: str = ""


@app.post("/ai/chat")
def ai_chat(
    chat_data: AIChatRequest,
    current_user=Depends(require_roles("CITIZEN", "OFFICER", "ADMIN"))
):
    message = chat_data.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if len(message) > 1000:
        raise HTTPException(status_code=400, detail="Message is too long")

    parcel_context = "No parcel selected."

    if chat_data.ulpin.strip():
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT p.ULPIN, p.PARCEL_NO, p.DISTRICT, p.VILLAGE,
                       p.STATE, p.AREA_ACRES, p.LAND_USE,
                       o.OWNER_NAME, o.OWNERSHIP_STATUS,
                       r.REGISTRATION_STATUS, r.TRANSACTION_TYPE
                FROM LAND_PARCELS p
                LEFT JOIN OWNERSHIP o ON p.ULPIN = o.ULPIN
                LEFT JOIN REGISTRATION r ON p.ULPIN = r.ULPIN
                WHERE UPPER(p.ULPIN) = UPPER(:ulpin)
                """,
                {"ulpin": chat_data.ulpin.strip()}
            )
            row = cursor.fetchone()
            if row:
                parcel_context = (
                    f"ULPIN: {row[0]}\n"
                    f"Survey/Parcel No: {row[1]}\n"
                    f"District: {row[2]}\n"
                    f"Village: {row[3]}\n"
                    f"State: {row[4]}\n"
                    f"Area (acres): {row[5]}\n"
                    f"Land use: {row[6]}\n"
                    f"Owner: {row[7] or 'Not available'}\n"
                    f"Ownership status: {row[8] or 'Not available'}\n"
                    f"Registration status: {row[9] or 'Not available'}\n"
                    f"Transaction type: {row[10] or 'Not available'}"
                )
            else:
                parcel_context = "The selected ULPIN was not found in the database."
        finally:
            cursor.close()
            conn.close()

    prompt = f"""You are LandStack AI, an assistant for a digital land governance platform.
Answer clearly and briefly. Use only the supplied database context for parcel-specific facts.
Do not invent ownership, legal status, fees, dates, zoning rules, or government decisions.
If information is unavailable, say so. For legal matters, explain that the answer is informational and the competent revenue/registration authority should be consulted.

Parcel context:
{parcel_context}

User question:
{message}

Give a concise answer suitable for a citizen or land officer."""

    if not OLLAMA_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Ollama API key is not configured."
        )

    payload = json.dumps({
        "model": "gpt-oss:120b",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://ollama.com/api/chat",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OLLAMA_API_KEY}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))

        answer = result.get("message", {}).get("content", "").strip()

        if not answer:
            raise HTTPException(
                status_code=502,
                detail="AI returned an empty response"
            )

        return {
            "success": True,
            "answer": answer
        }

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        raise HTTPException(
            status_code=502,
            detail=f"Ollama Cloud request failed: {error_body}"
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to connect to Ollama Cloud: {error.reason}"
        )

    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Ollama Cloud response timed out."
        )



# ============================================================
# CITIZEN TAX SERVICES
# ============================================================
@app.get("/citizen/taxes/{ulpin}")
def citizen_tax_details(
    ulpin: str,
    current_user=Depends(require_roles("CITIZEN"))
):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT TAX_ID, ULPIN, TAX_YEAR, AMOUNT_DUE,
                   DUE_DATE, STATUS, PAYMENT_ID, PAID_AT
            FROM TAX_DUES
            WHERE ULPIN = :ulpin
            ORDER BY TAX_YEAR DESC
            """,
            {"ulpin": ulpin}
        )
        rows = cursor.fetchall()
        taxes = []
        for row in rows:
            taxes.append({
                "tax_id": row[0],
                "ulpin": row[1],
                "tax_year": row[2],
                "amount_due": float(row[3]),
                "due_date": row[4].strftime("%Y-%m-%d") if row[4] else None,
                "status": row[5],
                "payment_id": row[6],
                "paid_at": row[7].isoformat() if row[7] else None
            })
        return {"data": taxes}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# CITIZEN TAX PAYMENT - DEMO PAYMENT WORKFLOW
# ============================================================
@app.post("/citizen/taxes/pay")
def citizen_pay_tax(
    payment_data: TaxPaymentRequest,
    current_user=Depends(require_roles("CITIZEN"))
):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT TAX_ID, ULPIN, AMOUNT_DUE, STATUS
            FROM TAX_DUES
            WHERE TAX_ID = :tax_id
            """,
            {"tax_id": payment_data.tax_id}
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tax record not found")

        tax_id, ulpin, amount, status = row
        if str(status).upper() == "PAID":
            raise HTTPException(status_code=400, detail="This tax has already been paid")

        payment_id = "PAY-" + datetime.now().strftime("%Y%m%d%H%M%S%f")[:20] + "-" + str(tax_id)

        cursor.execute(
            """
            UPDATE TAX_DUES
            SET STATUS = 'PAID',
                PAYMENT_ID = :payment_id,
                PAID_AT = CURRENT_TIMESTAMP
            WHERE TAX_ID = :tax_id
            """,
            {"payment_id": payment_id, "tax_id": tax_id}
        )
        conn.commit()

        return {
            "success": True,
            "message": "Tax payment successful",
            "payment_id": payment_id,
            "ulpin": ulpin,
            "amount": float(amount),
            "status": "PAID"
        }
    finally:
        cursor.close()
        conn.close()


# ============================================================
# ONLINE LAND REGISTRATION
# ============================================================
@app.post("/citizen/registrations")
def submit_registration(
    application: RegistrationApplicationRequest,
    current_user=Depends(require_roles("CITIZEN"))
):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT ULPIN FROM LAND_PARCELS WHERE ULPIN = :ulpin",
            {"ulpin": application.ulpin}
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Land parcel not found")

        cursor.execute(
            """
            SELECT OWNER_NAME, OWNERSHIP_STATUS
            FROM OWNERSHIP
            WHERE ULPIN = :ulpin
            """,
            {"ulpin": application.ulpin}
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Ownership record not found")

        fees = {
            "SALE": 5000,
            "GIFT": 2500,
            "LEASE": 3000,
            "TRANSFER": 3500,
            "MORTGAGE": 4000
        }
        transaction_type = application.transaction_type.upper()
        registration_fee = fees.get(transaction_type, 5000)

        application_id = "REG-2026-" + datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]

        cursor.execute(
            """
            INSERT INTO REGISTRATION_APPLICATIONS
            (
                APPLICATION_ID, ULPIN, APPLICANT_USERNAME,
                TRANSACTION_TYPE, BUYER_NAME, BUYER_MOBILE,
                BUYER_ADDRESS, DOCUMENT_NAME, REGISTRATION_FEE,
                STATUS, CREATED_AT
            )
            VALUES
            (
                :application_id, :ulpin, :applicant_username,
                :transaction_type, :buyer_name, :buyer_mobile,
                :buyer_address, :document_name, :registration_fee,
                'SUBMITTED', CURRENT_TIMESTAMP
            )
            """,
            {
                "application_id": application_id,
                "ulpin": application.ulpin,
                "applicant_username": current_user["username"],
                "transaction_type": application.transaction_type,
                "buyer_name": application.buyer_name,
                "buyer_mobile": application.buyer_mobile,
                "buyer_address": application.buyer_address,
                "document_name": application.document_name,
                "registration_fee": registration_fee
            }
        )
        conn.commit()

        return {
            "success": True,
            "message": "Registration application submitted",
            "application_id": application_id,
            "ulpin": application.ulpin,
            "transaction_type": application.transaction_type,
            "registration_fee": registration_fee,
            "status": "SUBMITTED"
        }
    finally:
        cursor.close()
        conn.close()


# ============================================================
# TRACK CITIZEN REGISTRATION APPLICATIONS
# ============================================================
@app.get("/citizen/registrations")
def get_citizen_registrations(
    current_user=Depends(require_roles("CITIZEN"))
):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT APPLICATION_ID, ULPIN, TRANSACTION_TYPE,
                   BUYER_NAME, BUYER_MOBILE, BUYER_ADDRESS,
                   DOCUMENT_NAME, REGISTRATION_FEE, STATUS, CREATED_AT
            FROM REGISTRATION_APPLICATIONS
            WHERE APPLICANT_USERNAME = :username
            ORDER BY CREATED_AT DESC
            """,
            {"username": current_user["username"]}
        )
        rows = cursor.fetchall()
        applications = []
        for row in rows:
            applications.append({
                "application_id": row[0],
                "ulpin": row[1],
                "transaction_type": row[2],
                "buyer_name": row[3],
                "buyer_mobile": row[4],
                "buyer_address": row[5],
                "document_name": row[6],
                "registration_fee": float(row[7]),
                "status": row[8],
                "created_at": row[9].isoformat() if row[9] else None
            })
        return {"data": applications}
    finally:
        cursor.close()
        conn.close()


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