from flask import Blueprint, jsonify, request
import psycopg2
from config import CONNECT_DB
from datetime import datetime, timedelta
import psycopg2.extras
from app.utils.system_house.get_school_year import school_working_year
import uuid
search_bp = Blueprint("search", __name__)

@search_bp.route("/all/search")
def search_all():
    query = request.args.get("q", "").strip()
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
    SELECT s.id_staff, s.fio, p.post, p.division FROM practical.staff as s
JOIN practical.staff_posts as sp
ON sp.id_staff = s.id_staff
JOIN practical.posts as p
ON p.id_post = sp.id_post
where sp.date_end is null
      AND fio ILIKE %s
""", (f"%{query}%",))

    all = cur.fetchall()

    cur.close()
    conn.close()
    return jsonify({"all": all})

@search_bp.route("/visitor/search")
def search_visitor():
    query = request.args.get("q", "").strip()
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
    SELECT s.id_staff, fio, COALESCE(p.post,'') AS post, COALESCE(p.division,'') AS division
    FROM practical.staff as s
    LEFT JOIN practical.staff_posts as sp ON s.id_staff = sp.id_staff
    LEFT JOIN practical.posts as p ON p.id_post = sp.id_post
    LEFT JOIN practical.supervisor_attending_classes as sac ON sac.id_staff = s.id_staff
    WHERE date_end is null
      AND (post ILIKE %s OR sac.id_staff is not null)
      AND fio ILIKE %s
""", ('%учитель%', f"%{query}%"))

    employees = cur.fetchall()

    cur.close()
    conn.close()
    return jsonify({"employees": employees})






@search_bp.route("/teacher/search")
def search_teacher():
    query = request.args.get("q", "").strip()
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id_staff, fio, p.post, p.division FROM practical.staff as s
        LEFT JOIN practical.staff_posts as sp
        ON s.id_staff = sp.id_staff
        LEFT JOIN practical.posts as p
        ON p.id_post = sp.id_post
        WHERE date_end is null AND post ilike %s and s.fio ILIKE %s
        ORDER BY id_staff ASC
    """, ('%учитель%', f"%{query}%"))
    teacher = [{"id_staff": r[0], "fio": r[1], "post": r[2], "division":r[3]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({"teacher": teacher})


@search_bp.route("/teacher/search/tutor")
def search_teacher_tutor():
    query = request.args.get("q", "").strip()
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id_staff, fio, p.post, p.division FROM practical.staff as s
        LEFT JOIN practical.staff_posts as sp
        ON s.id_staff = sp.id_staff
        LEFT JOIN practical.posts as p
        ON p.id_post = sp.id_post
        WHERE date_end is null AND (post ILIKE %s OR post ILIKE %s)  and s.fio ILIKE %s
        ORDER BY id_staff ASC
    """, ('%учитель%','%тьютор%', f"%{query}%"))
    teacher = [{"id_staff": r[0], "fio": r[1], "post": r[2], "division":r[3]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({"teacher": teacher})

@search_bp.route("/student/search")
def search_student():
    query = request.args.get("q", "").strip()
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id_student_class, fio, CONCAT(course, '-', liter,site) as class, faculty FROM practical.students_classes as sc
        LEFT JOIN practical.students as s
        ON s.id_student = sc.id_student
        LEFT JOIN practical.classes as c
        ON c.id_class = sc.id_class
        WHERE course > 4 AND course < 9 AND date_end is null AND fio ILIKE %s
    """, (f"%{query}%",))

    student = [{"id_student_class": r[0], "fio": r[1], "class": r[2], "faculty":r[3]} for r in cur.fetchall()]

    cur.close()
    conn.close()
    return jsonify({"student": student})

@search_bp.route("/student/all/search")
def search_student_all():
    query = request.args.get("q", "").strip()
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id_student_class, fio, CONCAT(course, '-', liter,site) as class, faculty FROM practical.students_classes as sc
        LEFT JOIN practical.students as s
        ON s.id_student = sc.id_student
        LEFT JOIN practical.classes as c
        ON c.id_class = sc.id_class
        WHERE date_end is null AND fio ILIKE %s
    """, (f"%{query}%",))

    student = [{"id_student_class": r[0], "fio": r[1], "class": r[2], "faculty":r[3]} for r in cur.fetchall()]

    cur.close()
    conn.close()
    return jsonify({"student": student})


@search_bp.route("/classes/search")
def search_classes():
    query = request.args.get("q", "").strip()
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id_class, CONCAT(course,'-',liter,site) as class FROM practical.classes
        WHERE CONCAT(course,'-',liter,site) ILIKE %s
    """, (f"{query}%",))

    classes = [{"id_class": r[0], "class": r[1]} for r in cur.fetchall()]

    cur.close()
    conn.close()
    return jsonify({"classes": classes})


@search_bp.route("/subjects/search")
def search_subjects():
    query = request.args.get("q", "").strip()
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id_subject, subject_name FROM practical.subject
        WHERE subject_name ILIKE %s
    """, (f"{query}%",))

    subjects = [{"id_subject": r[0], "subject_name": r[1]} for r in cur.fetchall()]

    cur.close()
    conn.close()
    return jsonify({"subjects": subjects})