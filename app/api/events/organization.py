from flask import Blueprint, jsonify, request
import psycopg2
from config import CONNECT_DB
from app.utils.system_house.get_school_year import school_working_year
from datetime import datetime, timedelta
import psycopg2.extras


organizations_bp = Blueprint("organizations", __name__)


@organizations_bp.route("/get", methods=["GET"])
def get_organizations():
    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name
            FROM practical.olympics_organization
            ORDER BY id ASC;
        """)
        rows = cur.fetchall()

        organizations = [
            {"value": r[0], "label": r[1]}
            for r in rows
        ]

        cur.close()
        conn.close()

        return jsonify(organizations), 200

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

@organizations_bp.route("/save", methods=["POST"])
def add_organization():
    data = request.get_json()

    # Проверяем входные данные
    if not isinstance(data, dict) or not data.get("name"):
        return jsonify({"error": "Поле 'name' обязательно"}), 400

    name = data["name"].strip()

    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()

        # Вставляем запись (id создаётся автоматически)
        cur.execute("""
            INSERT INTO practical.olympics_organization (name)
            VALUES (%s);
        """, (name,))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "status": "ok",
            "message": f"Организация '{name}' успешно добавлена"
        }), 201

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500
    
@organizations_bp.route("/delete/<int:org_id>", methods=["DELETE"])
def delete_organization(org_id):
    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()

        # Проверяем, используется ли организация в олимпиадах
        cur.execute("""
            SELECT COUNT(*) 
            FROM practical.olympics_event 
            WHERE id_organizer = %s
        """, (org_id,))
        count = cur.fetchone()[0]

        if count > 0:
            # Организация используется — не удаляем
            return jsonify({
                "error": "Невозможно удалить организацию: она задействована в олимпиадах"
            })

        # Если не используется — удаляем
        cur.execute(
            "DELETE FROM practical.olympics_organization WHERE id = %s",
            (org_id,)
        )
        conn.commit()
        return jsonify({"status": "ok", "deleted_id": org_id}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()


@organizations_bp.route("/update/<int:org_id>", methods=["PUT"])
def update_organization(org_id):
    conn = psycopg2.connect(CONNECT_DB)
    try:
        data = request.get_json()
        new_name = data.get("name")

        if not new_name or not new_name.strip():
            return jsonify({"error": "Название организации не может быть пустым"}), 400

        cur = conn.cursor()

        # Проверяем, существует ли организация
        cur.execute("""
            SELECT COUNT(*) 
            FROM practical.olympics_organization 
            WHERE id = %s
        """, (org_id,))
        exists = cur.fetchone()[0]

        if not exists:
            return jsonify({"error": "Организация не найдена"}), 404

        # Обновляем название
        cur.execute("""
            UPDATE practical.olympics_organization
            SET name = %s
            WHERE id = %s
        """, (new_name.strip(), org_id))

        conn.commit()
        return jsonify({
            "status": "ok",
            "updated_id": org_id,
            "new_name": new_name.strip()
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()
