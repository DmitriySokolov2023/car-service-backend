from flask import Blueprint, jsonify, request
import psycopg2
from config import CONNECT_DB
from app.utils.system_house.get_school_year import school_working_year
from datetime import datetime, timedelta
import psycopg2.extras
from app.db import db_pool

form_training_mc = Blueprint("form-training-mc", __name__)


@form_training_mc.route("/", methods=["GET"])
def get_questions_mc():
    conn = db_pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                q.id AS question_id,
                q.main_text,
                q.sub_text,
                q.is_many,
                q.is_order,
                a.id AS answer_id,
                a.name AS answer_text,
                a.short_name AS short_name
            FROM practical.teacher_training_testing_question q
            JOIN practical.teacher_training_testing_answer a
                ON q.id = a.id_quest
            WHERE q.id_block = 3 AND a.display IS TRUE AND q.display IS TRUE
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
                    "sub_text": row["sub_text"],
                    "is_many": row["is_many"],
                    "is_order": row["is_order"],
                    "answers": []
                }
            questions_dict[qid]["answers"].append({
                "value": row["answer_id"],
                "label": row["answer_text"],
                "short_name": row["short_name"]
            })

        return jsonify(list(questions_dict.values()))
    finally:
        db_pool.putconn(conn)


# POST
@form_training_mc.route("/save", methods=["POST"])
def save_training_mc():
    data = request.get_json()
    if not isinstance(data, list) or not data:
        return jsonify({"error": "Ожидался массив объектов"}), 400

    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        values = [(row["id_staff"], row["id_question"], row["answer"]) for row in data]

        # Batch insert
        cur.executemany("""
            INSERT INTO practical.teacher_training_testing_result
                (id_staff, id_question, answer)
            VALUES (%s, %s, %s)
        """, values)

        conn.commit()
        cur.close()
        return jsonify({"status": "ok"}), 201

    except Exception as e:
        conn.rollback()
        cur.close()
        return jsonify({"error": str(e)}), 500

    finally:
        db_pool.putconn(conn)