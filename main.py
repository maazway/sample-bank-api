from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Koneksi PostgreSQL
conn = psycopg2.connect(
    host=os.getenv("PG_HOST"),
    database=os.getenv("PG_DB"),
    user=os.getenv("PG_USER"),
    password=os.getenv("PG_PASSWORD"),
    port=os.getenv("PG_PORT")
)

# Model input data nasabah
class Nasabah(BaseModel):
    nama: str
    no_ktp: str
    email: str
    phone: str
    alamat: str

# Root endpoint
@app.get("/")
def root():
    return {"message": "API is running"}

# Endpoint fleksibel untuk ambil data nasabah
@app.get("/nasabah")
def get_nasabah(fields: str = Query(default=None), no_ktp: str = Query(default=None)):
    cur = conn.cursor()

    # Pilih kolom (default '*')
    if fields:
        try:
            columns = ", ".join([f.strip() for f in fields.split(",")])
        except:
            raise HTTPException(status_code=400, detail="Format 'fields' tidak valid")
    else:
        columns = "*"

    # Filter by no_ktp jika ada
    if no_ktp:
        query = f"SELECT {columns} FROM nasabah WHERE no_ktp = %s"
        cur.execute(query, (no_ktp,))
    else:
        query = f"SELECT {columns} FROM nasabah"
        cur.execute(query)

    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    cur.close()

    return [dict(zip(colnames, row)) for row in rows]

# Tambah data nasabah baru
@app.post("/nasabah")
def add_nasabah(data: Nasabah):
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO nasabah (nama, no_ktp, email, phone, alamat) VALUES (%s, %s, %s, %s, %s)",
            (data.nama, data.no_ktp, data.email, data.phone, data.alamat)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
    return {"message": "Nasabah ditambahkan"}

# Hapus nasabah berdasarkan no_ktp
@app.delete("/nasabah/{no_ktp}")
def delete_nasabah(no_ktp: str):
    cur = conn.cursor()
    cur.execute("DELETE FROM nasabah WHERE no_ktp = %s", (no_ktp,))
    conn.commit()
    cur.close()
    return {"message": f"Nasabah dengan KTP {no_ktp} dihapus"}
