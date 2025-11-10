# services.py
from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor
from psycopg2 import errorcodes
import psycopg2
from config import CONNECT_DB

services_bp = Blueprint("services", __name__)

# GET: все услуги
@services_bp.route("/get", methods=["GET"])
def get_services():
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, unit, base_price::float8 AS base_price, description
                FROM public.services
                ORDER BY id ASC;
            """)
            rows = cur.fetchall() or []
            return jsonify({"items": rows}), 200
    except Exception:
        return jsonify({"error": "db error"}), 500



# POST: создать услугу (name, unit, base_price обязательны; description опциональна)
@services_bp.route("/create", methods=["POST"])
def create_service():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    unit = (data.get("unit") or "").strip()
    base_price = data.get("base_price")
    description = (data.get("description") or "").strip()
    description = description if description != "" else None

    # валидация
    if not name or not unit or base_price is None:
        return jsonify({"error": "name, unit, base_price обязательны"}), 400
    try:
        base_price = float(base_price)
    except (TypeError, ValueError):
        return jsonify({"error": "base_price должен быть числом"}), 400
    try:
      if base_price <= 0:
          raise (TypeError, ValueError)
    except (TypeError, ValueError):
        return jsonify({"error": "base_price должен быть больше нуля"}), 400

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO public.services (name, unit, base_price, description)
                VALUES (%s, %s, %s, %s)
                RETURNING id, name, unit, base_price::float8 AS base_price, description;
            """, (name, unit, base_price, description))
            row = cur.fetchone()
            return jsonify({"item": row}), 201
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == errorcodes.UNIQUE_VIOLATION:
            return jsonify({"error": "Услуга с таким name уже существует"}), 409
        return jsonify({"error": "db error"}), 500

# PUT/PATCH: обновить услугу по id (те же поля; description опциональна)
@services_bp.route("/update/<int:service_id>", methods=["PUT", "PATCH"])
def update_service(service_id: int):
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    unit = (data.get("unit") or "").strip()
    base_price = data.get("base_price")
    desc_passed = "description" in data
    description = (data.get("description") or "").strip() if desc_passed else None
    if desc_passed and description == "":
        description = None

    if not name or not unit or base_price is None:
        return jsonify({"error": "name, unit, base_price обязательны"}), 400
    try:
        base_price = float(base_price)
    except (TypeError, ValueError):
        return jsonify({"error": "base_price должен быть числом"}), 400
    try:
      if base_price <= 0:
          raise (TypeError, ValueError)
    except (TypeError, ValueError):
        return jsonify({"error": "base_price должен быть больше нуля"}), 400

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            # description: если не передали — не трогаем; если передали — ставим значение (в т.ч. NULL)
            cur.execute(f"""
                UPDATE public.services
                   SET name = %s,
                       unit = %s,
                       base_price = %s,
                       description = {{}} 
                 WHERE id = %s
             RETURNING id, name, unit, base_price::float8 AS base_price, description;
            """.format("COALESCE(%s, description)" if not desc_passed else "%s"),
            (name, unit, base_price, None if not desc_passed else description, service_id))
            row = cur.fetchone()

            if not row:
                return jsonify({"error": "Услуга не найдена"}), 404

            return jsonify({"item": row}), 200
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == errorcodes.UNIQUE_VIOLATION:
            return jsonify({"error": "Услуга с таким name уже существует"}), 409
        return jsonify({"error": "db error"}), 500

# DELETE: удалить услугу
@services_bp.route("/delete/<int:service_id>", methods=["DELETE"])
def delete_service(service_id: int):
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""DELETE FROM public.services WHERE id = %s RETURNING id;""", (service_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Услуга не найдена"}), 404
            return jsonify({"deleted": True, "id": row["id"]}), 200
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == errorcodes.FOREIGN_KEY_VIOLATION:
            return jsonify({"error": "Нельзя удалить: есть связанные записи"}), 409
        return jsonify({"error": "db error"}), 500
