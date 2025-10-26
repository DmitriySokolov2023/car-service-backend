from flask import Blueprint, jsonify, request
import psycopg2
from config import CONNECT_DB
from app.utils.system_house.get_school_year import school_working_year
from datetime import datetime, timedelta
import psycopg2.extras


main_get_bp = Blueprint("main_get_pb", __name__)


@main_get_bp.route("/get/subjects", methods=["GET"])
def get_subjects():
    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id_subject, subject_name
            FROM practical.subject
            ORDER BY id_subject ASC;
        """)
        rows = cur.fetchall()

        subjects = [
            {"value": r[0], "label": r[1]}
            for r in rows
        ]

        cur.close()
        conn.close()
       

        return jsonify(subjects), 200

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500
    
@main_get_bp.route("/get/classes", methods=["GET"])
def get_class():
    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT course
            FROM practical.classes
            ORDER BY course ASC;
        """)
        rows = cur.fetchall()

        # Формируем список значений, например [1, 2, 3, 4, ...]
        classes = [r[0] for r in rows]

        cur.close()
        conn.close()

        return jsonify(classes), 200

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

@main_get_bp.route("/get/liter", methods=["GET"])
def get_liter():
    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT liter
            FROM practical.classes
            ORDER BY liter ASC;
        """)
        rows = cur.fetchall()

        # Формируем список значений, например [1, 2, 3, 4, ...]
        classes = [r[0] for r in rows]

        cur.close()
        conn.close()

        return jsonify(classes), 200

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500
    
@main_get_bp.route("/get/levels", methods=["GET"])
def get_levels():
    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, level
            FROM practical.olympics_levels
            ORDER BY id ASC;
        """)
        rows = cur.fetchall()

        subjects = [
            {"value": r[0], "label": r[1]}
            for r in rows
        ]

        cur.close()
        conn.close()
        

        return jsonify(subjects), 200

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500
    


@main_get_bp.route("/get/students", methods=["GET"])
def get_student_all():
    faculty = request.args.get("faculty", "").strip()
    fio_student = request.args.get("fioStudent", "").strip()
    course = request.args.get("course", "").strip()
    liter = request.args.get("liter", "").strip()
    site = request.args.get("site", "").strip()

    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    query = """
        SELECT 
            st.id_student,
            st.fio AS fio_student,
            c.course as course,
            c.liter as liter,
            c.site as site,
            st.faculty
        FROM practical.students AS st
        JOIN practical.students_classes AS sc 
            ON st.id_student = sc.id_student
        JOIN practical.classes AS c 
            ON sc.id_class = c.id_class
        WHERE sc.date_end IS NULL
        
        
    """

    conditions = []
    params = []

    if faculty:
        conditions.append("st.faculty ILIKE %s")
        params.append(f"%{faculty}%")
    if fio_student:
        conditions.append("st.fio ILIKE %s")
        params.append(f"%{fio_student}%")
    if course:
        conditions.append("CAST(c.course AS TEXT) = %s")
        params.append(course)
    if liter:
        conditions.append("c.liter = %s")
        params.append(liter)
    if site:
        conditions.append("c.site ILIKE %s")
        params.append(f"%{site}%")

    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += "ORDER BY course, liter, site,fio_student asc"

    cur.execute(query, params)
    rows = cur.fetchall()

    students = [{
        "id_student": r[0],
        "fio_student": r[1],
        "course": r[2],
        "liter": r[3],
        "site": r[4],
        "faculty": r[5]
    } for r in rows]

    cur.close()
    conn.close()

    return jsonify(students)

