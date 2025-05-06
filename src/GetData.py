import mysql.connector
import psutil
import time
import re
import subprocess
from datetime import datetime

# เชื่อมต่อกับฐานข้อมูล MySQL
def connect_to_mysql():
    return mysql.connector.connect(
        host="host_ipaddress",         # ปรับตามการตั้งค่า MySQL ของคุณ
        user="root",                 # ชื่อผู้ใช้
        password="password",  # รหัสผ่าน
        database="db_name"
    )

# ดึงข้อมูลจากคำสั่ง `top` ของ container
def get_top_data_from_container(container_name):
    try:
        command = f"docker exec {container_name} top -bn1 | grep 'Cpu(s)'"
        result = subprocess.check_output(command, shell=True).decode('utf-8')

        load_avg = psutil.getloadavg()[0]
        cpu_us = float(re.search(r'(\d+\.\d+) us', result).group(1))
        cpu_sy = float(re.search(r'(\d+\.\d+) sy', result).group(1))
        cpu_si = float(re.search(r'(\d+\.\d+) si', result).group(1))
        cpu_id = float(re.search(r'(\d+\.\d+) id', result).group(1))
        cpu_usage = 100 - cpu_id

        return load_avg, cpu_us, cpu_sy, cpu_si, cpu_usage
    except Exception as e:
        print(f"Error fetching top data from container {container_name}: {e}")
        return None, None, None, None, None

# ดึงจำนวนคำขอจาก access log ของ container
last_line_number = 0
log_cleared = False  # เพื่อให้เคลียร์แค่รอบแรกเท่านั้น

def get_request_count_from_container(container_name):
    global last_line_number, log_cleared
    log_file_path = "/var/log/nginx/access.log"
    request_count = 0

    try:
        # เคลียร์ log แค่รอบแรก
        if not log_cleared:
            subprocess.run(f"docker exec {container_name} sh -c 'echo \"\" > {log_file_path}'", shell=True)
            log_cleared = True
            print("[Log cleared]")

        # ดึง log ตั้งแต่บรรทัดล่าสุด + 1
        command = f"docker exec {container_name} tail -n +{last_line_number + 1} {log_file_path}"
        log_data = subprocess.check_output(command, shell=True).decode('utf-8')

        new_lines = log_data.strip().split('\n')
        request_count = len([line for line in new_lines if line.strip()])

        # เพิ่มเลขบรรทัดล่าสุด
        last_line_number += request_count

    except Exception as e:
        print(f"Error reading log file from container {container_name}: {e}")

    return request_count



# เก็บข้อมูลลง MySQL
def insert_data(load_avg, cpu_us, cpu_sy, cpu_si, cpu_usage, request_count, label):
    connection = None
    try:
        connection = connect_to_mysql()
        cursor = connection.cursor()
        query = """
            INSERT INTO exp1 (
                timestamp, load_average_1min, cpu_us, cpu_sy, cpu_si, cpu_usage, request_count, label
            ) VALUES (
                NOW(), %s, %s, %s, %s, %s, %s, %s
            )
        """
        values = (load_avg, cpu_us, cpu_sy, cpu_si, cpu_usage, request_count, label)
        cursor.execute(query, values)
        connection.commit()
        print("Data inserted successfully.")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# หลักการทำงานหลัก
def main():
    container_name = "mn.server1"

    while True:
        load_avg, cpu_us, cpu_sy, cpu_si, cpu_usage = get_top_data_from_container(container_name)
        request_count = get_request_count_from_container(container_name)
        label = "experiment333"  # ปรับตามต้องการ เช่น 'attack'

        insert_data(load_avg, cpu_us, cpu_sy, cpu_si, cpu_usage, request_count, label)

        time.sleep(5)

if __name__ == "__main__":
    main()

