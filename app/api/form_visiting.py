from flask import Blueprint, jsonify, request
import psycopg2
from config import CONNECT_DB
from app.utils.system_house.get_school_year import school_working_year
from datetime import datetime, timedelta
visiting_bp = Blueprint("form-visiting", __name__, url_prefix="/api/form-visiting")

visiting_save_bp = Blueprint("form-visiting-save", __name__)

@visiting_bp.route("/questions")
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


@visiting_save_bp.route("/attending/save", methods=["POST"])
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