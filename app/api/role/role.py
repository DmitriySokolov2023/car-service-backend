from flask import Blueprint, jsonify,request
from psycopg2.extras import RealDictCursor
import psycopg2
from config import CONNECT_DB
from psycopg2 import errorcodes

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
    

# POST: создать роль  (name обязателен, description опционален)
@role_bp.route("/create", methods=["POST"])
def create_role():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    description = description if description != "" else None

    if not name:
        return jsonify({"error": "name обязателен"}), 400

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO public.roles (name, description)
                VALUES (%s, %s)
                RETURNING id, name, description;
            """, (name, description))
            row = cur.fetchone()
            return jsonify({"item": row}), 201
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == errorcodes.UNIQUE_VIOLATION:
            return jsonify({"error": "Роль с таким name уже существует"}), 409
        return jsonify({"error": "db error"}), 500


# PUT/PATCH: обновить роль по id
@role_bp.route("/update/<int:role_id>", methods=["PUT", "PATCH"])
def update_role(role_id: int):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    # если description не передан — оставим как было; если передан пустой — очистим до NULL
    desc_passed = "description" in data
    description = (None if description == "" else description) if desc_passed else None

    if not name:
        return jsonify({"error": "name обязателен"}), 400

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"""
                UPDATE public.roles
                   SET name = %s,
                       description = {{}} -- подставим выражение ниже
                 WHERE id = %s
             RETURNING id, name, description;
            """.format("COALESCE(%s, description)" if not desc_passed else "%s"),
            (name, None if not desc_passed else description, role_id))
            row = cur.fetchone()

            if not row:
                return jsonify({"error": "Роль не найдена"}), 404

            return jsonify({"item": row}), 200

    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == errorcodes.UNIQUE_VIOLATION:
            return jsonify({"error": "Роль с таким name уже существует"}), 409
        return jsonify({"error": "db error"}), 500


# DELETE: удалить роль по id
@role_bp.route("/delete/<int:role_id>", methods=["DELETE"])
def delete_role(role_id: int):
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("DELETE FROM public.roles WHERE id = %s RETURNING id;", (role_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Роль не найдена"}), 404
            return jsonify({"deleted": True, "id": row["id"]}), 200
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == errorcodes.FOREIGN_KEY_VIOLATION:
            return jsonify({"error": "Нельзя удалить: есть связанные записи"}), 409
        return jsonify({"error": "db error"}), 500
