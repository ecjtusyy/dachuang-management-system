DROP DATABASE IF EXISTS dachuang_db;
CREATE DATABASE dachuang_db DEFAULT CHARACTER SET utf8mb4;
USE dachuang_db;

CREATE TABLE user (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    role ENUM('student', 'teacher', 'expert', 'admin') NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE student (
    student_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    student_no VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL,
    college VARCHAR(100),
    major VARCHAR(100),
    grade VARCHAR(20),
    phone VARCHAR(30),
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);

CREATE TABLE teacher (
    teacher_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    name VARCHAR(50) NOT NULL,
    title VARCHAR(50),
    college VARCHAR(100),
    phone VARCHAR(30),
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);

CREATE TABLE project (
    project_id INT PRIMARY KEY AUTO_INCREMENT,
    project_name VARCHAR(200) NOT NULL,
    leader_id INT NOT NULL,
    teacher_id INT,
    project_type ENUM('创新训练', '创业训练', '创业实践') NOT NULL,
    project_level ENUM('未定级', '校级', '省级', '国家级') DEFAULT '未定级',
    status ENUM('待评审', '已立项', '进行中', '待结题', '已结题', '已驳回') DEFAULT '待评审',
    budget DECIMAL(10,2) DEFAULT 0 CHECK (budget >= 0),
    used_budget DECIMAL(10,2) DEFAULT 0 CHECK (used_budget >= 0),
    apply_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    FOREIGN KEY (leader_id) REFERENCES student(student_id),
    FOREIGN KEY (teacher_id) REFERENCES teacher(teacher_id)
);

CREATE TABLE team_member (
    member_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    student_id INT NOT NULL,
    duty VARCHAR(100),
    join_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES project(project_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id)
);

CREATE TABLE review (
    review_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    teacher_id INT NOT NULL,
    score INT NOT NULL CHECK (score BETWEEN 0 AND 100),
    opinion TEXT,
    review_result ENUM('通过', '驳回', '修改后通过') NOT NULL,
    review_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES project(project_id),
    FOREIGN KEY (teacher_id) REFERENCES teacher(teacher_id)
);

CREATE TABLE progress_report (
    report_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    report_title VARCHAR(200) NOT NULL,
    report_type ENUM('月度报告', '季度报告', '中期报告') NOT NULL,
    content TEXT NOT NULL,
    submit_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('待审核', '已通过', '已驳回') DEFAULT '待审核',
    FOREIGN KEY (project_id) REFERENCES project(project_id)
);

CREATE TABLE expense (
    expense_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    expense_type VARCHAR(100) NOT NULL,
    amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    description TEXT,
    status ENUM('待审批', '已通过', '已驳回') DEFAULT '待审批',
    apply_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    approve_time DATETIME,
    FOREIGN KEY (project_id) REFERENCES project(project_id)
);

CREATE TABLE achievement (
    achievement_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    achievement_type ENUM('论文', '专利', '软件著作权', '竞赛获奖', '其他') NOT NULL,
    achievement_name VARCHAR(200) NOT NULL,
    achievement_date DATE,
    description TEXT,
    FOREIGN KEY (project_id) REFERENCES project(project_id)
);

CREATE TABLE operation_log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    action VARCHAR(200) NOT NULL,
    operation_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);