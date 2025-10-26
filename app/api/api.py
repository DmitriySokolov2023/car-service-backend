from flask import Blueprint, jsonify, request
import psycopg2
from config import CONNECT_DB
from datetime import datetime, timedelta
import psycopg2.extras
from app.utils.system_house.get_school_year import school_working_year
import uuid
api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/form-visiting/questions")
def get_data_form_visiting():
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()
    cur.execute("""
       SELECT 
            b.id_block_attending_classes AS block_id,
            b.main_text AS block_main_text,
            b.sub_text AS block_sub_text,
            b.number_block,
            q.id_question,
            q.main_text AS question_text,
            q.max_score
        FROM practical.block_attending_classes b
        LEFT JOIN practical.question_attending_classes q 
            ON b.id_block_attending_classes = q.id_block
            AND q.display = TRUE
        WHERE b.display = TRUE
        ORDER BY b.number_block, q.id_question;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    block = {}
    for block_id, block_main, block_sub, number_block, q_id, q_text, max_score in rows:
        if block_id not in block:
            block[block_id] = {
                "id": block_id,
                "main_text": block_main,
                "sub_text": block_sub,
                "number_block": number_block,
                "questions": []
            }
        if q_id: 
            block[block_id]["questions"].append({
                "id": q_id,
                "text": q_text,
                "max_score": max_score
            })
    return jsonify({'block':list(block.values())}) 

@api_bp.route("/visitor/search")
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

@api_bp.route("/teacher/search")
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



@api_bp.route("/student/search")
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




@api_bp.route("/attending/save", methods=["POST"])
def save_attending():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Нет данных"}), 400

    id_staff = data.get("id_staff")
    id_teacher = data.get("id_teacher")
    subject = data.get("subject")
    class_num = data.get("class")
    flag = data.get("flag")
    comment = data.get("comment", "").strip()
    date_now = datetime.now().date()
    

    questions = {k: v for k, v in data.items() if k.startswith("question_")}

    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    try:
        # 1️⃣ Если есть комментарий — сохраняем его
        id_comment = None
        if comment and comment.strip():
            cur.execute(
                """
                INSERT INTO practical.comment_attending_classes (comment)
                VALUES (%s)
                RETURNING id
                """,
                (comment,)
            )
            id_comment = cur.fetchone()[0]

        # 2️⃣ Удаляем старые записи за тот же день
        cur.execute("""
            DELETE FROM practical.result_attending_classes
            WHERE id_staff = %s
              AND id_teacher = %s
              AND class = %s
              AND DATE(date) = %s
        """, (id_staff, id_teacher, class_num, date_now))

        # 3️⃣ Сохраняем ответы по вопросам
        for q_key, score in questions.items():
            q_id = int(q_key.split("_")[1])
            cur.execute("""
                INSERT INTO practical.result_attending_classes 
                    (id_staff, id_teacher, id_question, score, subject, class, date, id_comment,flag)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (id_staff, id_teacher, q_id, score, subject, class_num, date_now, id_comment, flag))

        conn.commit()

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cur.close()
    conn.close()
    return jsonify({"status": "ok"}), 201


#ФИКСАЦИЯ БАЛЛОВ
@api_bp.route("/faculty/sender")
def search_sender():
    query = request.args.get("q", "").strip()
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    cur.execute("""
                
WITH s as (
  SELECT sp.id_staff_post, fio, p.post, p.division, fst.role, fst.max_score, COALESCE(fss.score,0) as score
  FROM practical.staff as s
  LEFT JOIN practical.staff_posts as sp
  ON s.id_staff = sp.id_staff
  LEFT JOIN practical.posts as p
  ON p.id_post = sp.id_post
  LEFT JOIN practical.faculty_supervisor as fst
  ON fst.id_post = sp.id_post
  LEFT JOIN practical.faculty_student_score as fss
  ON fss.id_staff_post = sp.id_staff_post
  WHERE date_end is null AND fst.id_post is not null 
  AND COALESCE(fss.score,0) >= 0 AND COALESCE(fss.spend, true) = True 
    AND fio ilike %s
  AND (fss.school_year = 2025 or fss.school_year is null)),
  
f as (SELECT sp.id_staff_post, fio, p.post, p.division, fs.role, fs.max_score, fss.score as score
  FROM practical.staff as s
  LEFT JOIN practical.staff_posts as sp
  ON s.id_staff = sp.id_staff
  LEFT JOIN practical.posts as p
  ON p.id_post = sp.id_post
  LEFT JOIN practical.faculty_supervisor as fs
  ON fs.id_post = sp.id_post
  LEFT JOIN practical.faculty_faculty_score as fss
  ON fss.id_staff_post = sp.id_staff_post
  WHERE date_end is null AND COALESCE(fss.spend, true) = True AND fs.id_post is not null 
  AND COALESCE(fss.score,0) >= 0  
    AND fio ilike %s
  AND (fss.school_year = 2025 or fss.school_year is null))

SELECT id_staff_post, fio, post, division, role, (max_score - COALESCE(SUM(score),0)) as score FROM (
SELECT  * FROM s
UNION ALL 
SELECT * FROM f) as h1
GROUP BY id_staff_post, fio, post, division, max_score, role
    """, (f"%{query}%", f"%{query}%"))

    sender = [{"id_staff_post": r[0], "fio": r[1], "post": r[2], "division":r[3], "role":r[4],"score":r[5]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({"sender": sender})



@api_bp.route("/faculty/student/score", methods=["POST"])
def save_faculty_student_score():
    
    try:
        data = request.get_json()
        school_year = school_working_year()
        id_student_class = data.get('id_student_class')
        id_staff = data.get('id_staff_post')
        criteria = data.get('criteria')
        score = data.get('score')
        score_date = data.get('score_date')
        criteria_type = data.get('criteria_type') 
        
        
        if not all([id_student_class, id_staff, criteria, score, score_date]):
            return jsonify({"error": "Missing required fields"}), 400
        
        conn = psycopg2.connect(CONNECT_DB)
        cur = conn.cursor()
        
        # Сначала удаляем старую запись
        # cur.execute("""
        #     DELETE FROM practical.faculty_student_score 
        #     WHERE id_student_class = %s 
        #       AND id_staff = %s 
        #       AND score_date = %s
        # """, (id_student_class, id_staff, score_date))
        
        # Затем вставляем новую
        cur.execute("""
            INSERT INTO practical.faculty_student_score 
                (id_student_class, id_staff_post, criteria, score, score_date, spend, school_year)
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (id_student_class, id_staff, criteria, score, score_date, criteria_type, school_year))
        
        result = cur.fetchone()
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Data saved successfully",
            "data": {
                "id_student_class": result[0],
                "id_staff": result[1],
                "criteria": result[2],
                "score": result[3],
                "score_date": result[4],
                "criteria_type": result[5],
                "school_year": result[5]
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/faculty/faculty/score", methods=["POST"])
def save_faculty_faculty_score():
    try:
        data = request.get_json()
        school_year = school_working_year()
        faculty_name = data.get('faculty_name')
        id_staff = data.get('id_staff_post')
        criteria = data.get('criteria')
        score = data.get('score')
        score_date = data.get('score_date')
        criteria_type = data.get('criteria_type') 
        site = data.get('site') 
       
        
        if not all([faculty_name, id_staff, criteria, score, score_date]):
            return jsonify({"error": "Missing required fields"}), 400
        
        conn = psycopg2.connect(CONNECT_DB)
        cur = conn.cursor()
        
        # Сначала удаляем старую запись
        # cur.execute("""
        #     DELETE FROM practical.faculty_faculty_score 
        #     WHERE faculty_name = %s 
        #       AND id_staff = %s 
        #       AND score_date = %s
        # """, (faculty_name, id_staff, score_date))
        
        # Затем вставляем новую
        cur.execute("""
            INSERT INTO practical.faculty_faculty_score 
                (faculty_name, id_staff_post, criteria, score, score_date, spend, school_year, site)
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (faculty_name, id_staff, criteria, score, score_date, criteria_type, school_year,site))
        
        result = cur.fetchone()
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Data saved successfully",
            "data": {
                "faculty_name": result[0],
                "id_staff": result[1],
                "criteria": result[2],
                "score": result[3],
                "score_date": result[4],
                "criteria_type": result[5]
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


@api_bp.route("/faculty", methods=["GET"])
def get_faculty():
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT distinct faculty FROM practical.students
        WHERE faculty is not null
    """)
    

    faculty = [{"value": r[0], "label": r[0]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(faculty)



@api_bp.route("/faculty/student/score", methods=["GET"])
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


@api_bp.route("/faculty/student/score/<int:id>", methods=["DELETE"])
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

@api_bp.route("/faculty/faculty/score/<int:id>", methods=["DELETE"])
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

@api_bp.route("/faculty/faculty/score", methods=["GET"])
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

@api_bp.route("/motivations/save", methods=["POST"])
def save_motivation_score():
    data = request.get_json()  # тут data = list
    if not isinstance(data, list):
        return jsonify({"error": "Ожидался массив объектов"}), 400
    common_id_human = str(uuid.uuid4())
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    for row in data:
        cur.execute("""
            INSERT INTO practical.digitalization_testing_1
                (id_post, subject, score_1, score_2, part, block, number_question, experience, id_human) 
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            row.get("id_post"),
            row.get("subject"),
            row.get("score_1"),
            row.get("score_2"),
            row.get("part"),
            row.get("block"),
            row.get("number_question"),
            row.get("experience"),
            common_id_human
        ))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "ok"}), 201


@api_bp.route("/motivations/post", methods=["GET"])
def get_motivation_post():
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()
    query = request.args.get("q", "").strip()
    cur.execute("""
        SELECT distinct p.* 
        FROM practical.posts as p
        LEFT JOIN practical.staff_posts as sp
        ON p.id_post = sp.id_post
        WHERE sp.date_end is null and post ilike %s
    """, (f"%{query}%",))
    
    post = [
        {
            "id_post": r[0],
            "post": r[1],
            "division": r[2]
        }
        for r in cur.fetchall()
    ]
    cur.close()
    conn.close()
    return jsonify(post)