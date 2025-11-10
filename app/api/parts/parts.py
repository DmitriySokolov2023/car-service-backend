# parts.py
from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor
from psycopg2 import errorcodes
import psycopg2
from config import CONNECT_DB

parts_bp = Blueprint("parts", __name__)

# GET: все запчасти
@parts_bp.route("/get", methods=["GET"])
def get_parts():
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, part_number, name, unit, price::float8 AS price, stock_qty
                FROM public.parts
                ORDER BY id ASC;
            """)
            rows = cur.fetchall() or []
            return jsonify({"items": rows}), 200
    except Exception:
        return jsonify({"error": "db error"}), 500


# POST: создать запчасть (все поля обязательны)
@parts_bp.route("/create", methods=["POST"])
def create_part():
    data = request.get_json(silent=True) or {}

    part_number = (data.get("part_number") or "").strip()
    name        = (data.get("name") or "").strip()
    unit        = (data.get("unit") or "").strip()
    price       = data.get("price")
    stock_qty   = data.get("stock_qty")

    if not part_number or not name or not unit or price is None or stock_qty is None:
        return jsonify({"error": "part_number, name, unit, price, stock_qty обязательны"}), 400

    # типы
    try:
        price = float(price)
    except (TypeError, ValueError):
        return jsonify({"error": "price должен быть числом"}), 400
    try:
        stock_qty = int(stock_qty)
    except (TypeError, ValueError):
        return jsonify({"error": "stock_qty должен быть целым числом"}), 400
    try:
        if stock_qty < 0:
            raise (TypeError, ValueError)
    except (TypeError, ValueError):
        return jsonify({"error": "stock_qty должен быть меньше нуля"}), 400
    try:
      if price <= 0:
          raise (TypeError, ValueError)
    except (TypeError, ValueError):
        return jsonify({"error": "price должен быть больше нуля"}), 400

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO public.parts (part_number, name, unit, price, stock_qty)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, part_number, name, unit, price::float8 AS price, stock_qty;
            """, (part_number, name, unit, price, stock_qty))
            row = cur.fetchone()
            return jsonify({"item": row}), 201
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == errorcodes.UNIQUE_VIOLATION:
            return jsonify({"error": "Запчасть с таким part_number уже существует"}), 409
        return jsonify({"error": "db error"}), 500


# PUT/PATCH: обновить по id (принимает те же поля, что и POST)
@parts_bp.route("/update/<int:part_id>", methods=["PUT", "PATCH"])
def update_part(part_id: int):
    data = request.get_json(silent=True) or {}

    part_number = (data.get("part_number") or "").strip()
    name        = (data.get("name") or "").strip()
    unit        = (data.get("unit") or "").strip()
    price       = data.get("price")
    stock_qty   = data.get("stock_qty")

    if not part_number or not name or not unit or price is None or stock_qty is None:
        return jsonify({"error": "part_number, name, unit, price, stock_qty обязательны"}), 400

    try:
        price = float(price)
    except (TypeError, ValueError):
        return jsonify({"error": "price должен быть числом"}), 400
    try:
        stock_qty = int(stock_qty)
    except (TypeError, ValueError):
        return jsonify({"error": "stock_qty должен быть целым числом"}), 400
    try:
      if price <= 0:
          raise (TypeError, ValueError)
    except (TypeError, ValueError):
        return jsonify({"error": "price должен быть больше нуля"}), 400
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE public.parts
                   SET part_number = %s,
                       name        = %s,
                       unit        = %s,
                       price       = %s,
                       stock_qty   = %s
                 WHERE id = %s
             RETURNING id, part_number, name, unit, price::float8 AS price, stock_qty;
            """, (part_number, name, unit, price, stock_qty, part_id))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Запчасть не найдена"}), 404
            return jsonify({"item": row}), 200
    except psycopg2.Error as e:
        code = getattr(e, "pgcode", None)
        if code == errorcodes.UNIQUE_VIOLATION:
            return jsonify({"error": "Запчасть с таким part_number уже существует"}), 409
        return jsonify({"error": "db error"}), 500


# DELETE: удалить по id
@parts_bp.route("/delete/<int:part_id>", methods=["DELETE"])
def delete_part(part_id: int):
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""DELETE FROM public.parts WHERE id = %s RETURNING id;""", (part_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Запчасть не найдена"}), 404
            return jsonify({"deleted": True, "id": row["id"]}), 200
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == errorcodes.FOREIGN_KEY_VIOLATION:
            return jsonify({"error": "Нельзя удалить: есть связанные записи"}), 409
        return jsonify({"error": "db error"}), 500
