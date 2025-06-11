// API 엔드포인트 설정
const API_URL = window.location.origin + '/api';

// 차트 객체 저장용 변수
const charts = {};

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
        
        // 데이터 표시 업데이트
        updateSensorDisplay(data);
        
        // 차트 설정
        setupCharts(data);
        
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
        
        // 위젯 데이터 업데이트
        updateWidgetValues(currentData);
        
        // 상태 업데이트
        document.getElementById('last-update').textContent = `마지막 업데이트: ${formatDateTime(currentData.timestamp)}`;
        document.getElementById('db-status').textContent = '데이터베이스 상태: 연결됨';
        
    } catch (error) {
        console.error('데이터 업데이트 오류:', error);
        document.getElementById('db-status').textContent = '데이터베이스 상태: 오류';
    }
}

// 위젯 및 카드 데이터 표시 업데이트
function updateSensorDisplay(data) {
    // 위젯 업데이트
    updateWidgetValues(data);
}

// 위젯 값 업데이트
function updateWidgetValues(data) {
    // 위젯 업데이트
    document.getElementById('temp-value').innerHTML = 
        data.temperature.toFixed(1) + '<span class="widget-unit">°C</span>';
    document.getElementById('humidity-value').innerHTML = 
        data.humidity.toFixed(1) + '<span class="widget-unit">%</span>';
    document.getElementById('light-value').innerHTML = 
        Math.round(data.light) + '<span class="widget-unit">lux</span>';
    document.getElementById('pressure-value').innerHTML = 
        data.pressure.toFixed(1) + '<span class="widget-unit">Pa</span>';
    document.getElementById('vibration-value').innerHTML = 
        data.vibration.toFixed(2) + '<span class="widget-unit">g</span>';
    document.getElementById('airquality-value').innerHTML = 
        Math.round(data.air_quality) + '<span class="widget-unit">/100</span>';
        
    // 카드 값 업데이트
    document.getElementById('temp-card-value').innerHTML = 
        data.temperature.toFixed(1) + '<span class="sensor-unit">°C</span>';
    document.getElementById('humidity-card-value').innerHTML = 
        data.humidity.toFixed(1) + '<span class="sensor-unit">%</span>';
    document.getElementById('light-card-value').innerHTML = 
        Math.round(data.light) + '<span class="sensor-unit">lux</span>';
    document.getElementById('pressure-card-value').innerHTML = 
        data.pressure.toFixed(1) + '<span class="sensor-unit">Pa</span>';
    document.getElementById('vibration-card-value').innerHTML = 
        data.vibration.toFixed(2) + '<span class="sensor-unit">g</span>';
    document.getElementById('airquality-card-value').innerHTML = 
        Math.round(data.air_quality) + '<span class="sensor-unit">/100</span>';
}

// 차트 설정
function setupCharts(data) {
    // 더미 히스토리 데이터 생성 (최근 24시간)
    const timeLabels = generateTimeLabels(24);
    const dummyHistory = generateDummyHistory(24, data);
    
    // 차트 설정값
    const chartConfigs = {
        temperature: {
            id: 'temperatureChart',
            label: '온도 (°C)',
            color: '#FF6384',
            data: dummyHistory.temperature,
            type: 'line'
        },
        humidity: {
            id: 'humidityChart',
            label: '습도 (%)',
            color: '#36A2EB',
            data: dummyHistory.humidity,
            type: 'line'
        },
        light: {
            id: 'lightChart',
            label: '조도 (lux)',
            color: '#FFCE56',
            data: dummyHistory.light,
            type: 'bar'
        },
        pressure: {
            id: 'pressureChart',
            label: '차압 (Pa)',
            color: '#4BC0C0',
            data: dummyHistory.pressure,
            type: 'line'
        },
        vibration: {
            id: 'vibrationChart',
            label: '진동 (g)',
            color: '#9966FF',
            data: dummyHistory.vibration,
            type: 'bar'
        },
        airquality: {
            id: 'airqualityChart',
            label: '공기질 (/100)',
            color: '#00d084',
            data: dummyHistory.airquality,
            type: 'line'
        }
    };

    // 개별 차트 생성
    for (const [sensor, config] of Object.entries(chartConfigs)) {
        const ctx = document.getElementById(config.id);
        if (ctx) {
            // 이미 존재하는 차트 파괴
            if (charts[sensor]) {
                charts[sensor].destroy();
            }
            
            // 각 센서별 독립 차트 생성
            charts[sensor] = new Chart(ctx.getContext('2d'), {
                type: config.type,
                data: {
                    labels: timeLabels,
                    datasets: [{
                        label: config.label,
                        data: config.data,
                        borderColor: config.color,
                        backgroundColor: config.type === 'bar' 
                            ? config.color + 'B3'  // 70% opacity
                            : config.color + '1A', // 10% opacity
                        tension: 0.4,
                        fill: config.type !== 'bar'
                    }]
                },
                options: getChartOptions(config.label)
            });
        }
    }
    
    // 통합 차트 생성
    const combinedCtx = document.getElementById('combinedChart');
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
                        label: '온도 (°C)',
                        data: dummyHistory.temperature,
                        borderColor: '#FF6384',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.4,
                        yAxisID: 'y1'
                    },
                    {
                        label: '습도 (%)',
                        data: dummyHistory.humidity,
                        borderColor: '#36A2EB',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.4,
                        yAxisID: 'y1'
                    },
                    {
                        label: '조도 (lux/10)',
                        data: dummyHistory.light.map(v => v/10),
                        borderColor: '#FFCE56',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.4,
                        yAxisID: 'y1'
                    },
                    {
                        label: '차압 (Pa)',
                        data: dummyHistory.pressure,
                        borderColor: '#4BC0C0',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.4,
                        yAxisID: 'y1'
                    },
                    {
                        label: '진동 (g*100)',
                        data: dummyHistory.vibration.map(v => v*100),
                        borderColor: '#9966FF',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { display: false }
                    },
                    y1: {
                        type: 'linear',
                        position: 'left',
                        title: {
                            display: true,
                            text: '측정값'
                        },
                        grid: {
                            borderDash: [2, 2]
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: '통합 센서 데이터'
                    }
                }
            }
        });
    }
}

// 더미 차트 설정 (오류 발생 시)
function setupDummyCharts() {
    // 시간 레이블
    const timeLabels = generateTimeLabels(24);
    
    // 더미 데이터
    const dummyData = {
        temperature: Array.from({length: 24}, () => Math.random() * 8 + 20),
        humidity: Array.from({length: 24}, () => Math.random() * 35 + 40),
        light: Array.from({length: 24}, () => Math.random() * 1000 + 500),
        pressure: Array.from({length: 24}, () => Math.random() * 15 + 5),
        vibration: Array.from({length: 24}, () => Math.random() * 0.49 + 0.01),
        airquality: Array.from({length: 24}, () => Math.random() * 40 + 30)
    };
    
    setupCharts({
        temperature: dummyData.temperature[23],
        humidity: dummyData.humidity[23],
        light: dummyData.light[23],
        pressure: dummyData.pressure[23],
        vibration: dummyData.vibration[23],
        air_quality: dummyData.airquality[23]
    });
}

// 더미 히스토리 데이터 생성
function generateDummyHistory(hours, currentData) {
    const data = {
        temperature: [],
        humidity: [],
        light: [],
        pressure: [],
        vibration: [],
        airquality: []
    };
    
    for (let i = 0; i < hours; i++) {
        data.temperature.push(currentData.temperature + (Math.random() - 0.5) * 4);
        data.humidity.push(currentData.humidity + (Math.random() - 0.5) * 10);
        data.light.push(currentData.light + (Math.random() - 0.5) * 200);
        data.pressure.push(currentData.pressure + (Math.random() - 0.5) * 5);
        data.vibration.push(currentData.vibration + (Math.random() - 0.5) * 0.1);
        data.airquality.push(currentData.air_quality + (Math.random() - 0.5) * 10);
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

// 차트 옵션 가져오기 함수
function getChartOptions(title) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            },
            title: {
                display: true,
                text: title,
                font: {
                    size: 12
                }
            }
        },
        scales: {
            x: {
                display: false
            },
            y: {
                beginAtZero: false
            }
        }
    };
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