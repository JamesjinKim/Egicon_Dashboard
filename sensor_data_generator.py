import sqlite3
import random
import time
import json
from datetime import datetime, timedelta

# 데이터베이스 연결
def create_database():
    conn = sqlite3.connect('sensor_data.db')
    cursor = conn.cursor()
    
    # 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sensor_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        temperature REAL,
        humidity REAL,
        light INTEGER,
        pressure REAL,
        vibration REAL
    )
    ''')
    
    # 현재 측정값을 저장하는 테이블
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS current_readings (
        id INTEGER PRIMARY KEY,
        temperature REAL,
        humidity REAL,
        light INTEGER,
        pressure REAL,
        vibration REAL,
        updated_at TEXT
    )
    ''')
    
    conn.commit()
    return conn, cursor

# 센서 데이터 범위 설정
sensor_ranges = {
    'temperature': {'min': 20, 'max': 28},
    'humidity': {'min': 40, 'max': 75},
    'light': {'min': 500, 'max': 1500},
    'pressure': {'min': 5, 'max': 20},
    'vibration': {'min': 0.01, 'max': 0.5}
}

# 랜덤 데이터 생성 함수
def generate_sensor_data():
    data = {}
    for sensor, range_values in sensor_ranges.items():
        value = random.uniform(range_values['min'], range_values['max'])
        
        # 소수점 자릿수 조정
        if sensor in ['temperature', 'pressure']:
            data[sensor] = round(value, 1)
        elif sensor == 'vibration':
            data[sensor] = round(value, 2)
        else:
            data[sensor] = int(value)
    
    return data

# 히스토리 데이터 생성 및 저장
def generate_history_data(conn, cursor, hours=24):
    now = datetime.now()
    
    # 기존 데이터 삭제
    cursor.execute("DELETE FROM sensor_readings")
    
    # 지정된 시간 동안의 데이터 생성
    for hour in range(hours, 0, -1):
        # 각 시간에 1개의 데이터 포인트 생성
        timestamp = (now - timedelta(hours=hour)).strftime('%Y-%m-%d %H:00:00')
        data = generate_sensor_data()
        
        cursor.execute('''
        INSERT INTO sensor_readings 
        (timestamp, temperature, humidity, light, pressure, vibration)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            data['temperature'],
            data['humidity'],
            data['light'],
            data['pressure'],
            data['vibration']
        ))
    
    # 현재 데이터 저장/업데이트
    current_data = generate_sensor_data()
    current_timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute("DELETE FROM current_readings")
    cursor.execute('''
    INSERT INTO current_readings 
    (id, temperature, humidity, light, pressure, vibration, updated_at)
    VALUES (1, ?, ?, ?, ?, ?, ?)
    ''', (
        current_data['temperature'],
        current_data['humidity'],
        current_data['light'],
        current_data['pressure'],
        current_data['vibration'],
        current_timestamp
    ))
    
    conn.commit()

# 웹 서버를 위한 데이터 API 생성
def get_sensor_data_api(cursor):
    # 히스토리 데이터 가져오기
    cursor.execute("SELECT timestamp, temperature, humidity, light, pressure, vibration FROM sensor_readings ORDER BY timestamp")
    history_data = cursor.fetchall()
    
    # 현재 데이터 가져오기
    cursor.execute("SELECT temperature, humidity, light, pressure, vibration, updated_at FROM current_readings WHERE id = 1")
    current = cursor.fetchone()
    
    if not current:
        return {"error": "No current data available"}
    
    # JSON 형식으로 변환
    history = {
        "timestamps": [],
        "temperature": [],
        "humidity": [],
        "light": [],
        "pressure": [],
        "vibration": []
    }
    
    for row in history_data:
        timestamp, temp, humid, light, press, vib = row
        history["timestamps"].append(timestamp)
        history["temperature"].append(temp)
        history["humidity"].append(humid)
        history["light"].append(light)
        history["pressure"].append(press)
        history["vibration"].append(vib)
    
    result = {
        "current": {
            "temperature": current[0],
            "humidity": current[1],
            "light": current[2],
            "pressure": current[3],
            "vibration": current[4],
            "updated_at": current[5]
        },
        "history": history
    }
    
    return result

# 데이터 업데이트 함수 (실제 사용 시에는 이 함수를 주기적으로 실행)
def update_current_data(conn, cursor):
    current_data = generate_sensor_data()
    current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
    UPDATE current_readings 
    SET temperature = ?, humidity = ?, light = ?, pressure = ?, vibration = ?, updated_at = ?
    WHERE id = 1
    ''', (
        current_data['temperature'],
        current_data['humidity'],
        current_data['light'],
        current_data['pressure'],
        current_data['vibration'],
        current_timestamp
    ))
    
    # 새 데이터를 기록 테이블에도 저장
    # 실제 사용 시에는 매 시간마다만 저장하는 등의 로직 추가 가능
    cursor.execute('''
    INSERT INTO sensor_readings 
    (timestamp, temperature, humidity, light, pressure, vibration)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        current_timestamp,
        current_data['temperature'],
        current_data['humidity'],
        current_data['light'],
        current_data['pressure'],
        current_data['vibration']
    ))
    
    conn.commit()

# 데이터 출력 함수 (웹서버를 위한 JSON 파일 생성)
def export_to_json():
    conn, cursor = create_database()
    data = get_sensor_data_api(cursor)
    
    with open('sensor_data.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    conn.close()
    return data

# 메인 함수
def main():
    conn, cursor = create_database()
    
    # 초기 히스토리 데이터 생성
    generate_history_data(conn, cursor)
    
    # 현재 데이터 출력
    data = get_sensor_data_api(cursor)
    print("Current sensor data:")
    print(f"Temperature: {data['current']['temperature']}°C")
    print(f"Humidity: {data['current']['humidity']}%")
    print(f"Light: {data['current']['light']} ADC")
    print(f"Pressure: {data['current']['pressure']} Pa")
    print(f"Vibration: {data['current']['vibration']} g")
    
    # JSON 파일로 내보내기
    export_to_json()
    
    print("\nData exported to sensor_data.json")
    
    # 연결 종료
    conn.close()

# 실시간 업데이트 시뮬레이션 (예: 3초마다 새 데이터 생성)
def simulate_realtime_updates(duration_seconds=60, interval_seconds=3):
    conn, cursor = create_database()
    
    # 초기 히스토리 데이터 생성
    generate_history_data(conn, cursor)
    
    end_time = time.time() + duration_seconds
    
    print(f"Simulating real-time updates for {duration_seconds} seconds...")
    
    while time.time() < end_time:
        # 데이터 업데이트
        update_current_data(conn, cursor)
        
        # JSON 파일로 내보내기
        export_to_json()
        
        print(f"Data updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 대기
        time.sleep(interval_seconds)
    
    # 연결 종료
    conn.close()
    print("Simulation complete.")

if __name__ == "__main__":
    # 일반 실행
    main()
    
    # 실시간 업데이트 시뮬레이션 (옵션)
    # simulate_realtime_updates()