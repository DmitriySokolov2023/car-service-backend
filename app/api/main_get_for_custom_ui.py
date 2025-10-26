from flask import Blueprint, jsonify, request
import psycopg2
from config import CONNECT_DB
from app.utils.system_house.get_school_year import school_working_year
from datetime import datetime, timedelta
import psycopg2.extras


main_get_custom_bp = Blueprint("main_get_custom_pb", __name__)

@main_get_custom_bp.route("/get/class", methods=["GET"])
def get_custom_class():
    import psycopg2
    from flask import request, jsonify


    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT course
            FROM practical.classes
            ORDER BY course ASC;
            """
        )
        rows = cur.fetchall()

        
        courses = [{"value": r[0], "label": r[0]} for r in rows]

        cur.close()
        conn.close()
        return jsonify(courses), 200

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

@main_get_custom_bp.route("/get/class/by/site", methods=["GET"])
def get_custom_class_by_site():
    import psycopg2
    from flask import request, jsonify

    site = request.args.get("site")  # например, /get/class/by/site?site=АЗ
    if not site:
        return jsonify({"error": "Параметр 'site' обязателен"}), 400

    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT course
            FROM practical.classes
            WHERE site = %s
            ORDER BY course ASC;
            """,
            (site,),
        )
        rows = cur.fetchall()

        
        courses = [{"value": r[0], "label": r[0]} for r in rows]

        cur.close()
        conn.close()
        return jsonify(courses), 200

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500
    

@main_get_custom_bp.route("/get/liter/by/class", methods=["GET"])
def get_liter_by_class():
    import psycopg2
    from flask import request, jsonify

    site = request.args.get("site")
    _class = request.args.get("_class")

    if not site or not _class:
        return jsonify({"error": "Параметры 'site' и '_class' обязательны"}), 400

    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT liter
            FROM practical.classes
            WHERE site = %s AND course = %s
            ORDER BY liter ASC;
            """,
            (site, _class),
        )
        rows = cur.fetchall()

        liters = [{"value": r[0], "label": r[0]} for r in rows]

        cur.close()
        conn.close()
        return jsonify(liters), 200

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500
    

@main_get_custom_bp.route("/get/students/by/class", methods=["GET"])
def get_students_by_class():
    import psycopg2
    from flask import request, jsonify

    site = request.args.get("site")
    course = request.args.get("course")
    liter = request.args.get("liter")

    if not site or not course or not liter:
        return jsonify({"error": "Параметры 'site', 'course' и 'liter' обязательны"}), 400

    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.id_student, s.fio
            FROM practical.students s
            JOIN practical.students_classes sc ON s.id_student = sc.id_student
            JOIN practical.classes c ON sc.id_class = c.id_class
            WHERE s.fio != 'nan' and fio is not null and c.site = %s AND c.course = %s AND c.liter = %s
            ORDER BY s.fio ASC;
            """,
            (site, course, liter),
        )
        rows = cur.fetchall()

        students = [{"value": r[0], "label": r[1]} for r in rows]

        cur.close()
        conn.close()
        return jsonify(students), 200

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500
