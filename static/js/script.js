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
    }
};

let updateInterval;
let isUpdating = false;

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
    
    // 3초마다 자동 업데이트
    setInterval(updateSensorData, 3000);
});

// 센서 데이터 초기 로드
async function loadSensorData() {
    showLoading();
    
    try {
        // 현재 센서 데이터 가져오기
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
        // 현재 데이터 가져오기
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
        } else {
            // 데이터가 없을 경우 모든 센서를 비연결 상태로 설정
            setAllSensorsDisconnected();
        }
    } catch (error) {
        console.error('센서 디스플레이 업데이트 오류:', error);
        setAllSensorsDisconnected();
    }
}

// 개별 센서 섹션 업데이트
function updateSensorSection(sensorType, data) {
    const sensorStatus = data.sensor_status && data.sensor_status[sensorType];
    const statusElement = document.getElementById(SENSOR_WIDGETS[sensorType].status);
    const sectionElement = document.getElementById(`${sensorType}-section`);
    
    if (sensorStatus) {
        // 센서 연결됨
        if (statusElement) {
            statusElement.textContent = '연결됨';
            statusElement.className = 'sensor-status-indicator connected';
        }
        if (sectionElement) {
            sectionElement.classList.remove('hidden');
        }
        
        // 센서별 데이터 업데이트
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
    
    // 통합 차트 설정
    setupCombinedChart(timeLabels, dummyHistory);
}

// 센서별 차트 설정
function setupSensorCharts(sensorType, dataTypes, timeLabels, dummyHistory, currentData) {
    dataTypes.forEach(dataType => {
        const chartId = SENSOR_CHARTS[sensorType][dataType];
        const ctx = document.getElementById(chartId);
        
        if (ctx) {
            // 이미 존재하는 차트 파괴
            if (charts[chartId]) {
                charts[chartId].destroy();
            }
            
            const config = getChartConfig(sensorType, dataType, timeLabels, dummyHistory);
            charts[chartId] = new Chart(ctx.getContext('2d'), config);
        }
    });
}

// 차트 설정 가져오기
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