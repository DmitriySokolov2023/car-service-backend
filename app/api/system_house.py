from flask import Blueprint, jsonify, request
import psycopg2
from config import CONNECT_DB
from datetime import datetime, timedelta
import psycopg2.extras
from app.utils.system_house.get_school_year import school_working_year
import uuid

house_bp = Blueprint("system-house", __name__)



#GET запросы

#Поиск отправителей
@house_bp.route("/faculty/sender", methods=["GET"])
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



#Получение факультетов 
@house_bp.route("/faculty", methods=["GET"])
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





#POST запросы
#Отправка баллов студенту
@house_bp.route("/faculty/student/score", methods=["POST"])
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
    
#Отправка баллов факультету
@house_bp.route("/faculty/faculty/score", methods=["POST"])
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
    


