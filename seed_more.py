import re
import pymysql
from config import DB_CONFIG

# =========================================================
# 批量测试数据生成脚本
# 作用：
# 1. 给各张表补充测试数据
# 2. 尽量保证每张核心表都有 30 条以上记录
# 3. 自动读取数据库 ENUM 字段，避免插入非法枚举值
# =========================================================

# 每张核心表至少生成到 30 条
MIN_COUNT = 30

# 连接数据库；DictCursor 方便使用 row["字段名"] 取值
conn = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

# 测试数据的固定选项
colleges = ["信息与软件工程学院", "理学院", "机电学院", "土木建筑学院", "经济管理学院"]
majors = ["软件工程", "数据科学", "数学与应用数学", "计算机科学", "人工智能"]
expense_types = ["材料费", "打印费", "实验耗材费", "竞赛报名费", "其他"]


def get_enum_values(cursor, table_name, column_name):
    """
    读取 MySQL 某个 ENUM 字段允许的所有取值。

    例如：
    project.project_type 的字段类型可能是：
    enum('创新训练','创业训练')

    这个函数会返回：
    ['创新训练', '创业训练']

    这样可以避免 Python 里写的值和数据库 ENUM 不一致。
    """
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (column_name,))
    row = cursor.fetchone()

    if not row:
        return []

    field_type = row["Type"]

    # 从 enum('A','B','C') 里面提取 A、B、C
    values = re.findall(r"'([^']*)'", field_type)
    return values


def choose(values, index):
    """
    从列表中循环取值。

    例如 values = ['校级', '省级', '国家级']
    index = 0 -> 校级
    index = 1 -> 省级
    index = 2 -> 国家级
    index = 3 -> 又回到校级
    """
    if not values:
        return None
    return values[index % len(values)]


def preferred_value(values, preferred_list):
    """
    优先选择指定的值。

    例如：
    values = ['待审批', '已通过', '已驳回']
    preferred_list = ['待审批']

    如果数据库允许 '待审批'，就返回 '待审批'。
    如果不允许，就返回 values 的第一个值。
    """
    for item in preferred_list:
        if item in values:
            return item

    if values:
        return values[0]

    return None


def table_count(cursor, table_name):
    """
    查询某张表当前有多少条记录。
    """
    cursor.execute(f"SELECT COUNT(*) AS c FROM `{table_name}`")
    return cursor.fetchone()["c"]


try:
    with conn.cursor() as cursor:
        # =====================================================
        # 0. 自动读取数据库 ENUM 字段允许值
        # =====================================================

        # 项目类型，例如：创新训练、创业训练、创业实践
        project_types = get_enum_values(cursor, "project", "project_type")

        # 项目等级，例如：未定级、校级、省级、国家级
        project_levels = get_enum_values(cursor, "project", "project_level")

        # 项目状态，例如：待评审、已立项、进行中、待结题、已结题、已驳回
        project_statuses = get_enum_values(cursor, "project", "status")

        # 评审结果，例如：通过、驳回、修改后通过
        review_results = get_enum_values(cursor, "review", "review_result")

        # 进度报告类型，例如：月度报告、季度报告、中期报告
        report_types = get_enum_values(cursor, "progress_report", "report_type")

        # 进度报告状态，例如：待审核、已通过、已驳回
        report_statuses = get_enum_values(cursor, "progress_report", "status")

        # 报销状态，例如：待审批、已通过、已驳回
        expense_statuses = get_enum_values(cursor, "expense", "status")

        # 成果类型，例如：论文、专利、软件著作权、竞赛获奖、其他
        achievement_types = get_enum_values(cursor, "achievement", "achievement_type")

        print("当前数据库允许的项目类型：", project_types)
        print("当前数据库允许的项目等级：", project_levels)
        print("当前数据库允许的项目状态：", project_statuses)

        # 如果数据库表设计有问题，这里直接提示
        if not project_types:
            raise Exception("project.project_type 没有读取到 ENUM 选项，请检查 schema.sql。")

        if not project_levels:
            raise Exception("project.project_level 没有读取到 ENUM 选项，请检查 schema.sql。")

        if not project_statuses:
            raise Exception("project.status 没有读取到 ENUM 选项，请检查 schema.sql。")

        # =====================================================
        # 1. 生成用户账号
        # =====================================================

        # 生成学生账号 student01 ~ student40
        # INSERT IGNORE 的意思是：如果账号已经存在，就跳过，不报错
        for i in range(1, 41):
            cursor.execute("""
                INSERT IGNORE INTO user(username, password, role)
                VALUES (%s, '123456', 'student')
            """, (f"student{i:02d}",))

        # 生成教师/专家账号 teacher01 ~ teacher40
        for i in range(1, 41):
            # 偶数是教师，奇数是专家
            role = "teacher" if i % 2 == 0 else "expert"

            cursor.execute("""
                INSERT IGNORE INTO user(username, password, role)
                VALUES (%s, '123456', %s)
            """, (f"teacher{i:02d}", role))

        # 保留管理员账号
        cursor.execute("""
            INSERT IGNORE INTO user(username, password, role)
            VALUES ('admin01', '123456', 'admin')
        """)

        # 先提交用户账号，后面才能查 user_id
        conn.commit()

        # =====================================================
        # 2. 生成学生信息
        # =====================================================

        # 查出所有学生账号
        cursor.execute("""
            SELECT user_id, username
            FROM user
            WHERE role='student'
            ORDER BY user_id
        """)
        student_users = cursor.fetchall()

        for idx, u in enumerate(student_users, start=1):
            # 判断这个 user_id 是否已经有学生信息
            cursor.execute("""
                SELECT student_id
                FROM student
                WHERE user_id=%s
                LIMIT 1
            """, (u["user_id"],))
            exist_student = cursor.fetchone()

            # 如果已经有 student 记录，就不重复插入
            if exist_student:
                continue

            cursor.execute("""
                INSERT INTO student(user_id, student_no, name, college, major, grade, phone)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                u["user_id"],
                f"2024{u['user_id']:04d}",
                f"学生{idx}",
                choose(colleges, idx),
                choose(majors, idx),
                "2024级",
                f"1380001{idx:04d}"
            ))

        # =====================================================
        # 3. 生成教师/专家信息
        # =====================================================

        # 查出所有教师和专家账号
        cursor.execute("""
            SELECT user_id, username, role
            FROM user
            WHERE role IN ('teacher', 'expert')
            ORDER BY user_id
        """)
        teacher_users = cursor.fetchall()

        for idx, u in enumerate(teacher_users, start=1):
            # 判断这个 user_id 是否已经有教师信息
            cursor.execute("""
                SELECT teacher_id
                FROM teacher
                WHERE user_id=%s
                LIMIT 1
            """, (u["user_id"],))
            exist_teacher = cursor.fetchone()

            # 如果已经有 teacher 记录，就不重复插入
            if exist_teacher:
                continue

            cursor.execute("""
                INSERT INTO teacher(user_id, name, title, college, phone)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                u["user_id"],
                f"教师{idx}",
                "教授" if idx % 2 == 0 else "副教授",
                choose(colleges, idx),
                f"1390001{idx:04d}"
            ))

        # 提交学生和教师信息
        conn.commit()

        # =====================================================
        # 4. 查询学生和教师编号
        # =====================================================

        cursor.execute("""
            SELECT student_id
            FROM student
            ORDER BY student_id
        """)
        students = cursor.fetchall()

        cursor.execute("""
            SELECT teacher_id
            FROM teacher
            ORDER BY teacher_id
        """)
        teachers = cursor.fetchall()

        if not students:
            raise Exception("student 表没有学生数据，无法生成项目。")

        if not teachers:
            raise Exception("teacher 表没有教师数据，无法生成项目。")

        # =====================================================
        # 5. 生成项目数据
        # =====================================================

        # 查看当前项目数量，只补不足的数量
        current_project_count = table_count(cursor, "project")
        need_project_count = max(0, MIN_COUNT - current_project_count)

        print(f"当前 project 表已有 {current_project_count} 条，需要补充 {need_project_count} 条。")

        for i in range(need_project_count):
            index = current_project_count + i + 1

            # 循环分配负责人
            leader_id = students[index % len(students)]["student_id"]

            # 循环分配指导教师
            teacher_id = teachers[index % len(teachers)]["teacher_id"]

            # 注意：
            # project_type、project_level、status 都从数据库 ENUM 里选
            # 不再手写死，所以不会出现 Data truncated
            project_type = choose(project_types, index)

            # 优先不要选择“未定级”，否则项目看起来不完整
            usable_levels = [x for x in project_levels if x != "未定级"]
            project_level = choose(usable_levels if usable_levels else project_levels, index)

            # 优先选择这些比较适合展示的状态
            usable_statuses = [
                x for x in project_statuses
                if x in ["已立项", "进行中", "待结题", "已结题", "待评审"]
            ]
            status = choose(usable_statuses if usable_statuses else project_statuses, index)

            cursor.execute("""
                INSERT INTO project(
                    project_name,
                    leader_id,
                    teacher_id,
                    project_type,
                    project_level,
                    status,
                    budget,
                    used_budget,
                    description
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s)
            """, (
                f"大学生创新创业项目{index}",
                leader_id,
                teacher_id,
                project_type,
                project_level,
                status,
                3000 + index * 100,
                f"这是第{index}个大创项目，主要用于测试系统全过程管理功能。"
            ))

        conn.commit()

        # 查询项目编号，后面生成团队、评审、进度、经费、成果都要用
        cursor.execute("""
            SELECT project_id, leader_id, teacher_id
            FROM project
            ORDER BY project_id
        """)
        projects = cursor.fetchall()

        if not projects:
            raise Exception("project 表没有项目数据，无法继续生成后续数据。")

        # =====================================================
        # 6. 生成团队成员
        # =====================================================

        current_count = table_count(cursor, "team_member")
        need_count = max(0, MIN_COUNT - current_count)

        print(f"当前 team_member 表已有 {current_count} 条，需要补充 {need_count} 条。")

        for i in range(need_count):
            index = current_count + i + 1

            p = projects[index % len(projects)]
            s = students[(index + 1) % len(students)]

            cursor.execute("""
                INSERT INTO team_member(project_id, student_id, duty)
                VALUES (%s, %s, %s)
            """, (
                p["project_id"],
                s["student_id"],
                "项目负责人" if index % 3 == 0 else "项目成员"
            ))

        # =====================================================
        # 7. 生成评审记录
        # =====================================================

        current_count = table_count(cursor, "review")
        need_count = max(0, MIN_COUNT - current_count)

        print(f"当前 review 表已有 {current_count} 条，需要补充 {need_count} 条。")

        # 评审结果优先用“通过”或“修改后通过”
        usable_review_results = [
            x for x in review_results
            if x in ["通过", "修改后通过", "驳回"]
        ]

        if not usable_review_results:
            usable_review_results = review_results

        for i in range(need_count):
            index = current_count + i + 1

            p = projects[index % len(projects)]
            t = teachers[index % len(teachers)]

            cursor.execute("""
                INSERT INTO review(project_id, teacher_id, score, opinion, review_result)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                p["project_id"],
                t["teacher_id"],
                70 + index % 25,
                f"项目方案较完整，具备一定创新性，建议继续完善实施计划。评审编号{index}",
                choose(usable_review_results, index)
            ))

        # =====================================================
        # 8. 生成进度报告
        # =====================================================

        current_count = table_count(cursor, "progress_report")
        need_count = max(0, MIN_COUNT - current_count)

        print(f"当前 progress_report 表已有 {current_count} 条，需要补充 {need_count} 条。")

        # 如果数据库没有读到报告类型，就给一个兜底值
        if not report_types:
            report_types = ["月度报告"]

        # 报告状态优先使用“待审核”或“已通过”
        usable_report_statuses = [
            x for x in report_statuses
            if x in ["待审核", "已通过", "已驳回"]
        ]

        if not usable_report_statuses:
            usable_report_statuses = report_statuses

        for i in range(need_count):
            index = current_count + i + 1

            p = projects[index % len(projects)]

            cursor.execute("""
                INSERT INTO progress_report(
                    project_id,
                    report_title,
                    report_type,
                    content,
                    status
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                p["project_id"],
                f"第{index}次项目进度报告",
                choose(report_types, index),
                f"本阶段完成了需求分析、数据库设计、系统编码和测试工作。报告编号{index}",
                choose(usable_report_statuses, index)
            ))

        # =====================================================
        # 9. 生成经费记录
        # =====================================================

        current_count = table_count(cursor, "expense")
        need_count = max(0, MIN_COUNT - current_count)

        print(f"当前 expense 表已有 {current_count} 条，需要补充 {need_count} 条。")

        # 报销状态优先用“待审批”
        expense_status = preferred_value(expense_statuses, ["待审批"])

        if not expense_status:
            raise Exception("expense.status 没有可用状态，请检查数据库字段。")

        for i in range(need_count):
            index = current_count + i + 1

            p = projects[index % len(projects)]

            cursor.execute("""
                INSERT INTO expense(
                    project_id,
                    expense_type,
                    amount,
                    description,
                    status
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                p["project_id"],
                choose(expense_types, index),
                80 + index * 10,
                f"项目材料或打印相关费用，记录编号{index}",
                expense_status
            ))

        # =====================================================
        # 10. 生成成果记录
        # =====================================================

        current_count = table_count(cursor, "achievement")
        need_count = max(0, MIN_COUNT - current_count)

        print(f"当前 achievement 表已有 {current_count} 条，需要补充 {need_count} 条。")

        if not achievement_types:
            achievement_types = ["其他"]

        for i in range(need_count):
            index = current_count + i + 1

            p = projects[index % len(projects)]

            cursor.execute("""
                INSERT INTO achievement(
                    project_id,
                    achievement_type,
                    achievement_name,
                    achievement_date,
                    description
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                p["project_id"],
                choose(achievement_types, index),
                f"项目阶段性成果{index}",
                "2026-06-01",
                f"这是第{index}条项目成果记录，用于系统测试和成果清单展示。"
            ))

        # =====================================================
        # 11. 生成操作日志
        # =====================================================

        current_count = table_count(cursor, "operation_log")
        need_count = max(0, MIN_COUNT - current_count)

        print(f"当前 operation_log 表已有 {current_count} 条，需要补充 {need_count} 条。")

        cursor.execute("""
            SELECT user_id
            FROM user
            ORDER BY user_id
        """)
        users = cursor.fetchall()

        if not users:
            raise Exception("user 表没有用户数据，无法生成日志。")

        for i in range(need_count):
            index = current_count + i + 1

            u = users[index % len(users)]

            cursor.execute("""
                INSERT INTO operation_log(user_id, action)
                VALUES (%s, %s)
            """, (
                u["user_id"],
                f"测试操作日志{index}"
            ))

    # 统一提交剩余测试数据
    conn.commit()

    print("批量测试数据生成完成。")
    print("现在可以运行 python app.py 打开系统测试。")

except Exception as e:
    # 如果中途出错，回滚本次未提交的数据
    conn.rollback()
    print("批量测试数据生成失败：")
    print(e)

finally:
    # 无论成功还是报错，最后都关闭数据库连接
    conn.close()