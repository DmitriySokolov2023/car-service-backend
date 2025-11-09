from flask import Blueprint, jsonify,request
from psycopg2.extras import RealDictCursor
import psycopg2
from config import CONNECT_DB
employees_bp = Blueprint("employees", __name__)

@employees_bp.route("/get", methods=["GET"])
def get_employees():
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""SELECT * FROM public.employees ORDER BY id ASC""")  
            rows = cur.fetchall() 
            return jsonify({"items": rows}), 200
    except Exception as e:
        return jsonify({"error": e}), 500