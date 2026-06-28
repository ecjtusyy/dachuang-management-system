from flask import Flask, render_template, request, redirect, session
import pymysql
from config import DB_CONFIG

app = Flask(__name__)
app.secret_key = "dachuang-secret-key"


def get_conn():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)


def login_required():
    return "user_id" in session


@app.route("/")
def index():
    if not login_required():
        return redirect("/login")
    return redirect("/dashboard")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM user WHERE username=%s AND password=%s",
                (username, password)
            )
            user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect("/dashboard")
        else:
            error = "账号或密码错误"

    return render_template("login.html", error=error)


@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect("/login")

    return render_template(
        "dashboard.html",
        username=session["username"],
        role=session["role"]
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/projects")
def project_list():
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT 
                p.project_id,
                p.project_name,
                p.project_type,
                p.project_level,
                p.status,
                p.budget,
                p.used_budget,
                p.apply_time,
                s.name AS leader_name,
                t.name AS teacher_name
            FROM project p
            JOIN student s ON p.leader_id = s.student_id
            LEFT JOIN teacher t ON p.teacher_id = t.teacher_id
            ORDER BY p.project_id DESC
        """)
        projects = cursor.fetchall()
    conn.close()

    return render_template("project_list.html", projects=projects)


@app.route("/projects/apply", methods=["GET", "POST"])
def project_apply():
    if not login_required():
        return redirect("/login")

    if session.get("role") != "student":
        return "只有学生可以申报项目"

    conn = get_conn()

    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT student_id FROM student WHERE user_id=%s",
            (session["user_id"],)
        )
        student = cursor.fetchone()

        cursor.execute("SELECT teacher_id, name FROM teacher")
        teachers = cursor.fetchall()

    if request.method == "POST":
        project_name = request.form.get("project_name")
        teacher_id = request.form.get("teacher_id")
        project_type = request.form.get("project_type")
        budget = request.form.get("budget")
        description = request.form.get("description")

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO project
                (project_name, leader_id, teacher_id, project_type, budget, description)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                project_name,
                student["student_id"],
                teacher_id,
                project_type,
                budget,
                description
            ))

            cursor.execute("""
                INSERT INTO operation_log(user_id, action)
                VALUES (%s, %s)
            """, (
                session["user_id"],
                "提交大创项目申报"
            ))

        conn.commit()
        conn.close()
        return redirect("/projects")

    conn.close()
    return render_template("project_apply.html", teachers=teachers)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)