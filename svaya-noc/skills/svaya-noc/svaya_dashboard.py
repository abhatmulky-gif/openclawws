import os
import redis
import json
from flask import Flask, jsonify, render_template_string
from dotenv import load_dotenv

load_dotenv('svaya-poc.env')
REDIS_URL = os.getenv('REDIS_URL')

app = Flask(__name__)
r = redis.from_url(REDIS_URL)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Svaya Trust Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;}
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
        h1, h2, h3 { margin-top: 0; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .metric { font-size: 24px; font-weight: bold; color: #2980b9; }
        .badge { background: #27ae60; color: white; padding: 5px 10px; border-radius: 12px; font-size: 14px; }
        .badge.warning { background: #f39c12; }
        .log-box { background: #1e1e1e; color: #00ff00; padding: 15px; border-radius: 5px; font-family: monospace; white-space: pre-wrap; height: 300px; overflow-y: auto; }
        .node-list { list-style-type: none; padding: 0; }
        .node-list li { background: #ecf0f1; margin: 5px 0; padding: 10px; border-radius: 5px; border-left: 4px solid #3498db; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>Svaya Trust Dashboard</h1>
            <p>Phase 1: Advisor Mode (Read-Only) | Geo-Fenced: Bangalore</p>
        </div>
        <div class="badge">DRM Security: ACTIVE</div>
    </div>

    <div class="grid">
        <div class="card">
            <h2>AI Confidence Metrics</h2>
            <p>Confidence Score: <span class="metric" id="confidence">--</span></p>
            <p>Guardrails: <span class="badge warning" id="guardrails">--</span></p>
            <p>Blast Radius: <strong id="radius">--</strong></p>
            <p>RAG Citation: <strong id="citation">--</strong></p>
        </div>

        <div class="card">
            <h2>Per-Node Status</h2>
            <ul class="node-list" id="node-list">
                <li>Waiting for telemetry...</li>
            </ul>
        </div>
    </div>

    <div class="card">
        <h2>Latest Cognitive RCA Output</h2>
        <div class="log-box" id="rca-output">Waiting for engine output...</div>
    </div>

    <script>
        async function fetchData() {
            const response = await fetch('/api/data');
            const data = await response.json();
            
            if (data.state) {
                document.getElementById('confidence').innerText = data.state.confidence;
                document.getElementById('guardrails').innerText = data.state.guardrails;
                document.getElementById('radius').innerText = data.state.blast_radius;
                document.getElementById('citation').innerText = data.state.rag_match;
                
                let nodesHtml = '';
                if(data.state.affected_nodes) {
                    data.state.affected_nodes.forEach(node => {
                        nodesHtml += `<li><strong>${node}</strong>: DRM Key Verified ✅ | QoE Alert Triggered</li>`;
                    });
                }
                document.getElementById('node-list').innerHTML = nodesHtml || '<li>System Healthy</li>';
            }
            
            if (data.rca && data.rca.length > 0) {
                document.getElementById('rca-output').innerText = data.rca[data.rca.length - 1];
            }
        }

        setInterval(fetchData, 2000);
        fetchData();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def api_data():
    state = r.get('dashboard_state')
    rca_len = r.llen('rca_notifications')
    rcas = []
    if rca_len > 0:
        # Get the latest 5 RCAs
        raw_rcas = r.lrange('rca_notifications', max(0, rca_len-5), rca_len-1)
        rcas = [rca.decode('utf-8') for rca in raw_rcas]
        
    return jsonify({
        "state": json.loads(state.decode('utf-8')) if state else None,
        "rca": rcas
    })

if __name__ == '__main__':
    print("Starting Svaya GUI Dashboard on port 5000...")
    app.run(host='0.0.0.0', port=5000)
