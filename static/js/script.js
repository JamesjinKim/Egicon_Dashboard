// API 엔드포인트 설정
const API_URL = window.location.origin + '/api';

// 차트 객체 저장용 변수
const charts = {};

// 센서별 차트 ID 매핑
const SENSOR_CHARTS = {
    sht40: {
        temperature: 'sht40-temperature-chart',
        humidity: 'sht40-humidity-chart'
    },
    bme688: {
        temperature: 'bme688-temperature-chart',
        humidity: 'bme688-humidity-chart',
        pressure: 'bme688-pressure-chart',
        airquality: 'bme688-airquality-chart'
    },
    sdp810: {
        pressure: 'sdp810-pressure-chart'
    },
    bh1750: {
        light: 'bh1750-light-chart'
    },
    virtual: {
        vibration: 'virtual-vibration-chart'
    },
    sps30: {
        pm1: 'sps30-pm1-chart',
        pm25: 'sps30-pm25-chart',
        pm4: 'sps30-pm4-chart',
        pm10: 'sps30-pm10-chart'
    }
};

// 센서별 위젯 ID 매핑
const SENSOR_WIDGETS = {
    sht40: {
        temperature: 'sht40-temp-value',
        humidity: 'sht40-humidity-value',
        status: 'sht40-status'
    },
    bme688: {
        temperature: 'bme688-temp-value',
        humidity: 'bme688-humidity-value',
        pressure: 'bme688-pressure-value',
        airquality: 'bme688-airquality-value',
        status: 'bme688-status'
    },
    sdp810: {
        pressure: 'sdp810-pressure-value',
        status: 'sdp810-status'
    },
    bh1750: {
        light: 'bh1750-light-value',
        status: 'bh1750-status'
    },
    virtual: {
        vibration: 'virtual-vibration-value'
    },
    sps30: {
        pm1: 'sps30-pm1-value',
        pm25: 'sps30-pm25-value',
        pm4: 'sps30-pm4-value',
        pm10: 'sps30-pm10-value',
        status: 'sps30-status'
    }
};

// 센서별 업데이트 간격 설정 (밀리초)
const SENSOR_UPDATE_INTERVALS = {
    sht40: 5000,      // 5초 - 온도/습도 변화 매우 느림
    bme688: 3000,     // 3초 - 가스저항은 중간 속도
    bh1750: 1000,     // 1초 - 조도 변화 빠름 (조명, 그림자)
    sdp810: 500,      // 0.5초 - 차압 변화 가장 빠름
    sps30: 3000,      // 3초 - 미세먼지 변화 중간 속도
    virtual: 2000     // 2초 - 가상 진동 센서
};

let sensorTimers = {};
let lastSensorData = {};
let logPaused = false;
let maxLogEntries = 100;

// 연결된 센서 목록 가져오기
async function getConnectedSensors() {
    try {
        const response = await fetch(`${API_URL}/status`);
        if (!response.ok) throw new Error('센서 상태 조회 실패');
        
        const status = await response.json();
        const connectedSensors = [];
        
        // 각 센서별 연결 상태 확인
        if (status.sht40) connectedSensors.push('sht40');
        if (status.bme688) connectedSensors.push('bme688');
        if (status.bh1750) connectedSensors.push('bh1750');
        if (status.sdp810) connectedSensors.push('sdp810');
        if (status.sps30) connectedSensors.push('sps30');
        
        // virtual은 항상 연결된 것으로 처리
        connectedSensors.push('virtual');
        
        return connectedSensors;
        
    } catch (error) {
        console.error('센서 상태 확인 실패:', error);
        // 오류 시 기본적으로 virtual만 활성화
        return ['virtual'];
    }
}

// DOM이 로드되면 실행
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.getElementById('main-content');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const refreshButton = document.getElementById('refresh-data');

    // 사이드바 토글
    sidebarToggle.addEventListener('click', function() {
        sidebar.classList.toggle('expanded');
        mainContent.classList.toggle('sidebar-expanded');
    });
    
    // 초기 데이터 로드
    loadSensorData();
    
    // 새로고침 버튼 이벤트
    refreshButton.addEventListener('click', function(e) {
        e.preventDefault();
        updateSensorData();
    });
    
    // 센서별 차별화된 업데이트 간격
    initializeSensorScheduler();
    
    // 로그 관련 이벤트 리스너
    initializeLogControls();
});

// 센서별 스케줄러 초기화
async function initializeSensorScheduler() {
    console.log('🔄 센서별 차별화된 업데이트 스케줄러 시작');
    addSensorLog('센서별 차별화된 업데이트 스케줄러 시작', 'info');
    
    // 기존 타이머 정리
    Object.values(sensorTimers).forEach(timer => clearInterval(timer));
    sensorTimers = {};
    
    // 먼저 센서 상태 확인
    const connectedSensors = await getConnectedSensors();
    console.log('🔍 연결된 센서들:', connectedSensors);
    
    // 연결된 센서들만 타이머 설정
    Object.entries(SENSOR_UPDATE_INTERVALS).forEach(([sensorType, interval]) => {
        if (connectedSensors.includes(sensorType)) {
            console.log(`📊 ${sensorType} 센서: ${interval}ms 간격으로 업데이트`);
            addSensorLog(`${interval}ms 간격으로 업데이트 스케줄 설정`, 'info', sensorType.toUpperCase());
            
            sensorTimers[sensorType] = setInterval(() => {
                updateSpecificSensorData(sensorType);
            }, interval);
            
            // 초기 데이터 로드 (0.5초씩 지연하여 동시 호출 방지)
            setTimeout(() => {
                updateSpecificSensorData(sensorType);
            }, connectedSensors.indexOf(sensorType) * 500);
        } else {
            console.log(`❌ ${sensorType} 센서: 연결되지 않음 - 스케줄링 생략`);
            addSensorLog(`연결되지 않음 - 업데이트 생략`, 'warning', sensorType.toUpperCase());
        }
    });
}

// 특정 센서 데이터 업데이트
async function updateSpecificSensorData(sensorType) {
    try {
        const response = await fetch(`${API_URL}/current-sensor/${sensorType}`);
        
        if (!response.ok) {
            // 개별 센서 API가 없는 경우 전체 데이터에서 추출
            return updateSensorDataFromFull(sensorType);
        }
        
        const data = await response.json();
        updateSensorDisplay(sensorType, data);
        addSensorLog(`데이터 업데이트 성공`, 'success', sensorType.toUpperCase());
        
    } catch (error) {
        console.warn(`⚠️ ${sensorType} 센서 데이터 업데이트 실패:`, error);
        addSensorLog(`데이터 업데이트 실패: ${error.message}`, 'error', sensorType.toUpperCase());
        // 개별 실패해도 다른 센서에 영향 없음
    }
}

// 전체 데이터에서 특정 센서 데이터 추출 (폴백)
async function updateSensorDataFromFull(sensorType) {
    try {
        const response = await fetch(`${API_URL}/current`);
        if (!response.ok) throw new Error('전체 데이터 조회 실패');
        
        const fullData = await response.json();
        const sensorData = extractSensorData(sensorType, fullData);
        updateSensorDisplay(sensorType, sensorData);
        
    } catch (error) {
        console.error(`❌ ${sensorType} 폴백 업데이트 실패:`, error);
    }
}

// 전체 데이터에서 센서별 데이터 추출
function extractSensorData(sensorType, fullData) {
    const extracted = {
        timestamp: fullData.timestamp,
        sensor_status: fullData.sensor_status
    };
    
    switch(sensorType) {
        case 'sht40':
            if (fullData.sensor_status?.sht40) {
                extracted.temperature = fullData.temperature;
                extracted.humidity = fullData.humidity;
            }
            break;
        case 'bme688':
            if (fullData.sensor_status?.bme688) {
                extracted.temperature = fullData.temperature;
                extracted.humidity = fullData.humidity;
                extracted.pressure = fullData.pressure;
                extracted.gas_resistance = fullData.gas_resistance;
                extracted.air_quality = fullData.air_quality;
            }
            break;
        case 'bh1750':
            if (fullData.sensor_status?.bh1750) {
                extracted.light = fullData.light;
            }
            break;
        case 'sdp810':
            if (fullData.sensor_status?.sdp810) {
                extracted.differential_pressure = fullData.differential_pressure;
            }
            break;
        case 'virtual':
            extracted.vibration = fullData.vibration;
            break;
        case 'sps30':
            if (fullData.sensor_status?.sps30) {
                extracted.pm1 = fullData.pm1;
                extracted.pm25 = fullData.pm25;
                extracted.pm4 = fullData.pm4;
                extracted.pm10 = fullData.pm10;
            }
            break;
    }
    
    return extracted;
}

// 센서별 UI 업데이트
function updateSensorDisplay(sensorType, data) {
    // 데이터 변화 확인
    const dataKey = `${sensorType}_${data.timestamp}`;
    if (lastSensorData[sensorType] === dataKey) {
        return; // 변화 없으면 UI 업데이트 스킵
    }
    lastSensorData[sensorType] = dataKey;
    
    // 센서 상태 업데이트
    const statusElement = document.getElementById(SENSOR_WIDGETS[sensorType]?.status);
    if (statusElement) {
        const isConnected = data.sensor_status?.[sensorType] || false;
        statusElement.textContent = isConnected ? '연결됨' : '미연결';
        statusElement.className = `sensor-status-indicator ${isConnected ? 'connected' : 'disconnected'}`;
    }
    
    // 센서별 데이터 업데이트
    switch(sensorType) {
        case 'sht40':
            updateSHT40Display(data);
            break;
        case 'bme688':
            updateBME688Display(data);
            break;
        case 'bh1750':
            updateBH1750Display(data);
            break;
        case 'sdp810':
            updateSDP810Display(data);
            break;
        case 'virtual':
            updateVirtualDisplay(data);
            break;
        case 'sps30':
            updateSPS30Display(data);
            break;
    }
    
    console.log(`📊 ${sensorType} 업데이트 완료:`, data);
}

// 센서별 개별 업데이트 함수들
function updateSHT40Display(data) {
    if (data.temperature !== undefined) {
        const tempElement = document.getElementById('sht40-temp-value');
        if (tempElement) {
            tempElement.innerHTML = `${data.temperature.toFixed(1)}<span class="widget-unit">°C</span>`;
        }
    }
    if (data.humidity !== undefined) {
        const humidElement = document.getElementById('sht40-humidity-value');
        if (humidElement) {
            humidElement.innerHTML = `${data.humidity.toFixed(1)}<span class="widget-unit">%</span>`;
        }
    }
}

function updateBME688Display(data) {
    if (data.temperature !== undefined) {
        const tempElement = document.getElementById('bme688-temp-value');
        if (tempElement) {
            tempElement.innerHTML = `${data.temperature.toFixed(1)}<span class="widget-unit">°C</span>`;
        }
    }
    if (data.pressure !== undefined) {
        const pressElement = document.getElementById('bme688-pressure-value');
        if (pressElement) {
            pressElement.innerHTML = `${data.pressure.toFixed(1)}<span class="widget-unit">hPa</span>`;
        }
    }
    if (data.air_quality !== undefined) {
        const aqElement = document.getElementById('bme688-airquality-value');
        if (aqElement) {
            aqElement.innerHTML = `${Math.round(data.air_quality)}<span class="widget-unit">/100</span>`;
        }
    }
}

function updateBH1750Display(data) {
    if (data.light !== undefined) {
        const lightElement = document.getElementById('bh1750-light-value');
        if (lightElement) {
            lightElement.innerHTML = `${Math.round(data.light)}<span class="widget-unit">lux</span>`;
        }
    }
}

function updateSDP810Display(data) {
    if (data.differential_pressure !== undefined) {
        const pressElement = document.getElementById('sdp810-pressure-value');
        if (pressElement) {
            pressElement.innerHTML = `${data.differential_pressure.toFixed(1)}<span class="widget-unit">Pa</span>`;
        }
    }
}

function updateVirtualDisplay(data) {
    if (data.vibration !== undefined) {
        const vibElement = document.getElementById('virtual-vibration-value');
        if (vibElement) {
            vibElement.innerHTML = `${data.vibration.toFixed(2)}<span class="widget-unit">g</span>`;
        }
    }
}

function updateSPS30Display(data) {
    if (data.pm1 !== undefined) {
        const pm1Element = document.getElementById('sps30-pm1-value');
        if (pm1Element) {
            pm1Element.innerHTML = `${data.pm1.toFixed(1)}<span class="widget-unit">μg/m³</span>`;
        }
    }
    if (data.pm25 !== undefined) {
        const pm25Element = document.getElementById('sps30-pm25-value');
        if (pm25Element) {
            pm25Element.innerHTML = `${data.pm25.toFixed(1)}<span class="widget-unit">μg/m³</span>`;
        }
    }
    if (data.pm4 !== undefined) {
        const pm4Element = document.getElementById('sps30-pm4-value');
        if (pm4Element) {
            pm4Element.innerHTML = `${data.pm4.toFixed(1)}<span class="widget-unit">μg/m³</span>`;
        }
    }
    if (data.pm10 !== undefined) {
        const pm10Element = document.getElementById('sps30-pm10-value');
        if (pm10Element) {
            pm10Element.innerHTML = `${data.pm10.toFixed(1)}<span class="widget-unit">μg/m³</span>`;
        }
    }
    // 공기질 지수 계산 및 표시
    if (data.pm25 !== undefined) {
        const airQualityElement = document.getElementById('sps30-airquality-value');
        if (airQualityElement) {
            const airQualityIndex = calculateAirQualityIndex(data.pm25);
            airQualityElement.innerHTML = `${airQualityIndex}<span class="widget-unit">/100</span>`;
        }
    }
}

// 공기질 지수 계산 함수 (PM2.5 기준)
function calculateAirQualityIndex(pm25Value) {
    if (pm25Value <= 15) {
        return Math.max(1, 100 - Math.round(pm25Value));
    } else if (pm25Value <= 35) {
        return Math.max(1, 85 - Math.round((pm25Value - 15) * 2));
    } else if (pm25Value <= 75) {
        return Math.max(1, 45 - Math.round((pm25Value - 35) * 1.5));
    } else {
        return Math.max(1, Math.max(1, 20 - Math.round((pm25Value - 75) * 0.5)));
    }
}

// 센서 데이터 초기 로드
async function loadSensorData() {
    showLoading();
    
    try {
        // 현재 센서 데이터 가져오기 (SPS30 포함)
        const response = await fetch(`${API_URL}/current`);
        
        if (!response.ok) {
            throw new Error('서버 응답 오류');
        }
        
        const data = await response.json();
        
        // 센서별 데이터 업데이트
        updateAllSensorDisplays(data);
        
        // 차트 설정
        setupAllCharts(data);
        
        // 상태 업데이트
        document.getElementById('db-status').textContent = '데이터베이스 상태: 연결됨';
        document.getElementById('last-update').textContent = `마지막 업데이트: ${formatDateTime(data.timestamp)}`;
        
        hideLoading();
    } catch (error) {
        console.error('데이터 로드 오류:', error);
        document.getElementById('db-status').textContent = '데이터베이스 상태: 오류';
        hideLoading();
        
        // 더미 데이터로 차트 초기화 (오류 대비)
        setupDummyCharts();
    }
}

// 센서 데이터 업데이트
async function updateSensorData() {
    try {
        // 현재 데이터 가져오기 (SPS30 포함)
        const currentResponse = await fetch(`${API_URL}/current`);
        
        if (!currentResponse.ok) {
            throw new Error('현재 데이터 조회 오류');
        }
        
        const currentData = await currentResponse.json();
        
        // 센서별 위젯 데이터 업데이트
        updateAllSensorDisplays(currentData);
        
        // 상태 업데이트
        document.getElementById('last-update').textContent = `마지막 업데이트: ${formatDateTime(currentData.timestamp)}`;
        document.getElementById('db-status').textContent = '데이터베이스 상태: 연결됨';
        
    } catch (error) {
        console.error('데이터 업데이트 오류:', error);
        document.getElementById('db-status').textContent = '데이터베이스 상태: 오류';
    }
}

// 모든 센서 디스플레이 업데이트
function updateAllSensorDisplays(data) {
    try {
        if (data && typeof data === 'object') {
            // 각 센서별로 업데이트
            updateSensorSection('sht40', data);
            updateSensorSection('bme688', data);
            updateSensorSection('sdp810', data);
            updateSensorSection('bh1750', data);
            updateVirtualSensors(data);
            updateSPS30Section(data);
        } else {
            // 데이터가 없을 경우 모든 센서를 비연결 상태로 설정
            setAllSensorsDisconnected();
        }
    } catch (error) {
        console.error('센서 디스플레이 업데이트 오류:', error);
        setAllSensorsDisconnected();
    }
}

// 개별 센서 섹션 업데이트 (멀티 센서 지원)
function updateSensorSection(sensorType, data) {
    const sensorArray = data.sensors && data.sensors[sensorType] ? data.sensors[sensorType] : [];
    const statusElement = document.getElementById(SENSOR_WIDGETS[sensorType].status);
    const sectionElement = document.getElementById(`${sensorType}-section`);
    
    if (sensorArray.length > 0) {
        // 센서가 하나 이상 연결됨
        const connectedSensors = sensorArray.filter(s => s.connected);
        
        if (statusElement) {
            if (connectedSensors.length > 0) {
                statusElement.textContent = `연결됨 (${connectedSensors.length}개)`;
                statusElement.className = 'sensor-status-indicator connected';
            } else {
                statusElement.textContent = '오류';
                statusElement.className = 'sensor-status-indicator error';
            }
        }
        
        if (sectionElement) {
            sectionElement.classList.remove('hidden');
        }
        
        // 첫 번째 연결된 센서의 데이터를 위젯에 표시 (레거시 호환성)
        if (connectedSensors.length > 0) {
            const firstSensor = connectedSensors[0];
            updateSensorWidgetFromMulti(sensorType, firstSensor.data, sensorArray.length);
        } else {
            setDefaultSensorValues(sensorType);
        }
    } else {
        // 센서 연결 안됨
        if (statusElement) {
            statusElement.textContent = '연결 안됨';
            statusElement.className = 'sensor-status-indicator disconnected';
        }
        // 섹션을 숨기지 않고 "센서 없음" 상태로 표시
        setDefaultSensorValues(sensorType);
    }
}

// 멀티 센서 데이터에서 위젯 업데이트
function updateSensorWidgetFromMulti(sensorType, data, sensorCount) {
    if (!data) return;
    
    switch (sensorType) {
        case 'sht40':
            updateSensorWidget('sht40', 'temperature', data.temperature, '°C');
            updateSensorWidget('sht40', 'humidity', data.humidity, '%');
            break;
        case 'bme688':
            updateSensorWidget('bme688', 'temperature', data.temperature, '°C');
            updateSensorWidget('bme688', 'humidity', data.humidity, '%');
            updateSensorWidget('bme688', 'pressure', data.pressure, 'hPa');
            updateSensorWidget('bme688', 'airquality', data.air_quality, '/100');
            break;
        case 'sdp810':
            updateSensorWidget('sdp810', 'pressure', data.differential_pressure, 'Pa');
            break;
        case 'bh1750':
            updateSensorWidget('bh1750', 'light', data.light, 'lux');
            break;
    }
}

// 개별 센서 위젯 업데이트
function updateSensorWidget(sensorType, dataType, value, unit) {
    const widgetId = SENSOR_WIDGETS[sensorType][dataType];
    const element = document.getElementById(widgetId);
    
    if (element) {
        let displayValue, statusClass;
        
        if (value !== undefined && value !== null) {
            if (dataType === 'light' || dataType === 'airquality') {
                displayValue = Math.round(value);
            } else {
                displayValue = value.toFixed(1);
            }
            statusClass = 'sensor-connected';
        } else {
            displayValue = '센서 없음';
            statusClass = 'sensor-disconnected';
        }
        
        element.innerHTML = displayValue + '<span class="widget-unit">' + unit + '</span>';
        element.className = element.className.replace(/sensor-\w+/g, '') + ' ' + statusClass;
    }
}

// 가상 센서 업데이트
function updateVirtualSensors(data) {
    const vibrationElement = document.getElementById(SENSOR_WIDGETS.virtual.vibration);
    if (vibrationElement) {
        const vibrationValue = (data.vibration !== undefined && data.vibration !== null) 
            ? data.vibration.toFixed(2) 
            : '0.00';
        vibrationElement.innerHTML = vibrationValue + '<span class="widget-unit">g</span>';
        vibrationElement.className = vibrationElement.className.replace(/sensor-\w+/g, '') + ' sensor-virtual';
    }
}

// SPS30 센서 섹션 업데이트
function updateSPS30Section(data) {
    const statusElement = document.getElementById(SENSOR_WIDGETS.sps30.status);
    const sectionElement = document.getElementById('sps30-section');
    
    // 센서 상태 확인 (/api/current 엔드포인트 데이터 구조에 맞게)
    const isConnected = data.sensor_status && data.sensor_status.sps30;
    const hasData = data.pm1 !== undefined && data.pm1 !== null && data.pm25 !== undefined && data.pm25 !== null;
    
    console.log('🔍 SPS30 섹션 업데이트:', {
        isConnected,
        hasData,
        pm1: data.pm1,
        pm25: data.pm25,
        pm4: data.pm4,
        pm10: data.pm10,
        sensor_status: data.sensor_status
    });
    
    if (statusElement) {
        if (isConnected && hasData) {
            statusElement.textContent = '연결됨';
            statusElement.className = 'sensor-status-indicator connected';
        } else if (isConnected && !hasData) {
            statusElement.textContent = '데이터 없음';
            statusElement.className = 'sensor-status-indicator warning';
        } else {
            statusElement.textContent = '연결 안됨';
            statusElement.className = 'sensor-status-indicator disconnected';
        }
    }
    
    if (sectionElement) {
        sectionElement.classList.remove('hidden');
    }
    
    // SPS30 위젯 데이터 업데이트
    if (isConnected && hasData) {
        updateSPS30Display(data);
        addSensorLog(`미세먼지 데이터 업데이트: PM2.5=${data.pm25.toFixed(1)}μg/m³`, 'success', 'SPS30');
    } else {
        // 기본값 설정
        setDefaultSPS30Values();
        if (isConnected && !hasData) {
            addSensorLog('센서 연결됨, 데이터 대기 중', 'warning', 'SPS30');
        } else {
            addSensorLog('센서 미연결', 'error', 'SPS30');
        }
    }
}

// SPS30 기본값 설정
function setDefaultSPS30Values() {
    const widgets = SENSOR_WIDGETS.sps30;
    const units = {
        pm1: 'μg/m³',
        pm25: 'μg/m³',
        pm4: 'μg/m³',
        pm10: 'μg/m³',
        airquality: '/100'
    };
    
    for (const [dataType, widgetId] of Object.entries(widgets)) {
        if (dataType !== 'status') {
            const element = document.getElementById(widgetId);
            if (element) {
                element.innerHTML = '센서 없음<span class="widget-unit">' + units[dataType] + '</span>';
                element.className = element.className.replace(/sensor-\w+/g, '') + ' sensor-disconnected';
            }
        }
    }
}

// 기본값으로 센서 설정
function setDefaultSensorValues(sensorType) {
    const widgets = SENSOR_WIDGETS[sensorType];
    const units = {
        temperature: '°C',
        humidity: '%',
        pressure: sensorType === 'sdp810' ? 'Pa' : 'hPa',
        airquality: '/100',
        light: 'lux'
    };
    
    for (const [dataType, widgetId] of Object.entries(widgets)) {
        if (dataType !== 'status') {
            const element = document.getElementById(widgetId);
            if (element) {
                element.innerHTML = '센서 없음<span class="widget-unit">' + units[dataType] + '</span>';
                element.className = element.className.replace(/sensor-\w+/g, '') + ' sensor-disconnected';
            }
        }
    }
}

// 모든 센서를 비연결 상태로 설정
function setAllSensorsDisconnected() {
    ['sht40', 'bme688', 'sdp810', 'bh1750'].forEach(sensorType => {
        const statusElement = document.getElementById(SENSOR_WIDGETS[sensorType].status);
        if (statusElement) {
            statusElement.textContent = '연결 안됨';
            statusElement.className = 'sensor-status-indicator disconnected';
        }
        setDefaultSensorValues(sensorType);
    });
}

// 모든 차트 설정
function setupAllCharts(data) {
    // 더미 히스토리 데이터 생성 (최근 24시간)
    const timeLabels = generateTimeLabels(24);
    const dummyHistory = generateDummyHistory(24, data);
    
    // 각 센서별 차트 생성
    setupSensorCharts('sht40', ['temperature', 'humidity'], timeLabels, dummyHistory, data);
    setupSensorCharts('bme688', ['temperature', 'humidity', 'pressure', 'airquality'], timeLabels, dummyHistory, data);
    setupSensorCharts('sdp810', ['pressure'], timeLabels, dummyHistory, data);
    setupSensorCharts('bh1750', ['light'], timeLabels, dummyHistory, data);
    setupSensorCharts('virtual', ['vibration'], timeLabels, dummyHistory, data);
    setupSensorCharts('sps30', ['pm1', 'pm25', 'pm4', 'pm10'], timeLabels, dummyHistory, data);
    
    // 통합 차트 설정
    setupCombinedChart(timeLabels, dummyHistory);
}

// 센서별 차트 설정 (멀티 센서 지원)
function setupSensorCharts(sensorType, dataTypes, timeLabels, dummyHistory, currentData) {
    dataTypes.forEach(dataType => {
        const chartId = SENSOR_CHARTS[sensorType][dataType];
        const ctx = document.getElementById(chartId);
        
        if (ctx) {
            // 이미 존재하는 차트 파괴
            if (charts[chartId]) {
                charts[chartId].destroy();
            }
            
            const config = getMultiSensorChartConfig(sensorType, dataType, timeLabels, dummyHistory, currentData);
            charts[chartId] = new Chart(ctx.getContext('2d'), config);
        }
    });
}

// 멀티 센서 차트 설정 가져오기
function getMultiSensorChartConfig(sensorType, dataType, timeLabels, dummyHistory, currentData) {
    const sensorArray = currentData.sensors && currentData.sensors[sensorType] ? currentData.sensors[sensorType] : [];
    const connectedSensors = sensorArray.filter(s => s.connected);
    
    const baseColors = {
        sht40: { temperature: '#ff6b6b', humidity: '#4ecdc4' },
        bme688: { temperature: '#ff9f43', humidity: '#54a0ff', pressure: '#5f27cd', airquality: '#00d2d3' },
        sdp810: { pressure: '#ff3838' },
        bh1750: { light: '#ffb142' },
        virtual: { vibration: '#8c7ae6' },
        sps30: { pm1: '#2ecc71', pm25: '#f39c12', pm4: '#e74c3c', pm10: '#9b59b6' }
    };
    
    const units = {
        temperature: '°C',
        humidity: '%',
        pressure: sensorType === 'sdp810' ? 'Pa' : 'hPa',
        airquality: '/100',
        light: 'lux',
        vibration: 'g',
        pm1: 'μg/m³',
        pm25: 'μg/m³',
        pm4: 'μg/m³',
        pm10: 'μg/m³'
    };
    
    const labels = {
        temperature: '온도',
        humidity: '습도',
        pressure: sensorType === 'sdp810' ? '차압' : '절대압력',
        airquality: '공기질',
        light: '조도',
        vibration: '진동',
        pm1: 'PM1.0',
        pm25: 'PM2.5',
        pm4: 'PM4.0',
        pm10: 'PM10'
    };
    
    const chartType = (dataType === 'light' || dataType === 'vibration') ? 'bar' : 'line';
    const baseColor = baseColors[sensorType][dataType];
    
    // 멀티 센서를 위한 데이터셋 생성
    const datasets = [];
    
    if (connectedSensors.length > 1) {
        // 여러 센서가 있을 경우 각각을 다른 라인으로
        connectedSensors.forEach((sensor, index) => {
            const colorVariation = adjustColorBrightness(baseColor, index * 30);
            const dataKey = dataType === 'pressure' && sensorType === 'sdp810' ? 'differential_pressure' : dataType;
            const data = generateSensorHistory(dummyHistory[dataKey] || Array(24).fill(0), index);
            
            datasets.push({
                label: `${sensor.alias} ${labels[dataType]} (${units[dataType]})`,
                data: data,
                borderColor: colorVariation,
                backgroundColor: chartType === 'bar' ? colorVariation + 'B3' : colorVariation + '1A',
                tension: 0.4,
                fill: chartType !== 'bar'
            });
        });
    } else {
        // 센서가 하나이거나 없을 경우 기본 처리
        const dataKey = dataType === 'pressure' && sensorType === 'sdp810' ? 'differential_pressure' : dataType;
        const data = dummyHistory[dataKey] || Array(24).fill(0);
        const alias = connectedSensors.length > 0 ? connectedSensors[0].alias : `${sensorType.toUpperCase()}`;
        
        datasets.push({
            label: `${alias} ${labels[dataType]} (${units[dataType]})`,
            data: data,
            borderColor: baseColor,
            backgroundColor: chartType === 'bar' ? baseColor + 'B3' : baseColor + '1A',
            tension: 0.4,
            fill: chartType !== 'bar'
        });
    }
    
    return {
        type: chartType,
        data: {
            labels: timeLabels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    display: connectedSensors.length > 1,
                    position: 'top'
                },
                title: {
                    display: true,
                    text: `${sensorType.toUpperCase()} ${labels[dataType]}`,
                    font: { size: 12 }
                }
            },
            scales: {
                x: { display: false },
                y: { beginAtZero: false }
            }
        }
    };
}

// 색상 밝기 조정 함수
function adjustColorBrightness(color, percent) {
    const num = parseInt(color.replace("#", ""), 16);
    const amt = Math.round(2.55 * percent);
    const R = (num >> 16) + amt;
    const G = (num >> 8 & 0x00FF) + amt;
    const B = (num & 0x0000FF) + amt;
    return "#" + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
        (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
        (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
}

// 센서별 히스토리 데이터 생성 (약간의 변화 추가)
function generateSensorHistory(baseData, sensorIndex) {
    return baseData.map(value => {
        const variation = (Math.random() - 0.5) * 2 * (sensorIndex + 1);
        return value + variation;
    });
}

// 차트 설정 가져오기 (레거시 호환성)
function getChartConfig(sensorType, dataType, timeLabels, dummyHistory) {
    const colors = {
        sht40: { temperature: '#ff6b6b', humidity: '#4ecdc4' },
        bme688: { temperature: '#ff9f43', humidity: '#54a0ff', pressure: '#5f27cd', airquality: '#00d2d3' },
        sdp810: { pressure: '#ff3838' },
        bh1750: { light: '#ffb142' },
        virtual: { vibration: '#8c7ae6' }
    };
    
    const units = {
        temperature: '°C',
        humidity: '%',
        pressure: sensorType === 'sdp810' ? 'Pa' : 'hPa',
        airquality: '/100',
        light: 'lux',
        vibration: 'g'
    };
    
    const labels = {
        temperature: '온도',
        humidity: '습도',
        pressure: sensorType === 'sdp810' ? '차압' : '절대압력',
        airquality: '공기질',
        light: '조도',
        vibration: '진동'
    };
    
    const dataKey = dataType === 'pressure' && sensorType === 'sdp810' ? 'differential_pressure' : dataType;
    const data = dummyHistory[dataKey] || Array(24).fill(0);
    const color = colors[sensorType][dataType];
    const chartType = (dataType === 'light' || dataType === 'vibration') ? 'bar' : 'line';
    
    return {
        type: chartType,
        data: {
            labels: timeLabels,
            datasets: [{
                label: `${labels[dataType]} (${units[dataType]})`,
                data: data,
                borderColor: color,
                backgroundColor: chartType === 'bar' ? color + 'B3' : color + '1A',
                tension: 0.4,
                fill: chartType !== 'bar'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    text: `${sensorType.toUpperCase()} ${labels[dataType]}`,
                    font: { size: 12 }
                }
            },
            scales: {
                x: { display: false },
                y: { beginAtZero: false }
            }
        }
    };
}

// 통합 차트 설정
function setupCombinedChart(timeLabels, dummyHistory) {
    const combinedCtx = document.getElementById('combined-chart');
    if (combinedCtx) {
        // 이미 존재하는 차트 파괴
        if (charts.combined) {
            charts.combined.destroy();
        }
        
        charts.combined = new Chart(combinedCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: timeLabels,
                datasets: [
                    {
                        label: 'SHT40 온도 (°C)',
                        data: dummyHistory.temperature || [],
                        borderColor: '#ff6b6b',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.4
                    },
                    {
                        label: 'SHT40 습도 (%)',
                        data: dummyHistory.humidity || [],
                        borderColor: '#4ecdc4',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.4
                    },
                    {
                        label: 'SDP810 차압 (Pa)',
                        data: dummyHistory.differential_pressure || [],
                        borderColor: '#ff3838',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.4
                    },
                    {
                        label: 'BH1750 조도 (lux/10)',
                        data: (dummyHistory.light || []).map(v => v/10),
                        borderColor: '#ffb142',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top' },
                    title: {
                        display: true,
                        text: '통합 센서 데이터'
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        title: {
                            display: true,
                            text: '측정값'
                        }
                    }
                }
            }
        });
    }
}

// 더미 차트 설정 (오류 발생 시)
function setupDummyCharts() {
    const timeLabels = generateTimeLabels(24);
    const dummyData = {
        temperature: Array.from({length: 24}, () => Math.random() * 8 + 20),
        humidity: Array.from({length: 24}, () => Math.random() * 35 + 40),
        light: Array.from({length: 24}, () => Math.random() * 1000 + 500),
        pressure: Array.from({length: 24}, () => Math.random() * 50 + 1000),
        differential_pressure: Array.from({length: 24}, () => Math.random() * 100 - 50),
        vibration: Array.from({length: 24}, () => Math.random() * 0.49 + 0.01),
        air_quality: Array.from({length: 24}, () => Math.random() * 40 + 30)
    };
    
    setupAllCharts({
        temperature: dummyData.temperature[23],
        humidity: dummyData.humidity[23],
        light: dummyData.light[23],
        pressure: dummyData.pressure[23],
        differential_pressure: dummyData.differential_pressure[23],
        vibration: dummyData.vibration[23],
        air_quality: dummyData.air_quality[23]
    });
}

// 더미 히스토리 데이터 생성
function generateDummyHistory(hours, currentData) {
    const data = {
        temperature: [],
        humidity: [],
        light: [],
        pressure: [],
        differential_pressure: [],
        vibration: [],
        air_quality: []
    };
    
    const defaultValues = {
        temperature: 22.0,
        humidity: 50.0,
        light: 300,
        pressure: 1013.0,
        differential_pressure: 0.0,
        vibration: 0.01,
        air_quality: 50
    };
    
    for (let i = 0; i < hours; i++) {
        data.temperature.push((currentData.temperature || defaultValues.temperature) + (Math.random() - 0.5) * 4);
        data.humidity.push((currentData.humidity || defaultValues.humidity) + (Math.random() - 0.5) * 10);
        data.light.push((currentData.light || defaultValues.light) + (Math.random() - 0.5) * 200);
        data.pressure.push((currentData.pressure || defaultValues.pressure) + (Math.random() - 0.5) * 50);
        data.differential_pressure.push((currentData.differential_pressure || defaultValues.differential_pressure) + (Math.random() - 0.5) * 20);
        data.vibration.push((currentData.vibration || defaultValues.vibration) + (Math.random() - 0.5) * 0.1);
        data.air_quality.push((currentData.air_quality || defaultValues.air_quality) + (Math.random() - 0.5) * 10);
    }
    
    return data;
}

// 시간 레이블 생성 함수 (지난 n시간)
function generateTimeLabels(hours) {
    const labels = [];
    const now = new Date();
    
    for (let i = hours - 1; i >= 0; i--) {
        const time = new Date(now);
        time.setHours(now.getHours() - i);
        labels.push(time.getHours() + ':00');
    }
    
    return labels;
}

// 로딩 표시
function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

// 로딩 숨기기
function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

// 시간 포맷팅
function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.getHours() + ':' + (date.getMinutes() < 10 ? '0' : '') + date.getMinutes();
}

// 날짜 및 시간 포맷팅
function formatDateTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

// 로그 컨트롤 초기화
function initializeLogControls() {
    const clearLogBtn = document.getElementById('clear-log-btn');
    const pauseLogBtn = document.getElementById('pause-log-btn');
    
    if (clearLogBtn) {
        clearLogBtn.addEventListener('click', clearSensorLog);
    }
    
    if (pauseLogBtn) {
        pauseLogBtn.addEventListener('click', toggleLogPause);
    }
}

// 센서 로그 추가
function addSensorLog(message, type = 'info', sensorName = '') {
    if (logPaused) return;
    
    const logOutput = document.getElementById('sensor-log-output');
    if (!logOutput) return;
    
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    
    const prefix = sensorName ? `[${sensorName}] ` : '';
    logEntry.innerHTML = `
        <span class="log-timestamp">[${timestamp}]</span>
        <span class="log-message">${prefix}${message}</span>
    `;
    
    logOutput.appendChild(logEntry);
    
    // 최대 로그 엔트리 수 제한
    const entries = logOutput.querySelectorAll('.log-entry');
    if (entries.length > maxLogEntries) {
        entries[0].remove();
    }
    
    // 자동 스크롤
    logOutput.scrollTop = logOutput.scrollHeight;
}

// 센서 로그 지우기
function clearSensorLog() {
    const logOutput = document.getElementById('sensor-log-output');
    if (logOutput) {
        logOutput.innerHTML = `
            <div class="log-entry info">
                <span class="log-timestamp">[${new Date().toLocaleTimeString()}]</span>
                <span class="log-message">로그가 지워졌습니다.</span>
            </div>
        `;
    }
}

// 로그 일시정지/재개
function toggleLogPause() {
    const pauseLogBtn = document.getElementById('pause-log-btn');
    if (!pauseLogBtn) return;
    
    logPaused = !logPaused;
    
    if (logPaused) {
        pauseLogBtn.innerHTML = '<i class="fas fa-play"></i> 재개';
        pauseLogBtn.style.backgroundColor = '#27ae60';
        addSensorLog('로그 모니터링이 일시정지되었습니다.', 'warning');
    } else {
        pauseLogBtn.innerHTML = '<i class="fas fa-pause"></i> 일시정지';
        pauseLogBtn.style.backgroundColor = '#f39c12';
        addSensorLog('로그 모니터링이 재개되었습니다.', 'info');
    }
}