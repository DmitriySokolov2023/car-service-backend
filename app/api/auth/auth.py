from flask import Blueprint, jsonify,request
import psycopg2
from config import CONNECT_DB
auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def auth():
    data = request.get_json(silent=True) or {}
    print(data)
    login = data.get("login")
    password = data.get("password")

    if not login or not password:
        return jsonify({"error": "login и password обязательны"}), 400

    try:
        with psycopg2.connect(CONNECT_DB) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, login, password
                    FROM public.users
                    WHERE login = %s AND password = %s
                    LIMIT 1
                """, (login, password))
                row = cur.fetchone()
    except Exception as e:
        return jsonify({"error": e}), 500

    if row:
        user_id, user_login, user_password = row
        return jsonify({
            "auth": True,
            "user": {"id": user_id, "login": user_login, "password": user_password}
        }), 200
    else:
        return jsonify({"auth": False}), 401