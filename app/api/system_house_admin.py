from flask import Blueprint, jsonify, request
import psycopg2
from config import CONNECT_DB
from datetime import datetime, timedelta
import psycopg2.extras
from app.utils.system_house.get_school_year import school_working_year
import uuid

house_admin_bp = Blueprint("system-house-admin", __name__)

#Поиск получателя баллов
@house_admin_bp.route("/faculty/student/score", methods=["GET"])
def get_faculty_student_score():
    fio = request.args.get("fio")  # получаем значение из query-параметра
    faculty = request.args.get("faculty", "").strip()
    fioStudent = request.args.get("fioStudent") 
    score_date = request.args.get("score_date", "").strip()

    course = request.args.get("course", "").strip()
    liter = request.args.get("liter", "").strip()
    site = request.args.get("site", "").strip()


    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    query = """
        SELECT 
            fss.id,
            fss.id_student_class,
            sc.id_class,
            st.fio AS fio_student,
            st.faculty,
            s.fio AS fio_staff,
            fss.criteria,
            fss.score_date,
            fss.score,
            c.course,
            c.liter,
            c.site
        FROM practical.faculty_student_score AS fss
        JOIN practical.students_classes AS sc
            ON sc.id_student_class = fss.id_student_class
        JOIN practical.students AS st
            ON sc.id_student = st.id_student
        JOIN practical.staff AS s
            ON s.id_staff = (
                SELECT DISTINCT id_staff 
                FROM practical.staff_posts 
                WHERE id_staff_post = fss.id_staff_post
            )
        JOIN practical.classes AS c
            ON sc.id_class = c.id_class
    """

    conditions = []
    params = []

    if fio:
        conditions.append("s.fio ILIKE %s")
        params.append(f"%{fio}%")
    if faculty:
        conditions.append("st.faculty ILIKE %s")
        params.append(f"%{faculty}%")
    if fioStudent:
        conditions.append("st.fio ILIKE %s")
        params.append(f"%{fioStudent}%")
    if score_date:
        conditions.append("fss.score_date::date = %s")
        params.append(score_date)
    if course:
        conditions.append("c.course = %s")
        params.append(course)
    if liter:
        conditions.append("c.liter = %s")
        params.append(liter)
    if site:
        conditions.append("c.site ILIKE %s")
        params.append(f"%{site}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    cur.execute(query, params)

    students = [{
        "id": r[0],
        "id_student_class": r[1],
        "id_class": r[2],
        "fio_student": r[3],
        "faculty": r[4],
        "fio": r[5],
        "criteria": r[6],
        "score_date": r[7].isoformat() if r[7] else None,
        "score": r[8],
        "course": r[9],
        "liter": r[10],
        "site": r[11],
    } for r in cur.fetchall()]

    cur.close()
    conn.close()
    return jsonify(students)

@house_admin_bp.route("/faculty/student/all", methods=["GET"])
def get_faculty_student_all():
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
            c.course,
            c.liter,
            c.site,
            st.faculty
        FROM practical.students AS st
        JOIN practical.students_classes AS sc 
            ON st.id_student = sc.id_student
        JOIN practical.classes AS c 
            ON sc.id_class = c.id_class
        WHERE sc.date_end IS NULL
          AND c.course > 4
    """

    conditions = []
    params = []

    # --- фильтры ---
    if faculty:
        if faculty.lower() == "none":
            conditions.append("(st.faculty IS NULL OR TRIM(st.faculty) = '')")
        else:
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

    # добавляем условия в запрос
    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += " ORDER BY st.id_student ASC"

    cur.execute(query, params)
    rows = cur.fetchall()

    students = [{
        "id_student": r[0],
        "fio_student": r[1],
        "course": r[2],
        "liter": r[3],
        "site": r[4],
        "faculty": r[5] if r[5] else ""
    } for r in rows]

    cur.close()
    conn.close()

    return jsonify(students)
@house_admin_bp.route("/faculty/student/update", methods=["POST"])
def update_faculty_student():
    data = request.get_json()
    id_student = data.get("id_student")
    faculty = data.get("faculty")

    if not id_student:
        return jsonify({"error": "id_student required"}), 400

    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    if faculty == "" or faculty is None:
        cur.execute("UPDATE practical.students SET faculty = NULL WHERE id_student = %s", (id_student,))
    else:
        cur.execute("UPDATE practical.students SET faculty = %s WHERE id_student = %s", (faculty, id_student))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"success": True})

#Поиск баллов по факультетам 
@house_admin_bp.route("/faculty/faculty/score", methods=["GET"])
def get_faculty_faculty_score():
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    fio = request.args.get('fio')
    faculty = request.args.get('faculty')
    site = request.args.get('site')
    score_date = request.args.get('score_date')

    query = """
        SELECT 
            ffs.id,
            s.fio,
            ffs.faculty_name,
            ffs.criteria,
            ffs.site,
            ffs.score,
            ffs.score_date
        FROM practical.faculty_faculty_score as ffs
        JOIN practical.staff AS s
        ON s.id_staff = (SELECT DISTINCT id_staff from practical.staff_posts where id_staff_post = ffs.id_staff_post) 
    """
    conditions = []
    params = []

    if fio:
        conditions.append("s.fio ILIKE %s")
        params.append(f"%{fio}%")
    if faculty:
        conditions.append("ffs.faculty_name ILIKE %s")
        params.append(f"%{faculty}%")
    if site:
        conditions.append("ffs.site ILIKE %s")
        params.append(f"%{site}%")
    if score_date:
        conditions.append("ffs.score_date::date = %s")
        params.append(score_date)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    cur.execute(query, params)

    faculty = [
        {
            "id": r[0],
            "fio": r[1],
            "faculty_name": r[2],
            "criteria": r[3],
            "site": r[4],
            "score": r[5],
            "score_date": r[6],
        }
        for r in cur.fetchall()
    ]

    cur.close()
    conn.close()
    return jsonify(faculty)

#DELETE запросы 

#Удаление баллов студентов
@house_admin_bp.route("/faculty/student/score/<int:id>", methods=["DELETE"])
def delete_faculty_student_score(id):
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM practical.faculty_student_score WHERE id = %s", (id,))
        conn.commit()
        return jsonify({'status': 'Запись удалена'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


#Удаление баллов факультетов
@house_admin_bp.route("/faculty/faculty/score/<int:id>", methods=["DELETE"])
def delete_faculty_faculty_score(id):
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM practical.faculty_faculty_score WHERE id = %s", (id,))
        conn.commit()
        return jsonify({'status': 'Запись удалена'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()