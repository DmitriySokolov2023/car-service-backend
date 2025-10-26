from flask import Blueprint, request, jsonify
import psycopg2
import psycopg2.extras
from app.db import db_pool
main_social_status_bp = Blueprint('main_social_status_bp', __name__)

@main_social_status_bp.route("/questions", methods=["GET"], strict_slashes=False)
def get_social_status_questions():
    # Подключаемся к базе
    conn = db_pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                ssa.id AS answer_id,
                ssa.main_text AS answer_text,
                ssa.id_question,
                ssa.route,
                ssq.main_text AS question_text,
                ssq.is_many
            FROM practical.social_status_answer AS ssa
            JOIN practical.social_status_question AS ssq
                ON ssq.id = ssa.id_question
            WHERE ssq.display = TRUE
            ORDER BY ssa.id_question ASC, ssa.id ASC
        """)

        rows = cur.fetchall()
        cur.close()

        # Группируем по вопросу
        questions_dict = {}
        for row in rows:
            qid = row["id_question"]
            if qid not in questions_dict:
                questions_dict[qid] = {
                    "id": qid,
                    "main_text": row["question_text"],
                    "is_many": row["is_many"],
                    "answers": []
                }

            # Добавляем ответ
            questions_dict[qid]["answers"].append({
                "value": row["answer_id"],
                "label": row["answer_text"],
                "route": row["route"]  # массив bigint[]
            })
        
        return jsonify(list(questions_dict.values())), 200

    except Exception as e:
        print(f"Error fetching social status questions: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db_pool.putconn(conn)
        


@main_social_status_bp.route("/save", methods=["POST"])
def save_social_status_result():
    data = request.get_json()
    id_student = data.get("id_student")
    if not id_student:
        return jsonify({"error": "id_student обязателен"}), 400

    conn = db_pool.getconn()
    try:
        cur = conn.cursor()

        # Проверяем, есть ли записи
        cur.execute("SELECT COUNT(*) FROM practical.social_status_result WHERE id_student = %s", (id_student,))
        exists = cur.fetchone()[0] > 0

        # Разворачиваем данные формы
        insert_values = []
        for key, value in data.items():
            if key.startswith("answer_"):
                id_question = int(key.split("_")[1])
                id_answer = value if isinstance(value, list) else [value]
                insert_values.append((id_student, id_question, id_answer))

        if exists:
            # Если есть — обновляем
            for val in insert_values:
                cur.execute("""
                    UPDATE practical.social_status_result
                    SET id_answer = %s
                    WHERE id_student = %s AND id_question = %s
                """, (val[2], val[0], val[1]))
        else:
            # Если нет — вставляем
            cur.executemany("""
                INSERT INTO practical.social_status_result (id_student, id_question, id_answer)
                VALUES (%s, %s, %s)
            """, insert_values)

        conn.commit()
        cur.close()
        return jsonify({"status": "ok", "mode": "update" if exists else "insert", "count": len(insert_values)}), 200

    except Exception as e:
        conn.rollback()
        print(f"Error saving social status result: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db_pool.putconn(conn)


@main_social_status_bp.route("/results/<int:id_student>", methods=["GET"])
def get_social_status_result(id_student):
    conn = db_pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id_question, id_answer
            FROM practical.social_status_result
            WHERE id_student = %s
        """, (id_student,))
        rows = cur.fetchall()
        cur.close()

        # Преобразуем в структуру вроде { answer_1: [2,3], answer_2: [5], ... }
        result = {}
        for row in rows:
            key = f"answer_{row['id_question']}"
            val = row['id_answer']  # bigint[] или одиночное значение

            # Для первых двух вопросов оставляем как число (если массив с одним         элементом — берем первый)
            if row['id_question'] in [1, 2]:
                if isinstance(val, list) and len(val) > 0:
                    result[key] = val[0]
                else:
                    result[key] = val
            else:
                # Для остальных вопросов всегда массив
                result[key] = val if isinstance(val, list) else [val]

        return jsonify(result), 200

    except Exception as e:
        print(f"Error fetching social status results: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db_pool.putconn(conn)