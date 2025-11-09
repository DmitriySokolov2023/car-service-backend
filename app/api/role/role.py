from flask import Blueprint, jsonify,request
from psycopg2.extras import RealDictCursor
import psycopg2
from config import CONNECT_DB
role_bp = Blueprint("role", __name__)

@role_bp.route("/get/custom", methods=["GET"])
def get_roles():
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name FROM public.roles ORDER BY id ASC")
            rows = cur.fetchall() or []
            result = [{"value": r["id"], "label": r["name"]} for r in rows]
            return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@role_bp.route("/get", methods=["GET"])
def get_roles_all():
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""SELECT * FROM public.roles ORDER BY id ASC""")  
            rows = cur.fetchall() 
            return jsonify({"items": rows}), 200
    except Exception as e:
        return jsonify({"error": e}), 500