from flask import Blueprint, jsonify, request
import psycopg2
from config import CONNECT_DB
from datetime import datetime, timedelta
import psycopg2.extras
from app.utils.system_house.get_school_year import school_working_year
import uuid
from app.db import db_pool
motivation_bp = Blueprint("motivation", __name__)


# GET
@motivation_bp.route("/motivations/post", methods=["GET"])
def get_motivation_post():
    query = request.args.get("q", "").strip()
    conn = db_pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT DISTINCT p.id_post, p.post, p.division
            FROM practical.posts AS p
            LEFT JOIN practical.staff_posts AS sp
            ON p.id_post = sp.id_post
            WHERE sp.date_end IS NULL AND post ILIKE %s
        """, (f"%{query}%",))
        
        post = [
            {
                "id_post": r["id_post"],
                "post": r["post"],
                "division": r["division"]
            }
            for r in cur.fetchall()
        ]
        cur.close()
        return jsonify(post)
    finally:
        db_pool.putconn(conn)


# POST
@motivation_bp.route("/motivations/save", methods=["POST"])
def save_motivation_score():
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({"error": "Ожидался массив объектов"}), 400

    common_id_human = str(uuid.uuid4())
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        values = [
            (
                row.get("id_post"),
                row.get("subject"),
                row.get("score_1"),
                row.get("score_2"),
                row.get("part"),
                row.get("block"),
                row.get("number_question"),
                row.get("experience"),
                common_id_human
            )
            for row in data
        ]
        cur.executemany("""
            INSERT INTO practical.digitalization_testing_1
                (id_post, subject, score_1, score_2, part, block, number_question, experience, id_human) 
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
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