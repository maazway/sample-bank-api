from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
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
@app.post("/nasabah", status_code=201)
def add_nasabah(data: Nasabah):
    cur = conn.cursor()
    try:
        # Cek apakah no_ktp sudah ada
        cur.execute("SELECT * FROM nasabah WHERE no_ktp = %s", (data.no_ktp,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="KTP sudah terdaftar")

        cur.execute(
            "INSERT INTO nasabah (nama, no_ktp, email, phone, alamat) VALUES (%s, %s, %s, %s, %s)",
            (data.nama, data.no_ktp, data.email, data.phone, data.alamat)
        )
        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "Nasabah berhasil ditambahkan"})

# Hapus nasabah berdasarkan no_ktp
@app.delete("/nasabah/{no_ktp}")
def delete_nasabah(no_ktp: str):
    cur = conn.cursor()
    cur.execute("SELECT * FROM nasabah WHERE no_ktp = %s", (no_ktp,))
    if not cur.fetchone():
        cur.close()
        raise HTTPException(status_code=404, detail=f"Nasabah dengan KTP {no_ktp} tidak ditemukan")

    cur.execute("DELETE FROM nasabah WHERE no_ktp = %s", (no_ktp,))
    conn.commit()
    cur.close()
    return {"message": f"Nasabah dengan KTP {no_ktp} dihapus"}

# Update data nasabah berdasarkan no_ktp
@app.put("/nasabah/{no_ktp}")
def update_nasabah(no_ktp: str, data: Nasabah):
    cur = conn.cursor()
    cur.execute("SELECT * FROM nasabah WHERE no_ktp = %s", (no_ktp,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Nasabah tidak ditemukan")

    cur.execute(
        "UPDATE nasabah SET nama=%s, email=%s, phone=%s, alamat=%s WHERE no_ktp=%s",
        (data.nama, data.email, data.phone, data.alamat, no_ktp)
    )
    conn.commit()
    cur.close()
    return {"message": f"Nasabah dengan KTP {no_ktp} berhasil diperbarui"}

# Model rekening & transaksi
class Rekening(BaseModel):
    no_rekening: str
    no_ktp: str
    saldo: int = 0

class Transaksi(BaseModel):
    no_rekening: str
    jenis: str  # "debit" atau "kredit"
    jumlah: int

# Get semua rekening
@app.get("/rekening")
def get_rekening():
    cur = conn.cursor()
    cur.execute("SELECT * FROM rekening")
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    cur.close()
    return [dict(zip(colnames, row)) for row in rows]

# Tambah rekening
@app.post("/rekening")
def add_rekening(data: Rekening):
    cur = conn.cursor()
    try:
        # Cek duplikasi
        cur.execute("SELECT * FROM rekening WHERE no_rekening = %s", (data.no_rekening,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Nomor rekening sudah terdaftar")

        cur.execute(
            "INSERT INTO rekening (no_rekening, no_ktp, saldo) VALUES (%s, %s, %s)",
            (data.no_rekening, data.no_ktp, data.saldo)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
    return {"message": "Rekening berhasil ditambahkan"}

# Tambah transaksi (otomatis update saldo)
@app.post("/transaksi")
def add_transaksi(data: Transaksi):
    if data.jenis not in ["debit", "kredit"]:
        raise HTTPException(status_code=400, detail="Jenis harus 'debit' atau 'kredit'")

    cur = conn.cursor()
    try:
        # Ambil id & saldo dari no_rekening
        cur.execute("SELECT id, saldo FROM rekening WHERE no_rekening = %s", (data.no_rekening,))
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Rekening tidak ditemukan")

        id_rekening, saldo = result

        # Hitung saldo baru
        if data.jenis == "debit":
            saldo += data.jumlah
        elif data.jenis == "kredit":
            if data.jumlah > saldo:
                raise HTTPException(status_code=400, detail="Saldo tidak cukup")
            saldo -= data.jumlah

        # Insert transaksi
        cur.execute(
            "INSERT INTO transaksi (id_rekening, jenis, jumlah, timestamp) VALUES (%s, %s, %s, NOW())",
            (id_rekening, data.jenis, data.jumlah)
        )

        # Update saldo
        cur.execute("UPDATE rekening SET saldo = %s WHERE id = %s", (saldo, id_rekening))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()

    return {"message": "Transaksi berhasil"}
