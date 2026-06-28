USE dachuang_db;

INSERT INTO user(username, password, role) VALUES
('student01', '123456', 'student'),
('student02', '123456', 'student'),
('teacher01', '123456', 'teacher'),
('expert01', '123456', 'expert'),
('admin01', '123456', 'admin');

INSERT INTO student(user_id, student_no, name, college, major, grade, phone) VALUES
(1, '20240001', '张三', '信息与软件工程学院', '软件工程', '2024级', '13800000001'),
(2, '20240002', '李四', '信息与软件工程学院', '数据科学与大数据技术', '2024级', '13800000002');

INSERT INTO teacher(user_id, name, title, college, phone) VALUES
(3, '王老师', '副教授', '信息与软件工程学院', '13800000003'),
(4, '赵专家', '教授', '信息与软件工程学院', '13800000004');

INSERT INTO project(project_name, leader_id, teacher_id, project_type, project_level, status, budget, description) VALUES
('基于数据库的大创项目全过程管理系统', 1, 1, '创新训练', '校级', '进行中', 5000, '实现大创项目申报、评审、进度、经费和成果管理。');

INSERT INTO team_member(project_id, student_id, duty) VALUES
(1, 1, '项目负责人'),
(1, 2, '系统测试与文档整理');