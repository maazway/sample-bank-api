from fastapi import FastAPI, HTTPException
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

class Nasabah(BaseModel):
    nama: str
    no_ktp: str
    email: str
    phone: str
    alamat: str

@app.get("/")
def root():
    return {"message": "API is running"}

@app.get("/nasabah")
def get_nasabah():
    cur = conn.cursor()
    cur.execute("SELECT * FROM nasabah")
    rows = cur.fetchall()
    cur.close()
    return rows

@app.post("/nasabah")
def add_nasabah(data: Nasabah):
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO nasabah (nama, no_ktp, email, phone, alamat) VALUES (%s, %s, %s, %s, %s)",
                    (data.nama, data.no_ktp, data.email, data.phone, data.alamat))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
    return {"message": "Nasabah ditambahkan"}

@app.delete("/nasabah/{no_ktp}")
def delete_nasabah(no_ktp: str):
    cur = conn.cursor()
    cur.execute("DELETE FROM nasabah WHERE no_ktp = %s", (no_ktp,))
    conn.commit()
    cur.close()
    return {"message": f"Nasabah dengan KTP {no_ktp} dihapus"}
