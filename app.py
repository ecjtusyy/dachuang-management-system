from flask import Flask, render_template, request, redirect, session
import pymysql
from config import DB_CONFIG

# 创建 Flask 应用
app = Flask(__name__)

# session 加密密钥
app.secret_key = "dachuang-secret-key"


def get_conn():
    # 获取数据库连接；DictCursor 让结果可以用 row["字段名"] 读取
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)


def login_required():
    # 判断当前用户是否已登录
    return "user_id" in session


def current_role():
    # 获取当前用户角色
    return session.get("role")


def write_log(action):
    # 未登录时不写日志
    if "user_id" not in session:
        return

    conn = get_conn()
    with conn.cursor() as cursor:
        # 记录当前用户的操作
        cursor.execute(
            "INSERT INTO operation_log(user_id, action) VALUES (%s, %s)",
            (session["user_id"], action)
        )
    conn.commit()
    conn.close()


def get_current_student_id():
    # 根据当前登录账号找到对应学生编号
    conn = get_conn()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT student_id FROM student WHERE user_id=%s",
            (session["user_id"],)
        )
        row = cursor.fetchone()
    conn.close()

    # 找到就返回 student_id，否则返回 None
    return row["student_id"] if row else None


def get_current_teacher_id():
    # 根据当前登录账号找到对应教师/专家编号
    conn = get_conn()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT teacher_id FROM teacher WHERE user_id=%s",
            (session["user_id"],)
        )
        row = cursor.fetchone()
    conn.close()

    # 找到就返回 teacher_id，否则返回 None
    return row["teacher_id"] if row else None


@app.route("/")
def index():
    # 未登录先去登录页
    if not login_required():
        return redirect("/login")

    # 已登录直接进入首页
    return redirect("/dashboard")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    # POST 表示用户提交了登录表单
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_conn()
        with conn.cursor() as cursor:
            # 查询账号密码是否匹配
            cursor.execute(
                "SELECT * FROM user WHERE username=%s AND password=%s",
                (username, password)
            )
            user = cursor.fetchone()
        conn.close()

        if user:
            # 登录成功，把用户信息存进 session
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            write_log("用户登录系统")
            return redirect("/dashboard")
        else:
            # 登录失败，给页面传错误信息
            error = "账号或密码错误"

    # GET 请求显示登录页
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    # 清空登录状态
    session.clear()
    return redirect("/login")


@app.route("/dashboard")
def dashboard():
    # 首页也需要登录
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    with conn.cursor() as cursor:
        # 统计项目数量
        cursor.execute("SELECT COUNT(*) AS c FROM project")
        project_count = cursor.fetchone()["c"]

        # 统计进度报告数量
        cursor.execute("SELECT COUNT(*) AS c FROM progress_report")
        progress_count = cursor.fetchone()["c"]

        # 统计经费申请数量
        cursor.execute("SELECT COUNT(*) AS c FROM expense")
        expense_count = cursor.fetchone()["c"]

        # 统计成果数量
        cursor.execute("SELECT COUNT(*) AS c FROM achievement")
        achievement_count = cursor.fetchone()["c"]

    conn.close()

    # 把统计结果传给首页模板
    return render_template(
        "dashboard.html",
        username=session["username"],
        role=session["role"],
        project_count=project_count,
        progress_count=progress_count,
        expense_count=expense_count,
        achievement_count=achievement_count
    )


@app.route("/projects")
def project_list():
    # 查看项目列表前先判断登录
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    with conn.cursor() as cursor:
        # 查询项目，并关联负责人和指导教师
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
    # 项目申报需要登录
    if not login_required():
        return redirect("/login")

    # 只有学生可以申报项目
    if current_role() != "student":
        return "只有学生可以申报项目"

    # 获取当前学生编号
    student_id = get_current_student_id()
    conn = get_conn()

    with conn.cursor() as cursor:
        # 查询教师列表，供申报时选择
        cursor.execute("SELECT teacher_id, name FROM teacher")
        teachers = cursor.fetchall()

    # POST 表示提交项目申报表
    if request.method == "POST":
        project_name = request.form.get("project_name")
        teacher_id = request.form.get("teacher_id")
        project_type = request.form.get("project_type")
        budget = request.form.get("budget")
        description = request.form.get("description")

        with conn.cursor() as cursor:
            # 插入新项目
            cursor.execute("""
                INSERT INTO project
                (project_name, leader_id, teacher_id, project_type, budget, description)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                project_name,
                student_id,
                teacher_id,
                project_type,
                budget,
                description
            ))

        conn.commit()
        conn.close()

        write_log("提交大创项目申报")
        return redirect("/projects")

    conn.close()

    # GET 显示申报页面
    return render_template("project_apply.html", teachers=teachers)


@app.route("/reviews")
def review_list():
    # 评审模块需要登录
    if not login_required():
        return redirect("/login")

    # 学生不能进入评审模块
    if current_role() not in ["teacher", "expert", "admin"]:
        return "只有教师、专家或管理员可以查看评审模块"

    conn = get_conn()
    with conn.cursor() as cursor:
        # 查询所有项目，供评审人员查看
        cursor.execute("""
            SELECT 
                p.project_id,
                p.project_name,
                p.project_type,
                p.project_level,
                p.status,
                s.name AS leader_name,
                t.name AS teacher_name
            FROM project p
            JOIN student s ON p.leader_id = s.student_id
            LEFT JOIN teacher t ON p.teacher_id = t.teacher_id
            ORDER BY p.project_id DESC
        """)
        projects = cursor.fetchall()
    conn.close()

    return render_template("review_list.html", projects=projects)


@app.route("/reviews/<int:project_id>", methods=["GET", "POST"])
def review_form(project_id):
    # 评审项目需要登录
    if not login_required():
        return redirect("/login")

    # 只有教师、专家、管理员可以评审
    if current_role() not in ["teacher", "expert", "admin"]:
        return "只有教师、专家或管理员可以评审项目"

    # 获取当前评审人的 teacher_id
    teacher_id = get_current_teacher_id()
    if teacher_id is None:
        return "当前账号没有关联教师/专家信息"

    conn = get_conn()

    with conn.cursor() as cursor:
        # 查询当前要评审的项目详情
        cursor.execute("""
            SELECT 
                p.*,
                s.name AS leader_name,
                t.name AS teacher_name
            FROM project p
            JOIN student s ON p.leader_id = s.student_id
            LEFT JOIN teacher t ON p.teacher_id = t.teacher_id
            WHERE p.project_id=%s
        """, (project_id,))
        project = cursor.fetchone()

    # POST 表示提交评审结果
    if request.method == "POST":
        score = request.form.get("score")
        opinion = request.form.get("opinion")
        review_result = request.form.get("review_result")

        # 根据评审结果更新项目状态
        if review_result == "通过":
            new_status = "已立项"
            new_level = request.form.get("project_level")
        elif review_result == "修改后通过":
            new_status = "已立项"
            new_level = request.form.get("project_level")
        else:
            new_status = "已驳回"
            new_level = "未定级"

        with conn.cursor() as cursor:
            # 保存评审记录
            cursor.execute("""
                INSERT INTO review(project_id, teacher_id, score, opinion, review_result)
                VALUES (%s, %s, %s, %s, %s)
            """, (project_id, teacher_id, score, opinion, review_result))

            # 同步更新项目状态和等级
            cursor.execute("""
                UPDATE project
                SET status=%s, project_level=%s
                WHERE project_id=%s
            """, (new_status, new_level, project_id))

        conn.commit()
        conn.close()

        write_log("完成项目评审")
        return redirect("/reviews")

    conn.close()

    # GET 显示评审页面
    return render_template("review_form.html", project=project)


@app.route("/progress")
def progress_list():
    # 查看进度报告需要登录
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    with conn.cursor() as cursor:
        # 查询进度报告，并关联项目和负责人
        cursor.execute("""
            SELECT 
                pr.report_id,
                pr.report_title,
                pr.report_type,
                pr.status,
                pr.submit_time,
                p.project_name,
                s.name AS leader_name
            FROM progress_report pr
            JOIN project p ON pr.project_id = p.project_id
            JOIN student s ON p.leader_id = s.student_id
            ORDER BY pr.report_id DESC
        """)
        reports = cursor.fetchall()
    conn.close()

    return render_template("progress_list.html", reports=reports)


@app.route("/progress/add", methods=["GET", "POST"])
def progress_add():
    # 提交进度需要登录
    if not login_required():
        return redirect("/login")

    # 只有学生可以提交进度报告
    if current_role() != "student":
        return "只有学生可以提交进度报告"

    # 获取当前学生编号
    student_id = get_current_student_id()
    conn = get_conn()

    with conn.cursor() as cursor:
        # 只查询当前学生负责的项目
        cursor.execute("""
            SELECT project_id, project_name
            FROM project
            WHERE leader_id=%s
            ORDER BY project_id DESC
        """, (student_id,))
        projects = cursor.fetchall()

    # POST 表示提交进度报告
    if request.method == "POST":
        project_id = request.form.get("project_id")
        report_title = request.form.get("report_title")
        report_type = request.form.get("report_type")
        content = request.form.get("content")

        with conn.cursor() as cursor:
            # 插入进度报告
            cursor.execute("""
                INSERT INTO progress_report(project_id, report_title, report_type, content)
                VALUES (%s, %s, %s, %s)
            """, (project_id, report_title, report_type, content))

        conn.commit()
        conn.close()

        write_log("提交项目进度报告")
        return redirect("/progress")

    conn.close()

    # GET 显示进度提交页面
    return render_template("progress_add.html", projects=projects)


@app.route("/progress/<int:report_id>/audit/<status>")
def progress_audit(report_id, status):
    # 审核进度需要登录
    if not login_required():
        return redirect("/login")

    # 只有教师、专家、管理员可以审核
    if current_role() not in ["teacher", "expert", "admin"]:
        return "只有教师、专家或管理员可以审核进度报告"

    # 限制状态，防止乱传参数
    if status not in ["已通过", "已驳回"]:
        return "非法状态"

    conn = get_conn()
    with conn.cursor() as cursor:
        # 更新进度报告状态
        cursor.execute(
            "UPDATE progress_report SET status=%s WHERE report_id=%s",
            (status, report_id)
        )
    conn.commit()
    conn.close()

    write_log("审核项目进度报告")
    return redirect("/progress")


@app.route("/expenses")
def expense_list():
    # 查看经费列表需要登录
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    with conn.cursor() as cursor:
        # 查询经费申请，并关联项目和负责人
        cursor.execute("""
            SELECT 
                e.expense_id,
                e.expense_type,
                e.amount,
                e.status,
                e.apply_time,
                e.approve_time,
                e.description,
                p.project_name,
                s.name AS leader_name
            FROM expense e
            JOIN project p ON e.project_id = p.project_id
            JOIN student s ON p.leader_id = s.student_id
            ORDER BY e.expense_id DESC
        """)
        expenses = cursor.fetchall()
    conn.close()

    return render_template("expense_list.html", expenses=expenses)


@app.route("/expenses/add", methods=["GET", "POST"])
def expense_add():
    # 提交经费申请需要登录
    if not login_required():
        return redirect("/login")

    # 只有学生可以提交经费报销
    if current_role() != "student":
        return "只有学生可以提交经费报销"

    # 获取当前学生编号
    student_id = get_current_student_id()
    conn = get_conn()

    with conn.cursor() as cursor:
        # 只查询当前学生负责的项目
        cursor.execute("""
            SELECT project_id, project_name
            FROM project
            WHERE leader_id=%s
            ORDER BY project_id DESC
        """, (student_id,))
        projects = cursor.fetchall()

    # POST 表示提交报销申请
    if request.method == "POST":
        project_id = request.form.get("project_id")
        expense_type = request.form.get("expense_type")
        amount = request.form.get("amount")
        description = request.form.get("description")

        with conn.cursor() as cursor:
            # 插入经费报销记录
            cursor.execute("""
                INSERT INTO expense(project_id, expense_type, amount, description)
                VALUES (%s, %s, %s, %s)
            """, (project_id, expense_type, amount, description))

        conn.commit()
        conn.close()

        write_log("提交经费报销申请")
        return redirect("/expenses")

    conn.close()

    # GET 显示经费申请页面
    return render_template("expense_add.html", projects=projects)


@app.route("/expenses/<int:expense_id>/approve")
def expense_approve(expense_id):
    # 审批经费需要登录
    if not login_required():
        return redirect("/login")

    # 只有管理员可以审批经费
    if current_role() != "admin":
        return "只有管理员可以审批经费"

    conn = get_conn()
    with conn.cursor() as cursor:
        # 审批通过；项目已用经费由数据库触发器自动更新
        cursor.execute("""
            UPDATE expense
            SET status='已通过', approve_time=NOW()
            WHERE expense_id=%s
        """, (expense_id,))
    conn.commit()
    conn.close()

    write_log("审批通过经费报销")
    return redirect("/expenses")


@app.route("/expenses/<int:expense_id>/reject")
def expense_reject(expense_id):
    # 驳回经费需要登录
    if not login_required():
        return redirect("/login")

    # 只有管理员可以审批经费
    if current_role() != "admin":
        return "只有管理员可以审批经费"

    conn = get_conn()
    with conn.cursor() as cursor:
        # 驳回申请，不增加项目已用经费
        cursor.execute("""
            UPDATE expense
            SET status='已驳回', approve_time=NOW()
            WHERE expense_id=%s
        """, (expense_id,))
    conn.commit()
    conn.close()

    write_log("驳回经费报销")
    return redirect("/expenses")


@app.route("/achievements")
def achievement_list():
    # 查看成果列表需要登录
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    with conn.cursor() as cursor:
        # 查询项目成果，并关联项目和负责人
        cursor.execute("""
            SELECT 
                a.achievement_id,
                a.achievement_type,
                a.achievement_name,
                a.achievement_date,
                a.description,
                p.project_id,
                p.project_name,
                p.status,
                s.name AS leader_name
            FROM achievement a
            JOIN project p ON a.project_id = p.project_id
            JOIN student s ON p.leader_id = s.student_id
            ORDER BY a.achievement_id DESC
        """)
        achievements = cursor.fetchall()
    conn.close()

    return render_template("achievement_list.html", achievements=achievements)


@app.route("/achievements/add", methods=["GET", "POST"])
def achievement_add():
    # 提交成果需要登录
    if not login_required():
        return redirect("/login")

    # 只有学生可以提交项目成果
    if current_role() != "student":
        return "只有学生可以提交项目成果"

    # 获取当前学生编号
    student_id = get_current_student_id()
    conn = get_conn()

    with conn.cursor() as cursor:
        # 只查询当前学生负责的项目
        cursor.execute("""
            SELECT project_id, project_name
            FROM project
            WHERE leader_id=%s
            ORDER BY project_id DESC
        """, (student_id,))
        projects = cursor.fetchall()

    # POST 表示提交成果
    if request.method == "POST":
        project_id = request.form.get("project_id")
        achievement_type = request.form.get("achievement_type")
        achievement_name = request.form.get("achievement_name")
        achievement_date = request.form.get("achievement_date")
        description = request.form.get("description")

        with conn.cursor() as cursor:
            # 插入成果记录
            cursor.execute("""
                INSERT INTO achievement
                (project_id, achievement_type, achievement_name, achievement_date, description)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                project_id,
                achievement_type,
                achievement_name,
                achievement_date,
                description
            ))

            # 提交成果后，项目进入待结题；已结题项目不再改状态
            cursor.execute("""
                UPDATE project
                SET status='待结题'
                WHERE project_id=%s AND status <> '已结题'
            """, (project_id,))

        conn.commit()
        conn.close()

        write_log("提交项目成果")
        return redirect("/achievements")

    conn.close()

    # GET 显示成果提交页面
    return render_template("achievement_add.html", projects=projects)


@app.route("/projects/<int:project_id>/finish")
def project_finish(project_id):
    # 办理结题需要登录
    if not login_required():
        return redirect("/login")

    # 只有管理员可以办理结题
    if current_role() != "admin":
        return "只有管理员可以办理结题"

    conn = get_conn()
    with conn.cursor() as cursor:
        # 更新项目状态为已结题
        cursor.execute("""
            UPDATE project
            SET status='已结题'
            WHERE project_id=%s
        """, (project_id,))
    conn.commit()
    conn.close()

    write_log("管理员办理项目结题")
    return redirect("/projects")


@app.route("/logs")
def logs():
    # 查看日志需要登录
    if not login_required():
        return redirect("/login")

    # 只有管理员可以查看操作日志
    if current_role() != "admin":
        return "只有管理员可以查看操作日志"

    conn = get_conn()
    with conn.cursor() as cursor:
        # 查询最近 100 条操作日志
        cursor.execute("""
            SELECT 
                l.log_id,
                u.username,
                u.role,
                l.action,
                l.operation_time
            FROM operation_log l
            LEFT JOIN user u ON l.user_id = u.user_id
            ORDER BY l.log_id DESC
            LIMIT 100
        """)
        logs_data = cursor.fetchall()
    conn.close()

    return render_template("logs.html", logs=logs_data)


if __name__ == "__main__":
    # Codespace 里需要用 0.0.0.0 才能外部访问
    app.run(host="0.0.0.0", port=5000, debug=True)