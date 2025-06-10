from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
import random
from sensor_manager import SensorManager

app = Flask(__name__, static_folder='.')
CORS(app)  # 크로스 오리진 요청 허용

# 전역 센서 매니저 인스턴스
sensor_manager = None

# 더미 센서 데이터 범위 설정 (폴백용)
sensor_ranges = {
    'temperature': {'min': 20, 'max': 28},
    'humidity': {'min': 40, 'max': 75},
    'light': {'min': 500, 'max': 1500},
    'pressure': {'min': 5, 'max': 20},
    'vibration': {'min': 0.01, 'max': 0.5}
}

# 데이터베이스 연결 함수
def get_db_connection():
    conn = sqlite3.connect('sensor_data.db')
    conn.row_factory = sqlite3.Row
    return conn

# 실제 센서 데이터 읽기 함수
def generate_sensor_data():
    """실제 센서에서 데이터를 읽거나 폴백 더미 데이터 생성"""
    global sensor_manager
    
    if sensor_manager:
        try:
            # 실제 센서 데이터 읽기
            sensor_data = sensor_manager.read_all_sensors()
            print(f"DEBUG: 실제 센서 데이터 - 온도: {sensor_data['temperature']}, 조도: {sensor_data['light']}")
            return {
                'temperature': sensor_data['temperature'],
                'humidity': sensor_data['humidity'],
                'light': sensor_data['light'],
                'pressure': sensor_data['pressure'],  # 이미 차압으로 변환됨
                'vibration': sensor_data['vibration']
            }
        except Exception as e:
            print(f"WARNING: 센서 읽기 실패, 더미 데이터 사용: {e}")
    
    # 폴백: 더미 데이터 생성
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

# 현재 데이터 업데이트 함수
def update_current_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
    
    # 새 데이터 확인
    if cursor.rowcount == 0:
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
    conn.close()
    
    return current_data

# API 라우트: 센서 상태 정보
@app.route('/api/sensor-status', methods=['GET'])
def get_sensor_status():
    """센서 연결 상태 및 정보 반환"""
    global sensor_manager
    
    if sensor_manager:
        status = sensor_manager.get_sensor_status()
        return jsonify({
            'sensors': {
                'bme688': 'connected' if status['bme688_connected'] else 'disconnected',
                'bh1750': 'connected' if status['bh1750_connected'] else 'disconnected',
                'total_connected': status['sensor_count']
            },
            'mode': 'fallback' if status['fallback_mode'] else 'real',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        return jsonify({
            'sensors': {'bme688': 'disconnected', 'bh1750': 'disconnected', 'total_connected': 0},
            'mode': 'fallback',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

# API 라우트: 확장된 센서 데이터 (가스 센서 포함)
@app.route('/api/extended-data', methods=['GET'])
def get_extended_sensor_data():
    """가스 센서 및 공기질 데이터 포함한 확장 센서 데이터"""
    global sensor_manager
    
    if sensor_manager:
        try:
            sensor_data = sensor_manager.read_all_sensors()
            return jsonify({
                'gas_resistance': sensor_data['gas_resistance'],
                'air_quality': sensor_data['air_quality'],
                'absolute_pressure': sensor_data['absolute_pressure'],
                'timestamp': sensor_data['timestamp']
            })
        except Exception as e:
            return jsonify({'error': f'센서 읽기 실패: {e}'}), 500
    else:
        return jsonify({'error': '센서 매니저 초기화되지 않음'}), 500

# API 라우트: 모든 센서 데이터 가져오기
@app.route('/api/sensor-data', methods=['GET'])
def get_all_sensor_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 히스토리 데이터 가져오기
    cursor.execute("SELECT timestamp, temperature, humidity, light, pressure, vibration FROM sensor_readings ORDER BY timestamp")
    history_data = cursor.fetchall()
    
    # 현재 데이터 가져오기
    cursor.execute("SELECT temperature, humidity, light, pressure, vibration, updated_at FROM current_readings WHERE id = 1")
    current = cursor.fetchone()
    
    # 현재 데이터가 없으면 업데이트
    if not current:
        updated_data = update_current_data()
        current = {
            "temperature": updated_data['temperature'],
            "humidity": updated_data['humidity'],
            "light": updated_data['light'],
            "pressure": updated_data['pressure'],
            "vibration": updated_data['vibration'],
            "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        current = dict(current)
    
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
        row_dict = dict(row)
        history["timestamps"].append(row_dict["timestamp"])
        history["temperature"].append(row_dict["temperature"])
        history["humidity"].append(row_dict["humidity"])
        history["light"].append(row_dict["light"])
        history["pressure"].append(row_dict["pressure"])
        history["vibration"].append(row_dict["vibration"])
    
    result = {
        "current": current,
        "history": history
    }
    
    conn.close()
    return jsonify(result)

# API 라우트: 현재 센서 데이터만 가져오기
@app.route('/api/current-data', methods=['GET'])
def get_current_sensor_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 현재 데이터 가져오기
    cursor.execute("SELECT temperature, humidity, light, pressure, vibration, updated_at FROM current_readings WHERE id = 1")
    current = cursor.fetchone()
    
    # 현재 데이터가 없으면 업데이트
    if not current:
        updated_data = update_current_data()
        result = {
            "temperature": updated_data['temperature'],
            "humidity": updated_data['humidity'],
            "light": updated_data['light'],
            "pressure": updated_data['pressure'],
            "vibration": updated_data['vibration'],
            "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        result = dict(current)
    
    conn.close()
    return jsonify(result)

# API 라우트: 데이터 업데이트 트리거
@app.route('/api/update-data', methods=['GET'])
def api_update_data():
    updated_data = update_current_data()
    
    result = {
        **updated_data,
        "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return jsonify(result)

# HTML 파일 제공
@app.route('/')
def index():
    return send_from_directory('.', 'sensor_dashboard.html')

# 센서 매니저 초기화
def initialize_sensors():
    """센서 매니저 초기화"""
    global sensor_manager
    
    print("실제 센서 연결 시도 중...")
    sensor_manager = SensorManager()
    
    if sensor_manager.initialize_sensors():
        status = sensor_manager.get_sensor_status()
        print(f"센서 초기화 완료: {status['sensor_count']}/2개 센서 연결")
        if status['fallback_mode']:
            print("WARNING: 폴백 모드로 동작 (더미 데이터 사용)")
        return True
    else:
        print("WARNING: 모든 센서 연결 실패. 더미 데이터만 사용합니다.")
        sensor_manager = None
        return False

# 시작 시 데이터베이스 존재 확인
def initialize_database():
    if not os.path.exists('sensor_data.db'):
        print("Database not found. Please run sensor_data_generator.py first.")
        print("Attempting to run it now...")
        try:
            import sensor_data_generator
            sensor_data_generator.main()
            print("Database created successfully!")
        except Exception as e:
            print(f"Error creating database: {e}")
            print("Please run sensor_data_generator.py manually.")

if __name__ == '__main__':
    print("=" * 60)
    print("EZ-Dash 센서 대시보드 API 서버 시작")
    print("=" * 60)
    
    # 데이터베이스 초기화
    initialize_database()
    
    # 센서 초기화
    initialize_sensors()
    
    print("\nFlask 서버 시작... (포트 5001)")
    print("대시보드 접속: http://localhost:5001")
    print("Ctrl+C로 종료\n")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5001)
    except KeyboardInterrupt:
        print("\n서버 종료 중...")
        if sensor_manager:
            sensor_manager.close_sensors()
        print("서버가 정상적으로 종료되었습니다.")
    except Exception as e:
        print(f"서버 오류: {e}")
        if sensor_manager:
            sensor_manager.close_sensors()