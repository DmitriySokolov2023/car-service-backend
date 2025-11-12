from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor
from psycopg2 import errorcodes
import psycopg2
from config import CONNECT_DB

clients_bp = Blueprint("clients", __name__)

def _to_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "t", "yes", "y")
    if isinstance(v, (int, float)):
        return bool(v)
    return None

# GET: все клиенты
@clients_bp.route("/get", methods=["GET"])
def get_clients():
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, is_company, name, phone, email, comment
                FROM public.clients
                ORDER BY id ASC;
            """)
            rows = cur.fetchall() or []
            return jsonify({"items": rows}), 200
    except Exception:
        return jsonify({"error": "db error"}), 500

# POST: создать клиента (comment опционален)
@clients_bp.route("/create", methods=["POST"])
def create_client():
    data = request.get_json(silent=True) or {}

    is_company = data.get("is_company")
    is_company = _to_bool(is_company) if is_company is not None else None

    name   = (data.get("name")  or "").strip()
    phone  = (data.get("phone") or "").strip()
    email  = (data.get("email") or "").strip()
    comment = (data.get("comment") or "").strip()
    comment = comment if comment != "" else None

    if is_company is None or not name or not phone or not email:
        return jsonify({"error": "is_company, name, phone, email обязательны"}), 400

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO public.clients (is_company, name, phone, email, comment)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, is_company, name, phone, email, comment;
            """, (is_company, name, phone, email, comment))
            row = cur.fetchone()
            return jsonify({"item": row}), 201

    except psycopg2.Error as e:
        code = getattr(e, "pgcode", None)
        if code == errorcodes.UNIQUE_VIOLATION:
            # например, если есть уникальные индексы на phone/email
            return jsonify({"error": "Клиент с таким телефоном или email уже существует"}), 409
        return jsonify({"error": "db error"}), 500

# PUT/PATCH: обновить клиента по id (те же поля; comment опционален)
@clients_bp.route("/update/<int:client_id>", methods=["PUT", "PATCH"])
def update_client(client_id: int):
    data = request.get_json(silent=True) or {}

    is_company = data.get("is_company")
    is_company = _to_bool(is_company) if is_company is not None else None

    name   = (data.get("name")  or "").strip()
    phone  = (data.get("phone") or "").strip()
    email  = (data.get("email") or "").strip()

    # comment: если не передали — не трогаем; если передали "" — очищаем до NULL
    comment_passed = "comment" in data
    comment = (data.get("comment") or "").strip() if comment_passed else None
    if comment_passed and comment == "":
        comment = None

    if is_company is None or not name or not phone or not email:
        return jsonify({"error": "is_company, name, phone, email обязательны"}), 400

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            # comment: если ключ не пришёл, оставляем как было; если пришёл — ставим значение (в т.ч. NULL)
            cur.execute(f"""
                UPDATE public.clients
                   SET is_company = %s,
                       name       = %s,
                       phone      = %s,
                       email      = %s,
                       comment    = { "%s" if comment_passed else "COALESCE(%s, comment)" }
                 WHERE id = %s
             RETURNING id, is_company, name, phone, email, comment;
            """, (is_company, name, phone, email, comment if comment_passed else None, client_id))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Клиент не найден"}), 404
            return jsonify({"item": row}), 200

    except psycopg2.Error as e:
        code = getattr(e, "pgcode", None)
        if code == errorcodes.UNIQUE_VIOLATION:
            return jsonify({"error": "Дубликат телефона или email"}), 409
        return jsonify({"error": "db error"}), 500

# DELETE: удалить клиента
@clients_bp.route("/delete/<int:client_id>", methods=["DELETE"])
def delete_client(client_id: int):
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""DELETE FROM public.clients WHERE id = %s RETURNING id;""", (client_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Клиент не найден"}), 404
            return jsonify({"deleted": True, "id": row["id"]}), 200
    except psycopg2.Error as e:
        code = getattr(e, "pgcode", None)
        if code == errorcodes.FOREIGN_KEY_VIOLATION:
            return jsonify({"error": "Нельзя удалить: есть связанные записи"}), 409
        return jsonify({"error": "db error"}), 500