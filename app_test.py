#!/usr/bin/env python3
"""
EG-Dash 테스트용 서버
- 센서 없이도 동작하는 테스트 버전
- 더미 데이터로 UI 테스트 가능
"""

from flask import Flask, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import random

app = Flask(__name__)
CORS(app)

def generate_dummy_data():
    """더미 센서 데이터 생성"""
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'temperature': round(20 + random.uniform(-3, 8), 1),
        'humidity': round(45 + random.uniform(-10, 20), 1), 
        'light': round(500 + random.uniform(-200, 300)),
        'pressure': round(10 + random.uniform(-3, 5), 1),
        'vibration': round(0.1 + random.uniform(-0.05, 0.1), 3),
        'gas_resistance': round(50000 + random.uniform(-10000, 20000)),
        'air_quality': round(70 + random.uniform(-20, 25)),
        'absolute_pressure': round(1013 + random.uniform(-5, 10), 1)
    }

@app.route('/')
def index():
    """메인 대시보드 페이지"""
    return render_template('pages/dashboard.html')

@app.route('/dashboard')
def dashboard():
    """대시보드 페이지 (별칭)"""
    return render_template('pages/dashboard.html')

@app.route('/api/current', methods=['GET'])
def get_current_data():
    """현재 센서 데이터 조회 (더미 데이터)"""
    try:
        data = generate_dummy_data()
        return jsonify(data)
    except Exception as e:
        print(f"데이터 생성 오류: {e}")
        return jsonify({'error': f'데이터 생성 실패: {e}'}), 500

@app.route('/api/status', methods=['GET'])
def get_sensor_status():
    """센서 연결 상태 (더미 상태)"""
    return jsonify({
        'connected': True,
        'bme688': True,
        'bh1750': True,
        'total_sensors': 2,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'API 엔드포인트를 찾을 수 없음'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '서버 내부 오류'}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("EG-Dash 테스트 서버")
    print("=" * 60)
    print("✅ 더미 데이터로 테스트 중")
    print(f"🚀 서버 시작: http://localhost:5002")
    print("Ctrl+C로 종료\n")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5002, threaded=True)
    except KeyboardInterrupt:
        print("\n서버 종료 중...")
        print("서버가 정상적으로 종료되었습니다.")