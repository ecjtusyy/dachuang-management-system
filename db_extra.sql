-- 触发器：报销审批通过后，自动更新项目已用经费。
-- 存储过程：根据项目编号查询项目完整信息，统计各学院项目数量。

USE dachuang_db;

DROP TRIGGER IF EXISTS trg_expense_approved_update_budget;
DROP PROCEDURE IF EXISTS sp_project_detail;
DROP PROCEDURE IF EXISTS sp_college_project_count;

DELIMITER //

CREATE TRIGGER trg_expense_approved_update_budget
AFTER UPDATE ON expense
FOR EACH ROW
BEGIN
    IF OLD.status <> '已通过' AND NEW.status = '已通过' THEN
        UPDATE project
        SET used_budget = used_budget + NEW.amount
        WHERE project_id = NEW.project_id;
    END IF;
END//

CREATE PROCEDURE sp_project_detail(IN pid INT)
BEGIN
    SELECT 
        p.project_id,
        p.project_name,
        p.project_type,
        p.project_level,
        p.status,
        p.budget,
        p.used_budget,
        p.apply_time,
        p.description,
        s.name AS leader_name,
        s.college AS leader_college,
        s.major AS leader_major,
        t.name AS teacher_name,
        t.title AS teacher_title
    FROM project p
    JOIN student s ON p.leader_id = s.student_id
    LEFT JOIN teacher t ON p.teacher_id = t.teacher_id
    WHERE p.project_id = pid;

    SELECT 
        tm.member_id,
        s.name AS student_name,
        s.student_no,
        tm.duty
    FROM team_member tm
    JOIN student s ON tm.student_id = s.student_id
    WHERE tm.project_id = pid;

    SELECT 
        r.score,
        r.opinion,
        r.review_result,
        r.review_time,
        t.name AS reviewer_name
    FROM review r
    JOIN teacher t ON r.teacher_id = t.teacher_id
    WHERE r.project_id = pid;

    SELECT 
        report_title,
        report_type,
        status,
        submit_time
    FROM progress_report
    WHERE project_id = pid;

    SELECT 
        expense_type,
        amount,
        status,
        apply_time,
        approve_time
    FROM expense
    WHERE project_id = pid;

    SELECT 
        achievement_type,
        achievement_name,
        achievement_date
    FROM achievement
    WHERE project_id = pid;
END//

CREATE PROCEDURE sp_college_project_count()
BEGIN
    SELECT 
        s.college,
        COUNT(*) AS project_count,
        SUM(p.budget) AS total_budget,
        SUM(p.used_budget) AS total_used_budget
    FROM project p
    JOIN student s ON p.leader_id = s.student_id
    GROUP BY s.college
    ORDER BY project_count DESC;
END//

DELIMITER ;