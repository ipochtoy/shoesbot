"""Analytics Dashboard for ShoesBot - Web interface for statistics and metrics."""
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string
from shoesbot.metrics import get_all_events
from shoesbot.barcode_database import get_barcode_db
from shoesbot.cache_manager import get_cache
from shoesbot.logging_setup import logger

app = Flask(__name__)

# Configuration
DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', 8080))
DASHBOARD_HOST = os.getenv('DASHBOARD_HOST', '0.0.0.0')


def get_time_series_data(hours=24):
    """Get time series data for the last N hours."""
    events = get_all_events()
    if not events:
        return []

    now = datetime.now()
    cutoff = now - timedelta(hours=hours)

    # Group events by hour
    hourly_data = {}
    for event in events:
        try:
            ts = datetime.fromisoformat(event['ts'])
            if ts < cutoff:
                continue

            hour_key = ts.strftime('%Y-%m-%d %H:00')
            if hour_key not in hourly_data:
                hourly_data[hour_key] = {
                    'timestamp': hour_key,
                    'total': 0,
                    'success': 0,
                    'empty': 0,
                    'avg_time': [],
                }

            hourly_data[hour_key]['total'] += 1
            if event.get('result_count', 0) > 0:
                hourly_data[hour_key]['success'] += 1
            else:
                hourly_data[hour_key]['empty'] += 1

            # Calculate average processing time
            timeline = event.get('timeline', [])
            total_time = sum(t.get('ms', 0) for t in timeline)
            hourly_data[hour_key]['avg_time'].append(total_time)

        except Exception as e:
            logger.warning(f"Error processing event for time series: {e}")
            continue

    # Calculate averages
    result = []
    for hour_key in sorted(hourly_data.keys()):
        data = hourly_data[hour_key]
        avg_times = data['avg_time']
        data['avg_processing_time'] = sum(avg_times) / len(avg_times) if avg_times else 0
        del data['avg_time']
        result.append(data)

    return result


def get_decoder_stats():
    """Get statistics by decoder type."""
    events = get_all_events()
    if not events:
        return {}

    decoder_stats = {}
    for event in events:
        timeline = event.get('timeline', [])
        for decoder_info in timeline:
            decoder_name = decoder_info.get('decoder', 'unknown')
            if decoder_name not in decoder_stats:
                decoder_stats[decoder_name] = {
                    'total_runs': 0,
                    'total_hits': 0,
                    'total_time': 0,
                    'errors': 0,
                }

            stats = decoder_stats[decoder_name]
            stats['total_runs'] += 1
            stats['total_hits'] += decoder_info.get('count', 0)
            stats['total_time'] += decoder_info.get('ms', 0)
            if decoder_info.get('error'):
                stats['errors'] += 1

    # Calculate averages
    for decoder_name, stats in decoder_stats.items():
        if stats['total_runs'] > 0:
            stats['avg_time'] = round(stats['total_time'] / stats['total_runs'], 2)
            stats['success_rate'] = round((stats['total_runs'] - stats['errors']) / stats['total_runs'] * 100, 2)
            stats['hit_rate'] = round(stats['total_hits'] / stats['total_runs'] * 100, 2)

    return decoder_stats


def get_overall_stats():
    """Get overall statistics."""
    events = get_all_events()
    db = get_barcode_db()
    cache = get_cache()

    db_stats = db.get_stats()
    cache_stats = cache.get_stats()

    total_scans = len(events)
    success_scans = sum(1 for e in events if e.get('result_count', 0) > 0)
    empty_scans = total_scans - success_scans

    # Calculate average processing time
    total_times = []
    for event in events:
        timeline = event.get('timeline', [])
        total_time = sum(t.get('ms', 0) for t in timeline)
        total_times.append(total_time)

    avg_time = sum(total_times) / len(total_times) if total_times else 0

    return {
        'total_scans': total_scans,
        'success_scans': success_scans,
        'empty_scans': empty_scans,
        'success_rate': round(success_scans / total_scans * 100, 2) if total_scans > 0 else 0,
        'avg_processing_time': round(avg_time, 2),
        'unique_barcodes': db_stats.get('total_unique_barcodes', 0),
        'total_barcode_scans': db_stats.get('total_scans', 0),
        'cache_hit_rate': cache_stats.get('hit_rate_percent', 0),
        'cached_files': cache_stats.get('cached_files', 0),
    }


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/overall')
def api_overall():
    """API endpoint for overall statistics."""
    return jsonify(get_overall_stats())


@app.route('/api/timeseries/<int:hours>')
def api_timeseries(hours):
    """API endpoint for time series data."""
    return jsonify(get_time_series_data(hours))


@app.route('/api/decoders')
def api_decoders():
    """API endpoint for decoder statistics."""
    return jsonify(get_decoder_stats())


@app.route('/api/top_barcodes/<int:limit>')
def api_top_barcodes(limit):
    """API endpoint for top barcodes."""
    db = get_barcode_db()
    top = db.get_top_barcodes(limit)
    return jsonify(top)


@app.route('/api/recent_scans/<int:limit>')
def api_recent_scans(limit):
    """API endpoint for recent scans."""
    db = get_barcode_db()
    recent = db.get_recent_scans(limit)
    return jsonify(recent)


# HTML Template for Dashboard
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShoesBot Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        .stat-card h3 {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stat-card .value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }
        .stat-card .label {
            font-size: 0.85rem;
            color: #999;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .chart-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .chart-card h2 {
            font-size: 1.3rem;
            margin-bottom: 20px;
            color: #333;
        }
        .table-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #666;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .badge-success {
            background: #d4edda;
            color: #155724;
        }
        .badge-warning {
            background: #fff3cd;
            color: #856404;
        }
        .badge-info {
            background: #d1ecf1;
            color: #0c5460;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: white;
            font-size: 1.2rem;
        }
        .refresh-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: white;
            border: none;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            font-size: 1.5rem;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: transform 0.2s;
        }
        .refresh-btn:hover {
            transform: scale(1.1);
        }
        .refresh-btn:active {
            transform: scale(0.95);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 ShoesBot Analytics Dashboard</h1>

        <div class="loading" id="loading">⏳ Загрузка данных...</div>

        <div id="dashboard" style="display: none;">
            <div class="stats-grid" id="stats-grid"></div>

            <div class="charts-grid">
                <div class="chart-card">
                    <h2>📈 Сканирования за 24 часа</h2>
                    <canvas id="timeSeriesChart"></canvas>
                </div>
                <div class="chart-card">
                    <h2>⚙️ Производительность декодеров</h2>
                    <canvas id="decoderChart"></canvas>
                </div>
            </div>

            <div class="table-card">
                <h2>🏆 Топ-20 штрих-кодов</h2>
                <table id="topBarcodesTable">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Штрих-код</th>
                            <th>Продукт</th>
                            <th>Количество сканирований</th>
                            <th>Последнее сканирование</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>

        <button class="refresh-btn" onclick="loadDashboard()" title="Обновить">🔄</button>
    </div>

    <script>
        let timeSeriesChart = null;
        let decoderChart = null;

        async function loadDashboard() {
            try {
                document.getElementById('loading').style.display = 'block';
                document.getElementById('dashboard').style.display = 'none';

                // Load all data in parallel
                const [overall, timeseries, decoders, topBarcodes] = await Promise.all([
                    fetch('/api/overall').then(r => r.json()),
                    fetch('/api/timeseries/24').then(r => r.json()),
                    fetch('/api/decoders').then(r => r.json()),
                    fetch('/api/top_barcodes/20').then(r => r.json())
                ]);

                // Render stats cards
                renderStatsCards(overall);

                // Render charts
                renderTimeSeriesChart(timeseries);
                renderDecoderChart(decoders);

                // Render top barcodes table
                renderTopBarcodesTable(topBarcodes);

                document.getElementById('loading').style.display = 'none';
                document.getElementById('dashboard').style.display = 'block';
            } catch (error) {
                console.error('Error loading dashboard:', error);
                document.getElementById('loading').textContent = '❌ Ошибка загрузки данных';
            }
        }

        function renderStatsCards(stats) {
            const grid = document.getElementById('stats-grid');
            grid.innerHTML = `
                <div class="stat-card">
                    <h3>Всего сканирований</h3>
                    <div class="value">${stats.total_scans}</div>
                    <div class="label">За все время</div>
                </div>
                <div class="stat-card">
                    <h3>Успешных</h3>
                    <div class="value">${stats.success_rate}%</div>
                    <div class="label">${stats.success_scans} из ${stats.total_scans}</div>
                </div>
                <div class="stat-card">
                    <h3>Среднее время</h3>
                    <div class="value">${stats.avg_processing_time}ms</div>
                    <div class="label">Обработка фото</div>
                </div>
                <div class="stat-card">
                    <h3>Уникальных кодов</h3>
                    <div class="value">${stats.unique_barcodes}</div>
                    <div class="label">В базе данных</div>
                </div>
                <div class="stat-card">
                    <h3>Кэш Vision API</h3>
                    <div class="value">${stats.cache_hit_rate}%</div>
                    <div class="label">${stats.cached_files} файлов</div>
                </div>
                <div class="stat-card">
                    <h3>Всего кодов</h3>
                    <div class="value">${stats.total_barcode_scans}</div>
                    <div class="label">Отсканировано</div>
                </div>
            `;
        }

        function renderTimeSeriesChart(data) {
            const ctx = document.getElementById('timeSeriesChart');

            if (timeSeriesChart) {
                timeSeriesChart.destroy();
            }

            timeSeriesChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => d.timestamp.substring(11, 16)),
                    datasets: [{
                        label: 'Успешных',
                        data: data.map(d => d.success),
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'Пустых',
                        data: data.map(d => d.empty),
                        borderColor: '#ffc107',
                        backgroundColor: 'rgba(255, 193, 7, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        function renderDecoderChart(decoders) {
            const ctx = document.getElementById('decoderChart');

            if (decoderChart) {
                decoderChart.destroy();
            }

            const decoderNames = Object.keys(decoders);
            const avgTimes = decoderNames.map(name => decoders[name].avg_time);
            const successRates = decoderNames.map(name => decoders[name].success_rate);

            decoderChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: decoderNames,
                    datasets: [{
                        label: 'Среднее время (ms)',
                        data: avgTimes,
                        backgroundColor: 'rgba(102, 126, 234, 0.8)',
                        yAxisID: 'y'
                    }, {
                        label: 'Успешность (%)',
                        data: successRates,
                        backgroundColor: 'rgba(40, 167, 69, 0.8)',
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        }
                    },
                    scales: {
                        y: {
                            type: 'linear',
                            position: 'left',
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Время (ms)'
                            }
                        },
                        y1: {
                            type: 'linear',
                            position: 'right',
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: 'Успешность (%)'
                            },
                            grid: {
                                drawOnChartArea: false
                            }
                        }
                    }
                }
            });
        }

        function renderTopBarcodesTable(barcodes) {
            const tbody = document.querySelector('#topBarcodesTable tbody');
            tbody.innerHTML = barcodes.map((item, idx) => `
                <tr>
                    <td><strong>${idx + 1}</strong></td>
                    <td><code>${item.barcode}</code></td>
                    <td>${item.product_name || '<span style="color: #999;">Неизвестно</span>'}</td>
                    <td><span class="badge badge-info">${item.scan_count}x</span></td>
                    <td>${new Date(item.last_seen).toLocaleString('ru-RU')}</td>
                </tr>
            `).join('');
        }

        // Auto-refresh every 30 seconds
        setInterval(loadDashboard, 30000);

        // Initial load
        loadDashboard();
    </script>
</body>
</html>
'''


def run_dashboard():
    """Run the analytics dashboard server."""
    logger.info(f"Starting Analytics Dashboard on http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False)


if __name__ == '__main__':
    run_dashboard()
