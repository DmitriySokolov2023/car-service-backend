from flask import Blueprint, jsonify, request
import psycopg2
from config import CONNECT_DB
from app.utils.system_house.get_school_year import school_working_year
from datetime import datetime, timedelta
import psycopg2.extras
from app.db import db_pool

form_training_fb = Blueprint("form-training-fb", __name__)


@form_training_fb.route("/", methods=["GET"])
def get_questions_fb():
    conn = db_pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT 
                q.id AS question_id,
                q.main_text,
                q.sub_text,
                q.is_many,
                q.display,
                q.is_order,
                a.id AS answer_id,
                a.name AS answer_text
            FROM practical.teacher_training_testing_question q
            JOIN practical.teacher_training_testing_answer a
                ON q.id = a.id_quest
            WHERE q.id_block = 2 and a.display is True and q.display is True 
            ORDER BY q.id, a.id
        """)

        rows = cur.fetchall()
        cur.close()


        questions_dict = {}
        for row in rows:
            qid = row["question_id"]
            if qid not in questions_dict:
                questions_dict[qid] = {
                    "id": qid,
                    "main_text": row["main_text"],
                    "sub_text": row["sub_text"],   # ✅ не дублируется
                    "is_many": row["is_many"],
                    "display": row["display"],
                    "is_order": row["is_order"],
                    "answers": []
                }
            questions_dict[qid]["answers"].append({
                "value": row["answer_id"],
                "label": row["answer_text"]
            })

        return jsonify(list(questions_dict.values()))
    finally:
        db_pool.putconn(conn)


#POST
@form_training_fb.route("/save", methods=["POST"])
def post_answer_fb():
    data = request.get_json()
    if not isinstance(data, list) or not data:
        return jsonify({"error": "Ожидался массив объектов"}), 400

    conn = db_pool.getconn()  # берем соединение из пула
    try:
        cur = conn.cursor()
        # Формируем список кортежей для batch insert
        values = [
            (
                row.get("id_post"),
                row.get("site"),
                row.get("id_answer"),
                row.get("comment")
            )
            for row in data
        ]

        # Batch insert
        cur.executemany("""
            INSERT INTO practical.teacher_training_testing_result_os
                (id_post, site, id_answer, comment)
            VALUES (%s, %s, %s, %s)
        """, values)

        conn.commit()
        cur.close()
        return jsonify({"status": "ok"}), 201

    except Exception as e:
        conn.rollback()
        cur.close()
        return jsonify({"error": str(e)}), 500

    finally:
        db_pool.putconn(conn)  # возвращаем соединение в пул