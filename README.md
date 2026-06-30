# dachuang-management-system

运行
docker start dachuang-mysql
python app.py

docker exec -i dachuang-mysql mysql --protocol=tcp -h127.0.0.1 --default-character-set=utf8mb4 -uroot -p123456 < schema.sql
这样导入数据库，防止出现中文乱码