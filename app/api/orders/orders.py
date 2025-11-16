# orders.py
from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor
from psycopg2 import errorcodes
from datetime import date
import psycopg2
from config import CONNECT_DB

orders_bp = Blueprint("orders", __name__)

# GET: все заказы
@orders_bp.route("/get", methods=["GET"])
def get_orders():
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, client_id, car_id, manager_id,
                       opened_at, closed_at, status, comment
                FROM public.orders
                ORDER BY id ASC;
            """)
            rows = cur.fetchall() or []
            return jsonify({"items": rows}), 200
    except Exception:
        return jsonify({"error": "db error"}), 500


# POST: создать заказ
@orders_bp.route("/create", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}

    client_id  = data.get("client_id")
    car_id     = data.get("car_id")
    manager_id = data.get("manager_id")
    status     = (data.get("status") or "").strip()
    comment    = (data.get("comment") or "").strip()
    comment    = comment if comment != "" else None

    # обязательные поля
    if client_id is None or car_id is None or manager_id is None or not status:
        return jsonify({"error": "client_id, car_id, manager_id, status обязательны"}), 400

    # типы
    try:
        client_id = int(client_id)
        car_id = int(car_id)
        manager_id = int(manager_id)
    except (TypeError, ValueError):
        return jsonify({"error": "client_id, car_id, manager_id должны быть целыми числами"}), 400

    opened_at = date.today().isoformat()  # 'YYYY-MM-DD', как просили

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO public.orders
                    (client_id, car_id, manager_id, opened_at, closed_at, status, comment)
                VALUES (%s, %s, %s, %s, NULL, %s, %s)
                RETURNING id, client_id, car_id, manager_id,
                          opened_at, closed_at, status, comment;
            """, (client_id, car_id, manager_id, opened_at, status, comment))
            row = cur.fetchone()
            return jsonify({"item": row}), 201

    except psycopg2.Error as e:
        code = getattr(e, "pgcode", None)
        if code == errorcodes.FOREIGN_KEY_VIOLATION:
            # одна из ссылок client_id / car_id / manager_id не существует
            return jsonify({"error": "Неверные ссылки: client_id/car_id/manager_id"}), 409
        if code == errorcodes.UNIQUE_VIOLATION:
            # если у вас есть уникальные ограничения, сообщим общее
            return jsonify({"error": "Нарушено уникальное ограничение"}), 409
        return jsonify({"error": "db error"}), 500


# PUT/PATCH: обновить заказ (без opened_at/closed_at)
@orders_bp.route("/update/<int:order_id>", methods=["PUT", "PATCH"])
def update_order(order_id: int):
    data = request.get_json(silent=True) or {}

    client_id  = data.get("client_id")
    car_id     = data.get("car_id")
    manager_id = data.get("manager_id")
    status     = (data.get("status") or "").strip()

    # comment: если ключ не пришёл — не трогаем; если пришёл пустой — обнулим до NULL
    comment_passed = "comment" in data
    comment = (data.get("comment") or "").strip() if comment_passed else None
    if comment_passed and comment == "":
        comment = None

    if client_id is None or car_id is None or manager_id is None or not status:
        return jsonify({"error": "client_id, car_id, manager_id, status обязательны"}), 400

    try:
        client_id = int(client_id)
        car_id = int(car_id)
        manager_id = int(manager_id)
    except (TypeError, ValueError):
        return jsonify({"error": "client_id, car_id, manager_id должны быть целыми числами"}), 400

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"""
                UPDATE public.orders
                   SET client_id  = %s,
                       car_id     = %s,
                       manager_id = %s,
                       status     = %s,
                       comment    = { "%s" if comment_passed else "COALESCE(%s, comment)" }
                 WHERE id = %s
             RETURNING id, client_id, car_id, manager_id,
                       opened_at, closed_at, status, comment;
            """, (client_id, car_id, manager_id, status,
                  (comment if comment_passed else None),
                  order_id))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Заказ не найден"}), 404
            return jsonify({"item": row}), 200

    except psycopg2.Error as e:
        code = getattr(e, "pgcode", None)
        if code == errorcodes.FOREIGN_KEY_VIOLATION:
            return jsonify({"error": "Неверные ссылки: client_id/car_id/manager_id"}), 409
        return jsonify({"error": "db error"}), 500


# DELETE: удалить заказ
@orders_bp.route("/delete/<int:order_id>", methods=["DELETE"])
def delete_order(order_id: int):
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""DELETE FROM public.orders WHERE id = %s RETURNING id;""", (order_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Заказ не найден"}), 404
            return jsonify({"deleted": True, "id": row["id"]}), 200
    except psycopg2.Error as e:
        code = getattr(e, "pgcode", None)
        if code == errorcodes.FOREIGN_KEY_VIOLATION:
            return jsonify({"error": "Нельзя удалить: есть связанные записи"}), 409
        return jsonify({"error": "db error"}), 500

@orders_bp.route("/get/by", methods=["GET"])
def get_orders_by():
    """Фильтр по client_id и/или car_id: /orders/get/by?client_id=1&car_id=2"""
    client_id = request.args.get("client_id", type=int)
    car_id = request.args.get("car_id", type=int)

    base_sql = "SELECT * FROM public.orders WHERE 1=1"
    params = []
    if client_id is not None:
        base_sql += " AND client_id = %s"
        params.append(client_id)
    if car_id is not None:
        base_sql += " AND car_id = %s"
        params.append(car_id)
    base_sql += " ORDER BY opened_at DESC, id DESC;"

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(base_sql, params)
            rows = cur.fetchall() or []
            return jsonify({"items": rows, "count": len(rows)}), 200
    except Exception:
        return jsonify({"error": "db error"}), 500