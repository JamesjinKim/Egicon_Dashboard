#!/usr/bin/env python3
"""
데이터베이스 마이그레이션 스크립트
SPS30 중복 방지를 위한 UNIQUE 제약조건 추가
"""

import sqlite3
import os
import shutil
from datetime import datetime

def migrate_database():
    db_path = "sensors.db"
    backup_path = f"sensors_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    print("=" * 60)
    print("데이터베이스 마이그레이션 시작")
    print("=" * 60)
    
    if not os.path.exists(db_path):
        print("❌ 데이터베이스 파일이 존재하지 않습니다.")
        return False
    
    # 백업 생성
    print(f"📋 데이터베이스 백업 생성: {backup_path}")
    shutil.copy2(db_path, backup_path)
    
    try:
        # 기존 데이터 읽기
        print("📖 기존 데이터 읽기...")
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 모든 센서 데이터 백업
            cursor.execute("SELECT * FROM sensors")
            all_sensors = [dict(row) for row in cursor.fetchall()]
            
            # SPS30 중복 확인
            sps30_sensors = [s for s in all_sensors if s['name'] == 'SPS30']
            print(f"🔍 SPS30 센서 개수: {len(sps30_sensors)}")
            
            # SPS30 중복 제거 (가장 최근 것만 유지)
            if len(sps30_sensors) > 1:
                print("🗑️ SPS30 중복 제거 중...")
                # 가장 최근 ID만 유지
                latest_sps30 = max(sps30_sensors, key=lambda x: x['id'])
                cursor.execute("""
                    DELETE FROM sensors 
                    WHERE name = 'SPS30' AND communication_type = 'UART' 
                    AND id != ?
                """, (latest_sps30['id'],))
                conn.commit()
                print(f"✅ SPS30 중복 제거 완료 (유지: ID {latest_sps30['id']})")
        
        # 새 스키마로 데이터베이스 재생성
        print("🔄 새 스키마로 데이터베이스 재생성...")
        
        # 임시 데이터베이스 생성
        temp_db_path = "sensors_temp.db"
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        
        with sqlite3.connect(temp_db_path) as temp_conn:
            temp_cursor = temp_conn.cursor()
            
            # 새 스키마 적용
            temp_cursor.execute('''
                CREATE TABLE sensors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address INTEGER,
                    name VARCHAR(50) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    description TEXT,
                    voltage VARCHAR(20),
                    communication_type VARCHAR(20) DEFAULT 'I2C',
                    port_info VARCHAR(100),
                    is_default BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(address, communication_type),
                    UNIQUE(name, communication_type, is_default)
                )
            ''')
            
            # 스캔 히스토리 테이블
            temp_cursor.execute('''
                CREATE TABLE scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bus_number INTEGER NOT NULL,
                    address INTEGER NOT NULL,
                    sensor_id INTEGER,
                    scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sensor_id) REFERENCES sensors(id)
                )
            ''')
            
            # 인덱스 생성
            temp_cursor.execute('CREATE INDEX idx_sensors_address ON sensors(address)')
            temp_cursor.execute('CREATE INDEX idx_scan_history_address ON scan_history(address)')
            temp_cursor.execute('CREATE INDEX idx_scan_history_time ON scan_history(scan_time)')
            
            temp_conn.commit()
        
        # 정리된 데이터를 새 데이터베이스로 이전
        print("📦 데이터 이전 중...")
        with sqlite3.connect(db_path) as old_conn:
            old_conn.row_factory = sqlite3.Row
            old_cursor = old_conn.cursor()
            
            # 중복 제거 후 데이터 다시 읽기
            old_cursor.execute("SELECT * FROM sensors ORDER BY id")
            final_sensors = [dict(row) for row in old_cursor.fetchall()]
            
            with sqlite3.connect(temp_db_path) as temp_conn:
                temp_cursor = temp_conn.cursor()
                
                for sensor in final_sensors:
                    try:
                        temp_cursor.execute('''
                            INSERT INTO sensors 
                            (address, name, type, description, voltage, 
                             communication_type, port_info, is_default, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            sensor['address'], sensor['name'], sensor['type'],
                            sensor['description'], sensor['voltage'], sensor['communication_type'],
                            sensor['port_info'], sensor['is_default'], 
                            sensor['created_at'], sensor['updated_at']
                        ))
                    except sqlite3.IntegrityError as e:
                        print(f"⚠️ 센서 이전 실패 (중복): {sensor['name']} - {e}")
                
                temp_conn.commit()
        
        # 원본을 새 데이터베이스로 교체
        print("🔄 데이터베이스 교체...")
        os.remove(db_path)
        shutil.move(temp_db_path, db_path)
        
        # 결과 확인
        print("✅ 마이그레이션 완료! 결과 확인:")
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as total FROM sensors")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) as sps30_count FROM sensors WHERE name = 'SPS30'")
            sps30_count = cursor.fetchone()[0]
            
            print(f"📊 총 센서 개수: {total}")
            print(f"📊 SPS30 센서 개수: {sps30_count}")
            
            # 스키마 확인
            cursor.execute("PRAGMA table_info(sensors)")
            columns = cursor.fetchall()
            print("📋 테이블 스키마 확인:")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
        
        print("✅ 데이터베이스 마이그레이션 성공!")
        return True
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        # 백업에서 복원
        print("🔄 백업에서 복원 중...")
        shutil.copy2(backup_path, db_path)
        return False

if __name__ == "__main__":
    migrate_database()