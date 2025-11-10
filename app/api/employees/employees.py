from flask import Blueprint, jsonify,request
from psycopg2.extras import RealDictCursor
import psycopg2
from config import CONNECT_DB
from psycopg2 import errorcodes

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
    

    
@employees_bp.route("/create", methods=["POST"])
def create_employee():
    data = request.get_json(silent=True) or {}

    full_name = (data.get("full_name") or "").strip()
    email     = (data.get("email") or "").strip()
    phone     = (data.get("phone") or "").strip()
    role_id   = data.get("role_id")
    active = True

    if not full_name or not email or not phone or role_id is None:
        return jsonify({"error": "full_name, email, phone, role_id обязательны"}), 400

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO public.employees (full_name, email, phone, role_id, active)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *;
            """, (full_name, email, phone, role_id, active))
            row = cur.fetchone()
            return jsonify({"item": row}), 201
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == errorcodes.UNIQUE_VIOLATION:
            return jsonify({"error": "Сотрудник с таким email или телефоном уже существует"}), 409
        # Конфликт внешнего ключа по role_id
        if getattr(e, "pgcode", None) == errorcodes.FOREIGN_KEY_VIOLATION:
            return jsonify({"error": "role_id не найден в roles"}), 409
        # Прочее
        return jsonify({"error": e}), 500
    
@employees_bp.route("/update/<int:employee_id>", methods=["PUT", "PATCH"])
def update_employee(employee_id: int):
    data = request.get_json(silent=True) or {}

    full_name = (data.get("full_name") or "").strip()
    email     = (data.get("email") or "").strip()
    phone     = (data.get("phone") or "").strip()
    role_id   = data.get("role_id")
    active    = data.get("active")  # необязательное поле

    if not full_name or not email or not phone or role_id is None:
        return jsonify({"error": "full_name, email, phone, role_id обязательны"}), 400

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE public.employees
                SET full_name = %s,
                    email     = %s,
                    phone     = %s,
                    role_id   = %s,
                    active    = COALESCE(%s, active)
                WHERE id = %s
                RETURNING *;
            """, (full_name, email, phone, role_id, active, employee_id))
            row = cur.fetchone()

            if not row:
                return jsonify({"error": "Сотрудник не найден"}), 404

            return jsonify({"item": row}), 200

    except psycopg2.Error as e:
        code = getattr(e, "pgcode", None)
        if code == errorcodes.UNIQUE_VIOLATION:
            return jsonify({"error": "Дубликат email или телефона"}), 409
        if code == errorcodes.FOREIGN_KEY_VIOLATION:
            return jsonify({"error": "role_id не найден в roles"}), 409
        return jsonify({"error": "db error"}), 500

@employees_bp.route("/delete/<int:employee_id>", methods=["DELETE"])
def delete_employee(employee_id: int):
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("DELETE FROM public.employees WHERE id = %s RETURNING id;", (employee_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Сотрудник не найден"}), 404
            return jsonify({"deleted": True, "id": row["id"]}), 200

    except psycopg2.Error as e:
        code = getattr(e, "pgcode", None)
        # например, если на сотрудника есть ссылки (FK) из других таблиц
        if code == errorcodes.FOREIGN_KEY_VIOLATION:
            return jsonify({"error": "Нельзя удалить: есть связанные записи"}), 409
        return jsonify({"error": "db error"}), 500