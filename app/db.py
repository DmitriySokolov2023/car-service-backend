# app/db.py
from psycopg2 import pool
from config import CONNECT_DB

# Создаем пул соединений
db_pool = pool.SimpleConnectionPool(
    minconn=5,   
    maxconn=50,  
    dsn=CONNECT_DB
)

if not db_pool:
    raise Exception("Не удалось создать пул соединений PostgreSQL")