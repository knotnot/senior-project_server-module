import subprocess
import numpy as np
import onnxruntime as ort
import time
import re
import os

# ฟังก์ชันดึงข้อมูลจาก top
def get_top_data():
    top_output = subprocess.check_output(['top', '-bn1']).decode('utf-8')
    cpu_line = [line for line in top_output.split('\n') if 'Cpu(s):' in line]
    
    if cpu_line:
        line = cpu_line[0]
        
        # ดึงค่าต่าง ๆ ด้วย regex
        us_match = re.search(r'(\d+\.\d+)\s+us', line)
        sy_match = re.search(r'(\d+\.\d+)\s+sy', line)
        si_match = re.search(r'(\d+\.\d+)\s+si', line)
        id_match = re.search(r'(\d+\.\d+)\s+id', line)

        if us_match and sy_match and si_match and id_match:
            cpu_us = float(us_match.group(1))
            cpu_sy = float(sy_match.group(1))
            cpu_si = float(si_match.group(1))
            cpu_id = float(id_match.group(1))
            cpu_usage = 100.0 - cpu_id
        else:
            return None, None, None, None, None

        # ดึง load average
        uptime_output = subprocess.check_output(['uptime']).decode('utf-8')
        load_avg = float(re.findall(r'load average[s]?: ([\d\.]+)', uptime_output)[0])
        
        return load_avg, cpu_us, cpu_sy, cpu_si, cpu_usage
    else:
        return None, None, None, None, None

# ฟังก์ชันดึงข้อมูลจาก Nginx access log
def get_new_request_count(log_file_path='/var/log/nginx/access.log', state_file='log_offset.txt'):
    offset = 0
    # โหลดตำแหน่งที่อ่านไว้ล่าสุด
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            offset = int(f.read().strip() or 0)

    # เปิด access.log แล้ว seek ไปที่ตำแหน่ง offset
    with open(log_file_path, 'r') as log_file:
        log_file.seek(offset)
        new_lines = log_file.readlines()
        new_offset = log_file.tell()  # จำตำแหน่งไว้

    # บันทึกตำแหน่งไว้สำหรับรอบถัดไป
    with open(state_file, 'w') as f:
        f.write(str(new_offset))

    # กรองเฉพาะบรรทัดที่เป็น 200 OK
    request_count = sum(1 for line in new_lines if ' 200 ' in line)
    return request_count

# โหลดโมเดล ONNX
session = ort.InferenceSession('detect.onnx')

# ตรวจสอบชื่อ input ของโมเดล
input_name = session.get_inputs()[0].name

# เริ่มต้นลูป
while True:
    # ดึงข้อมูลจาก top
    load_avg, cpu_us, cpu_sy, cpu_si, cpu_usage = get_top_data()

    # ดึง request count จาก access log
    request_count = get_new_request_count('/var/log/nginx/access.log')

    # แสดงข้อมูลที่ดึงมา
    print(f"Load average: {load_avg}")
    print(f"CPU us: {cpu_us}, CPU sy: {cpu_sy}, CPU si: {cpu_si}, CPU usage: {cpu_usage}")
    print(f"Request count: {request_count}")

    # สร้างข้อมูล input ในรูปแบบ list หรือ array
    input_data = np.array([[load_avg, cpu_us, cpu_sy, cpu_si, cpu_usage, request_count]], dtype=np.float32)

    # ใช้โมเดลทำนาย
    prediction = session.run(None, {input_name: input_data})

    # แสดงผลการทำนาย
    score = prediction[0][0]
    print(f"Prediction: {score}")

    if score > 0.8:
        print("Server is under attack!")
    else:
        print("Normal")

    # หน่วงเวลา 5 วินาที
    time.sleep(5)

