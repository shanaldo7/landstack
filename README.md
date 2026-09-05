to run the app you need 
https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html?utm_source=chatgpt.com  first normal one then
(download oracle for database here normal one then this Download	Details
Basic Package
instantclient-basic-windows.x64-23.26.3.0.0.zip

143,794,194 bytes (checksum = 2489869853)

SHA256 4c7fe8a77f6b9a00d57214ffda241f14f79dad5774a8f53073b7497e54b51763

Review the Operating System Checklist for Oracle Database Client Installation. Note Windows 7 is not supported.
The 23.26 Basic package requires the latest Microsoft Visual C++ Redistributable package common for Visual Studio 2015, 2017, 2019, and 2022)


python download 3.14.7(64-bit version)

# 🏞️ LandStack

## An Integrated GIS-based Digital Public Infrastructure for Land Governance

LandStack is a prototype system for managing and viewing land parcel information using:

- HTML, CSS and JavaScript
- FastAPI
- Python
- Oracle Database
- Leaflet Map

The system allows users to search for a land parcel using its ULPIN, survey number, owner name or village and view its land information.

---

# 📁 Project Structure

landstack/
│
├── backend/
│   ├── main.py
│   └── requirements.txt
│
├── database/
│   └── schema.sql
│
├── ui/
│   └── index.html
│
└── LandStack_COMPLETE_SETUP_GUIDE

uvicorn main:app --reload command to start the server (important)

pips needed
fastapi
uvicorn
oracledb


