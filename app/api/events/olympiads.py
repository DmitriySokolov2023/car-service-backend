from flask import Blueprint, jsonify, request, send_file
import psycopg2
from config import CONNECT_DB
from app.utils.system_house.get_school_year import school_working_year
from datetime import datetime, timedelta
import psycopg2.extras
from io import BytesIO
import pandas as pd

olympiads_bp = Blueprint("olympiads", __name__)


@olympiads_bp.route("/get", methods=["GET"])
def get_olympiads():
    conn = psycopg2.connect(CONNECT_DB)
    try:
        category = request.args.get("category")  # например, "students"

        cur = conn.cursor()

        # Базовый SQL
        base_query = """
            SELECT 
                oe.id,
                oe.main_name,
                oe.id_subject,
                s.subject_name,
                oe.passing_score,
                oe.class,
                oe.max_score,
                oe.school_year,
                oe.category,
                oe.id_level,
                ol.level,
                oe.id_organizer,
                oo.name
            FROM practical.olympics_event AS oe
            JOIN practical.subject AS s
                ON s.id_subject = oe.id_subject
            JOIN practical.olympics_levels AS ol
                ON oe.id_level = ol.id
            JOIN practical.olympics_organization AS oo
                ON oe.id_organizer = oo.id
        """

        # Добавляем WHERE, если category указана
        if category:
            base_query += " WHERE oe.category = %s"
            cur.execute(base_query + " ORDER BY oe.id DESC", (category,))
        else:
            cur.execute(base_query + " ORDER BY oe.id DESC")

        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]

        olympiads = [
            {colnames[i]: r[i] for i in range(len(colnames))}
            for r in rows
        ]

        cur.close()
        conn.close()
        return jsonify(olympiads), 200

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500


@olympiads_bp.route("/save", methods=["POST"])
def add_olympiad():
    data = request.get_json()

    def school_working_year():
        if (datetime.now().month < 8): return datetime.now().year - 1
        return datetime.now().year

    year = school_working_year()
    # Проверяем входные данные
    required_fields = [
        "main_name", "category", "class", "id_subject",
        "id_level", "id_organizer"
    ]
    missing = [f for f in required_fields if f not in data or data[f] in (None, "")]
    if missing:
        return jsonify({"error": f"Отсутствуют обязательные поля: {', '.join(missing)}"}), 400

    # Извлекаем значения
    main_name = data["main_name"].strip()
    category = data["category"].strip()
    class_num = data["class"]
    id_subject = data["id_subject"]
    id_level = data["id_level"]
    max_score = data["max_score"]
    passing_score = data["passing_score"]
    school_year = year
    id_organizer = data["id_organizer"]

    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO practical.olympics_event
                (main_name, category, class, id_subject, id_level, max_score, passing_score, school_year, id_organizer)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            main_name, category, class_num, id_subject, id_level,
            max_score, passing_score, school_year, id_organizer
        ))

        olymp_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "status": "ok",
            "message": f"Олимпиада '{main_name}' успешно добавлена",
            "id": olymp_id
        }), 201

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500
    

@olympiads_bp.route("/update", methods=["PUT"])
def update_olympiad():
    data = request.get_json()

    def school_working_year():
        if datetime.now().month < 8:
            return datetime.now().year - 1
        return datetime.now().year

    year = school_working_year()

    # Проверяем наличие ID
    olympiad_id = data.get("id")
    if not olympiad_id:
        return jsonify({"error": "Отсутствует ID олимпиады для обновления"}), 400

    # Проверяем обязательные поля
    required_fields = [
        "main_name",
        "category",
        "class",
        "id_subject",
        "id_level",
        "id_organizer",
    ]

    missing = [f for f in required_fields if f not in data or data[f] in (None, "")]
    if missing:
        return jsonify(
            {"error": f"Отсутствуют обязательные поля: {', '.join(missing)}"}
        ), 400

    # Извлекаем значения
    main_name = data["main_name"].strip()
    category = data["category"].strip()
    class_num = data["class"]
    id_subject = data["id_subject"]
    id_level = data["id_level"]
    max_score = data["max_score"]
    passing_score = data["passing_score"]
    id_organizer = data["id_organizer"]
    school_year = year

    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE practical.olympics_event
            SET main_name = %s,
                category = %s,
                class = %s,
                id_subject = %s,
                id_level = %s,
                max_score = %s,
                passing_score = %s,
                id_organizer = %s,
                school_year = %s
            WHERE id = %s
            RETURNING id;
            """,
            (
                main_name,
                category,
                class_num,
                id_subject,
                id_level,
                max_score,
                passing_score,
                id_organizer,
                school_year,
                olympiad_id,
            ),
        )
        updated = cur.fetchone()
        if not updated:
            conn.rollback()
            return jsonify({"error": f"Олимпиада с id={olympiad_id} не найдена"}), 404

        conn.commit()
        return jsonify(
            {
                "status": "ok",
                "message": f"Олимпиада '{main_name}' успешно обновлена",
                "id": olympiad_id,
            }
        ), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@olympiads_bp.route("/delete/<int:org_id>", methods=["DELETE"])
def delete_olympiad(org_id):
    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()

        # Проверяем, есть ли участники, привязанные к этой олимпиаде
        cur.execute("""
            SELECT COUNT(*)
            FROM practical.olympics_students_result
            WHERE id_olympic = %s
        """, (org_id,))
        count = cur.fetchone()[0]

        if count > 0:
            # Есть записи — нельзя удалять олимпиаду
            return jsonify({
                "error": "Сначала открепите участников!"
            })

        # Если участников нет — удаляем олимпиаду
        cur.execute(
            "DELETE FROM practical.olympics_event WHERE id = %s",
            (org_id,)
        )
        conn.commit()

        return jsonify({
            "status": "ok",
            "deleted_id": org_id
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cur.close()
        conn.close()


@olympiads_bp.route("/student/add", methods=["POST"])
def add_student_to_olympiad():
    data = request.get_json()
    id_olympic = data.get("id_olympic")
    id_student = data.get("id_student")

    if not id_olympic or not id_student:
        return jsonify({"error": "id_olympic и id_student обязательны"}), 400

    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        # Проверяем, не добавлен ли уже студент
        cur.execute(
            """
            SELECT id FROM practical.olympics_students_result
            WHERE id_olympic = %s AND id_student = %s
            """,
            (id_olympic, id_student)
        )
        exists = cur.fetchone()
        if exists:
            return jsonify({"error": "Студент уже добавлен"}), 400

        cur.execute(
            """
            INSERT INTO practical.olympics_students_result (id_olympic, id_student)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (id_olympic, id_student),
        )
        conn.commit()
        new_id = cur.fetchone()[0]
        return jsonify({"status": "ok", "id": new_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# Удалить студента из олимпиады
@olympiads_bp.route("/student/remove", methods=["DELETE"])
def remove_student_from_olympiad():
    data = request.get_json()
    id_olympic = data.get("id_olympic")
    id_student = data.get("id_student")

    if not id_olympic or not id_student:
        return jsonify({"error": "id_olympic и id_student обязательны"}), 400

    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM practical.olympics_students_result
            WHERE id_olympic = %s AND id_student = %s
            """,
            (id_olympic, id_student)
        )
        conn.commit()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@olympiads_bp.route("/student/added/<int:id_olympic>", methods=["GET"])
def get_olympiad_students(id_olympic):
    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id_student FROM practical.olympics_students_result WHERE id_olympic = %s",
            (id_olympic,)
        )
        rows = cur.fetchall()
        ids = [r[0] for r in rows]
        return jsonify(ids)
    finally:
        cur.close()
        conn.close()
@olympiads_bp.route("/student/added/count/<int:id_olympic>", methods=["GET"])
def get_olympiad_students_count(id_olympic):
    conn = psycopg2.connect(CONNECT_DB)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(DISTINCT id_student) FROM practical.olympics_students_result WHERE id_olympic = %s",
            (id_olympic,)
        )
        rows = cur.fetchall()
        
        return jsonify(rows)
    finally:
        cur.close()
        conn.close()

@olympiads_bp.route("/student/adding", methods=["GET"])
def get_student_adding():
    fio_student = request.args.get("fioStudent", "").strip()
    course = request.args.get("course", "").strip()
    liter = request.args.get("liter", "").strip()
    site = request.args.get("site", "").strip()
    id_olympic = request.args.get("id_olympic", "").strip()

    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    query = """
    SELECT 
            st.id_student,
            st.fio AS fio_student,
            c.course as course,
            c.liter as liter,
            c.site as site,
			osr.score,
			osr.status,
			osr.flag
        FROM practical.students AS st
        JOIN practical.students_classes AS sc 
            ON st.id_student = sc.id_student
        JOIN practical.classes AS c 
            ON sc.id_class = c.id_class
		JOIN practical.olympics_students_result as osr
		ON st.id_student = osr.id_student
        WHERE sc.date_end IS NULL
    """

    conditions = []
    params = []

    if id_olympic:
        conditions.append("osr.id_olympic = %s")
        params.append(id_olympic)
    if fio_student:
        conditions.append("st.fio ILIKE %s")
        params.append(f"%{fio_student}%")
    if course:
        conditions.append("CAST(c.course AS TEXT) = %s")
        params.append(course)
    if liter:
        conditions.append("c.liter = %s")
        params.append(liter)
    if site:
        conditions.append("c.site ILIKE %s")
        params.append(f"%{site}%")

    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += "ORDER BY course, liter, site asc LIMIT 100"

    cur.execute(query, params)
    rows = cur.fetchall()

    students = [{
        "id_student": r[0],
        "fio_student": r[1],
        "course": r[2],
        "liter": r[3],
        "site": r[4],
        "score": r[5],
        "status": r[6],
        "flag": r[7]
    } for r in rows]

    cur.close()
    conn.close()

    return jsonify(students)



@olympiads_bp.route("/student/update", methods=["POST"])
def update_students_results():
    from flask import request, jsonify
    import psycopg2

    data = request.get_json()

    if not isinstance(data, list) or not data:
        return jsonify({"error": "Ожидается массив студентов"}), 400

    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()

    updated = []
    not_found = []
    errors = []

    try:
        for item in data:
            id_olympic = item.get("id_olympic")
            id_student = item.get("id_student")
            score = item.get("score", None)
            status = item.get("status")

            if not id_olympic or not id_student:
                continue

            # Проверяем max_score олимпиады, только если score указан
            if score is not None:
                cur.execute(
                    """
                    SELECT max_score
                    FROM practical.olympics_event
                    WHERE id = %s
                    """,
                    (id_olympic,),
                )
                olympic_row = cur.fetchone()

                if olympic_row:
                    max_score = olympic_row[0]
                    if int(score) > max_score:
                        errors.append({
                            "id_student": id_student,
                            "id_olympic": id_olympic,
                            "message": f"Балл {score} превышает максимальный ({max_score})"
                        })
                        continue  # пропускаем обновление этой записи

                # Если балл > 0, а статус "Не явка" → делаем "Участник"
                if int(score) > 0 and status == "Не явка":
                    status = "Участник"

            # Проверяем, есть ли запись в результатах
            cur.execute(
                """
                SELECT id
                FROM practical.olympics_students_result
                WHERE id_olympic = %s AND id_student = %s
                """,
                (id_olympic, id_student),
            )
            existing = cur.fetchone()

            if existing:
                # ✅ Выбираем нужный SQL в зависимости от наличия score
                if score is not None:
                    cur.execute(
                        """
                        UPDATE practical.olympics_students_result
                        SET score = %s,
                            status = %s,
                            flag = TRUE
                        WHERE id_olympic = %s AND id_student = %s
                        """,
                        (score, status, id_olympic, id_student),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE practical.olympics_students_result
                        SET status = %s,
                            flag = TRUE
                        WHERE id_olympic = %s AND id_student = %s
                        """,
                        (status, id_olympic, id_student),
                    )

                if cur.rowcount > 0:
                    updated.append({
                        "id_student": id_student,
                        "status": status,
                        "score": score,
                    })
                else:
                    not_found.append(id_student)
            else:
                not_found.append(id_student)

        conn.commit()

        # Если есть ошибки превышения max_score — вернуть их
        if errors:
            return jsonify({
                "status": "error",
                "message": "Некоторые оценки не были обновлены из-за превышения максимума",
                "errors": errors,
                "updated": updated,
            }), 400

        if not updated:
            return jsonify({
                "status": "no_changes",
                "message": "Ни одна запись не была обновлена",
                "not_found": not_found,
            }), 200

        return jsonify({
            "status": "ok",
            "message": f"Обновлено {len(updated)} студентов",
            "updated": updated,
            "not_found": not_found,
        }), 200

    except Exception as e:
        conn.rollback()
        print("Ошибка при обновлении:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()


@olympiads_bp.route("/export/<int:olymp_id>", methods=["GET"])
def export_olympiad_results(olymp_id):
    conn = psycopg2.connect(CONNECT_DB)
    try:
        query = """
            SELECT 
                CONCAT(su.short_subject, '-', c.course, c.site, '-', st.id) AS shifr,
                s.fio,
                st.score,
                st.status
            FROM practical.olympics_students_result AS st
            LEFT JOIN practical.olympics_event AS e ON st.id_olympic = e.id
            LEFT JOIN practical.subject AS su ON su.id_subject = e.id_subject
            LEFT JOIN practical.students AS s ON s.id_student = st.id_student
            LEFT JOIN practical.students_classes AS stc ON stc.id_student = st.id_student
            LEFT JOIN practical.classes AS c ON c.id_class = stc.id_class
            WHERE stc.date_end IS NULL AND st.id_olympic = %s
        """
        df = pd.read_sql(query, conn, params=(olymp_id,))
        if df.empty:
            return jsonify({"error": "Нет данных для экспорта"}), 404

        # Сохраняем в Excel в память
        output = BytesIO()
        df.to_excel(output, index=False, sheet_name="Результаты")
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name=f"olympiad_{olymp_id}_results.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@olympiads_bp.route("/export/diplom/<int:olymp_id>", methods=["GET"])
def export_olympiad_results_from_diplom(olymp_id):
    conn = psycopg2.connect(CONNECT_DB)
    try:
        query = """
            SELECT fio, course, status, level
                FROM practical.olympics_students_result as st
                LEFT JOIN practical.olympics_event as e 
                ON st.id_olympic = e.id
                LEFT JOIN practical.subject as su
                ON su.id_subject = e.id_subject
                LEFT JOIN practical.students as s
                ON s.id_student = st.id_student
                LEFT JOIN practical.olympics_levels as l
                ON l.id = e.id_level
                LEFT JOIN practical.students_classes as stc
                ON stc.id_student = st.id_student
                LEFT JOIN practical.classes as c
                ON c.id_class = stc.id_class
                WHERE stc.date_end is null AND st.id_olympic = %s
        """
        df = pd.read_sql(query, conn, params=(olymp_id,))
        if df.empty:
            return jsonify({"error": "Нет данных для экспорта"}), 404

        # Сохраняем в Excel в память
        output = BytesIO()
        df.to_excel(output, index=False, sheet_name="Результаты")
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name=f"olympiad_{olymp_id}_results_dp.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@olympiads_bp.route("/export/protocol/<int:olymp_id>", methods=["GET"])
def export_olympiad_results_from_protocol(olymp_id):
    conn = psycopg2.connect(CONNECT_DB)
    try:
        query = """
            SELECT
  ROW_NUMBER() OVER (ORDER BY score DESC) as "№ п/п",
  CONCAT(su.short_subject, '-', c.course, c.site, '-', st.id) AS "Шифр участника",
  s.fio as "ФИО учащегося",
  c.course as "класс обучается",
  e.class as "класс выступает",
  'АНОО "Школа 800"' as "ОО, в которой обучается",
  st.score as "Количество набранных баллов",
  e.max_score as "Максимальный балл"
FROM practical.olympics_students_result AS st
LEFT JOIN practical.olympics_event AS e ON st.id_olympic = e.id
LEFT JOIN practical.subject AS su ON su.id_subject = e.id_subject
LEFT JOIN practical.students AS s ON s.id_student = st.id_student
LEFT JOIN practical.students_classes AS stc ON stc.id_student = st.id_student
LEFT JOIN practical.classes AS c ON c.id_class = stc.id_class
WHERE stc.date_end IS NULL AND st.id_olympic = %s

        """
        df = pd.read_sql(query, conn, params=(olymp_id,))
        if df.empty:
            return jsonify({"error": "Нет данных для экспорта"}), 404

        # Сохраняем в Excel в память
        output = BytesIO()
        df.to_excel(output, index=False, sheet_name="Результаты")
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name=f"olympiad_{olymp_id}_results_prot.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@olympiads_bp.route("/check-flags/<int:olymp_id>", methods=["GET"])
def check_flags(olymp_id):
    conn = psycopg2.connect(CONNECT_DB)
    cur = conn.cursor()
    try:
        # Считаем количество студентов с флагом = false
        cur.execute("""
            SELECT COUNT(*) 
            FROM practical.olympics_students_result
            WHERE id_olympic = %s AND (flag IS NULL OR flag = false)
        """, (olymp_id,))
        count_not_ready = cur.fetchone()[0]

        # Если студентов нет вообще, тоже считаем что нельзя экспортировать
        cur.execute("""
            SELECT COUNT(*) 
            FROM practical.olympics_students_result
            WHERE id_olympic = %s
        """, (olymp_id,))
        total_students = cur.fetchone()[0]

        cur.close()
        conn.close()

        if total_students == 0 or count_not_ready > 0:
            return jsonify({"can_export": False, "message": "Нет готовых студентов для экспорта"})
        else:
            return jsonify({"can_export": True})

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500