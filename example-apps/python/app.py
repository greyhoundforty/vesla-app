from flask import Flask, jsonify
import os
import socket

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <html>
        <head>
            <title>Vesla Test App</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                h1 { color: #2c3e50; }
                .info {
                    background: #ecf0f1;
                    padding: 15px;
                    border-radius: 4px;
                    margin: 10px 0;
                }
                .endpoint {
                    background: #3498db;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 4px;
                    display: inline-block;
                    margin: 5px 0;
                    font-family: monospace;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Vesla Test Application</h1>
                <p>This is a simple Python Flask application for testing Vesla deployments.</p>

                <div class="info">
                    <strong>Hostname:</strong> ''' + socket.gethostname() + '''<br>
                    <strong>Port:</strong> ''' + os.environ.get('PORT', '5000') + '''
                </div>

                <h2>Available Endpoints:</h2>
                <ul>
                    <li><span class="endpoint">GET /</span> - This page</li>
                    <li><span class="endpoint">GET /health</span> - Health check endpoint</li>
                    <li><span class="endpoint">GET /info</span> - JSON info about the app</li>
                </ul>
            </div>
        </body>
    </html>
    '''

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'vesla-test-app'
    }), 200

@app.route('/info')
def info():
    return jsonify({
        'app': 'vesla-test-app',
        'runtime': 'python',
        'hostname': socket.gethostname(),
        'port': os.environ.get('PORT', '5000'),
        'environment': {
            'DEBUG': os.environ.get('DEBUG', 'false'),
            'PORT': os.environ.get('PORT', '5000')
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
