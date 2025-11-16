# cars.py
from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor
from psycopg2 import errorcodes
import psycopg2
from config import CONNECT_DB
from datetime import date

cars_bp = Blueprint("cars", __name__)

MIN_YEAR = 1900
MAX_YEAR = date.today().year + 1
def _year_ok(y: int) -> bool: return MIN_YEAR <= y <= MAX_YEAR

# GET: все авто
@cars_bp.route("/get", methods=["GET"])
def get_cars():
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, client_id, make, model, vin, license_plate, year, mileage
                FROM public.cars
                ORDER BY id ASC;
            """)
            rows = cur.fetchall() or []
            return jsonify({"items": rows}), 200
    except Exception:
        return jsonify({"error": "db error"}), 500

@cars_bp.route("/get/by-client/<int:client_id>", methods=["GET"])
def get_cars_by_client(client_id: int):
    """
    Возвращает все автомобили клиента.
    Формат ответа: {"items": [...], "count": N}
    """
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, client_id, make, model, vin, license_plate, year, mileage
                FROM public.cars
                WHERE client_id = %s
                ORDER BY id ASC;
            """, (client_id,))
            rows = cur.fetchall() or []
            return jsonify({"items": rows, "count": len(rows)}), 200
    except Exception:
        return jsonify({"error": "db error"}), 500
    
@cars_bp.route("/get/<int:car_id>", methods=["GET"])
def get_car_by_id(car_id: int):
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""SELECT * FROM public.cars WHERE id = %s LIMIT 1;""", (car_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Авто не найдено"}), 404
            return jsonify({"item": row}), 200
    except Exception:
        return jsonify({"error": "db error"}), 500
# POST: создать авто (все поля обязательны)
@cars_bp.route("/create", methods=["POST"])
def create_car():
    data = request.get_json(silent=True) or {}

    
    client_id     = data.get("client_id")
    make          = (data.get("make") or "").strip()
    model         = (data.get("model") or "").strip()
    vin           = (data.get("vin") or "").strip()
    license_plate = (data.get("license_plate") or "").strip()
    year          = data.get("year")
    mileage       = data.get("mileage")

    if client_id is None or not make or not model or not vin or not license_plate or year is None or mileage is None:
        return jsonify({"error": "client_id, make, model, vin, license_plate, year, mileage обязательны"}), 400

    try:
        client_id = int(client_id)
        year = int(year)
        mileage = int(mileage)
    except (TypeError, ValueError):
        return jsonify({"error": "client_id, year, mileage должны быть целыми числами"}), 400
    if not _year_ok(year):
        return jsonify({
            "error": f"Некорректный год выпуска. Допустимый диапазон: {MIN_YEAR}..{MAX_YEAR}"
        }), 400

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO public.cars (client_id, make, model, vin, license_plate, year, mileage)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, client_id, make, model, vin, license_plate, year, mileage;
            """, (client_id, make, model, vin, license_plate, year, mileage))
            row = cur.fetchone()
            return jsonify({"item": row}), 201
    except psycopg2.Error as e:
        code = getattr(e, "pgcode", None)
        if code == errorcodes.CHECK_VIOLATION:
            constraint = getattr(getattr(e, "diag", None), "constraint_name", None)
            # дружественный текст под известный чек:
            if constraint == "cars_year_chk":
                return jsonify({
                    "error": f"Год выпуска вне допустимого диапазона {MIN_YEAR}..{MAX_YEAR}",
                    "constraint": constraint
                }), 400
            # общее сообщение для других CHECK'ов
            return jsonify({
                "error": "Нарушено ограничение целостности (CHECK).",
                "constraint": constraint
            }), 400

        if code == errorcodes.UNIQUE_VIOLATION:
            return jsonify({"error": "Запись с таким VIN или номером уже существует"}), 409
        if code == errorcodes.FOREIGN_KEY_VIOLATION:
            return jsonify({"error": "client_id не найден в clients"}), 409
        return jsonify({"error": e}), 500


# PUT/PATCH: обновить авто по id (те же поля, все обязательны)
@cars_bp.route("/update/<int:car_id>", methods=["PUT", "PATCH"])
def update_car(car_id: int):
    data = request.get_json(silent=True) or {}
    print(data)
    client_id     = data.get("client_id")
    make          = (data.get("make") or "").strip()
    model         = (data.get("model") or "").strip()
    vin           = (data.get("vin") or "").strip()
    license_plate = (data.get("license_plate") or "").strip()
    year          = data.get("year")
    mileage       = data.get("mileage")
    try:
        client_id = int(client_id)
        year = int(year)
        mileage = int(mileage)
    except (TypeError, ValueError):
        return jsonify({"error": "client_id, year, mileage должны быть целыми числами"}), 400

    if not _year_ok(year):
        return jsonify({
            "error": f"Некорректный год выпуска. Допустимый диапазон: {MIN_YEAR}..{MAX_YEAR}"
        }), 400

    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE public.cars
                   SET client_id=%s, make=%s, model=%s, vin=%s,
                       license_plate=%s, year=%s, mileage=%s
                 WHERE id=%s
             RETURNING id, client_id, make, model, vin, license_plate, year, mileage;
            """, (client_id, make, model, vin, license_plate, year, mileage, car_id))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Авто не найдено"}), 404
            return jsonify({"item": row}), 200

    except psycopg2.Error as e:
        code = getattr(e, "pgcode", None)
        if code == errorcodes.CHECK_VIOLATION:
            constraint = getattr(getattr(e, "diag", None), "constraint_name", None)
            if constraint == "cars_year_chk":
                return jsonify({
                    "error": f"Год выпуска вне допустимого диапазона {MIN_YEAR}..{MAX_YEAR}",
                    "constraint": constraint
                }), 400
            return jsonify({
                "error": "Нарушено ограничение целостности (CHECK).",
                "constraint": constraint
            }), 400

        if code == errorcodes.UNIQUE_VIOLATION:
            return jsonify({"error": "Запись с таким VIN или номером уже существует"}), 409
        if code == errorcodes.FOREIGN_KEY_VIOLATION:
            return jsonify({"error": "client_id не найден в clients"}), 409
        return jsonify({"error": e}), 500


# DELETE: удалить авто
@cars_bp.route("/delete/<int:car_id>", methods=["DELETE"])
def delete_car(car_id: int):
    try:
        with psycopg2.connect(CONNECT_DB) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""DELETE FROM public.cars WHERE id = %s RETURNING id;""", (car_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Авто не найдено"}), 404
            return jsonify({"deleted": True, "id": row["id"]}), 200
    except psycopg2.Error as e:
        code = getattr(e, "pgcode", None)
        if code == errorcodes.FOREIGN_KEY_VIOLATION:
            return jsonify({"error": "Нельзя удалить: есть связанные записи"}), 409
        return jsonify({"error": "db error"}), 500
