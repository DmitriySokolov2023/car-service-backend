from flask import Blueprint, jsonify, request
import psycopg2
import pandas as pd
from config import CONNECT_DB
from app.utils.system_house.get_school_year import school_working_year
from datetime import datetime, timedelta
import psycopg2.extras
from app.db import db_pool

main_form_survey_bp = Blueprint("main_from_survey_pb", __name__)


@main_form_survey_bp.route("/questions", methods=["GET"])
def get_main_survey_questions():
    id_survey = request.args.get("id_survey", type=int)
    if not id_survey:
        return jsonify({"error": "id_survey parameter is required"}), 400

    conn = db_pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                sq.id AS question_id,
                sq.main_text,
                sq.sub_text,
                sq.is_many,
                sq.is_order,
                sq.is_text,
                sq.display AS question_display,
                sa.id AS answer_id,
                sa.name AS answer_text,
                sa.short_name AS short_name,
                sb.id AS block_id,
                sb.name AS block_name
            FROM practical.survey_question AS sq
            LEFT JOIN practical.survey_answer AS sa
                ON sa.id_question = sq.id
                AND sa.display IS TRUE
            LEFT JOIN practical.survey_block AS sb
                ON sb.id = sq.id_block
            WHERE sb.id_survey = %s
              AND sq.display IS TRUE
            ORDER BY sb.id, sq.id, sa.id
        """, (id_survey,))

        rows = cur.fetchall()
        cur.close()

        # Группируем вопросы
        questions_dict = {}
        for row in rows:
            qid = row["question_id"]
            if qid not in questions_dict:
                questions_dict[qid] = {
                    "id": qid,
                    "block_id": row["block_id"],
                    "block_name": row["block_name"],
                    "main_text": row["main_text"],
                    "sub_text": row["sub_text"],
                    "is_many": row["is_many"],
                    "is_order": row["is_order"],
                    "is_text": row["is_text"],
                    
                    "display": row["question_display"],
                    "answers": []
                }

            # Добавляем ответы, если есть
            if row.get("answer_id") and row.get("answer_text"):
                questions_dict[qid]["answers"].append({
                    "value": row["answer_id"],
                    "label": row["answer_text"],
                    "short_name": row["short_name"]

                })

        # Преобразуем в массив
        return jsonify(list(questions_dict.values()))

    except Exception as e:
        print(f"Error fetching survey questions: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db_pool.putconn(conn)


@main_form_survey_bp.route("/save", methods=["POST"])
def save_main_survey():
    data = request.get_json()
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "Ожидался JSON объект"}), 400

    conn = db_pool.getconn()
    try:
        cur = conn.cursor()

        # Универсальные данные
        id_staff = data.get("id_staff")
        id_subject = data.get("id_subject")
        id_teacher = data.get("id_teacher")
        id_student = data.get("id_student")
        id_post = data.get("id_post")
        site = data.get("site")

        # --- 🔹 Ключевая логика: class_id > class ---
        id_class = None
        _class = None
        if "id_class" in data:
            id_class = data.get("id_class")
        elif "class" in data:
            _class = data.get("class")

        insert_values = []

        # Проходим по всем ключам формы
        for key, value in data.items():

            # === 1️⃣ Ответы с множественным выбором ===
            if key.startswith("answer_") and not key.startswith(("answer_order_", "answer_text_")):
                id_question = int(key.split("_")[1])
                answers = value if isinstance(value, list) else [value]
                answers_sorted = sorted(answers)
                insert_values.append((
                    id_staff,
                    id_question,
                    answers_sorted,
                    None,
                    id_subject,
                    id_class,
                    id_teacher,
                    id_student,
                    id_post,
                    _class,
                    site
                ))

            # === 2️⃣ Ответы с порядком (массив приходит напрямую) ===
            elif key.startswith("answer_order_"):
                id_question = int(key.split("_")[2]) if key.startswith("answer_order_") else int(key.split("_")[1])
                answers_ordered = value if isinstance(value, list) else [value]

                insert_values.append((
                    id_staff,
                    id_question,
                    answers_ordered,
                    None,
                    id_subject,
                    id_class,
                    id_teacher,
                    id_student,
                    id_post,
                    _class,
                    site
                ))

            # === 3️⃣ Текстовые ответы ===
            elif key.startswith("answer_text_"):
                id_question = int(key.split("_")[2]) if key.startswith("answer_text_") else int(key.split("_")[1])
                insert_values.append((
                    id_staff,
                    id_question,
                    None,
                    value.strip() if value else None,
                    id_subject,
                    id_class,
                    id_teacher,
                    id_student,
                    id_post,
                    _class,
                    site
                ))

        # ✅ Массовая вставка
        cur.executemany("""
            INSERT INTO practical.survey_result
                (id_staff, id_question, id_answer, answer, id_subject, id_class, id_teacher, id_student, id_post, class, site)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, insert_values)

        conn.commit()
        cur.close()
        return jsonify({"status": "ok", "inserted": len(insert_values)}), 201

    except Exception as e:
        conn.rollback()
        print(f"Error saving survey: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        db_pool.putconn(conn)


@main_form_survey_bp.route("/general", methods=["GET"])
def get_main_survey_general():
    id_survey = request.args.get("id_survey", type=int)
    if not id_survey:
        return jsonify({"error": "id_survey parameter is required"}), 400

    conn = db_pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                sg.id,
                sg.name,
                sg.is_teacher,
                sg.is_class,
                sg.is_subject,
                sg.is_course
            FROM practical.survey_general AS sg
            WHERE sg.id = %s
        """, (id_survey,))
        row = cur.fetchone()
        cur.close()

        if not row:
            return jsonify({"error": "Survey not found"}), 404

        return jsonify(row)

    except Exception as e:
        print(f"Error fetching survey general: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        db_pool.putconn(conn)


@main_form_survey_bp.route("/general/info", methods=["GET"])
def get_main_survey_general_info():
    # id_survey = request.args.get("id_survey", type=int)
    # if not id_survey:
    #     return jsonify({"error": "id_survey parameter is required"}), 400

    conn = db_pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                sg.id,
                sg.name
            FROM practical.survey_general AS sg
        """)
        row = cur.fetchall()
        cur.close()

        if not row:
            return jsonify({"error": "Survey not found"}), 404

        return jsonify(row)

    except Exception as e:
        print(f"Error fetching survey general: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        db_pool.putconn(conn)