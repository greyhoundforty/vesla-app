const express = require('express');
const os = require('os');

const app = express();
const port = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.send(`
    <html>
        <head>
            <title>Vesla Test App - Node.js</title>
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
                    background: #27ae60;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 4px;
                    display: inline-block;
                    margin: 5px 0;
                    font-family: monospace;
                }
                .badge {
                    background: #16a085;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 0.9em;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Vesla Test Application <span class="badge">Node.js</span></h1>
                <p>This is a simple Node.js Express application for testing Vesla deployments.</p>

                <div class="info">
                    <strong>Runtime:</strong> Node.js ${process.version}<br>
                    <strong>Hostname:</strong> ${os.hostname()}<br>
                    <strong>Port:</strong> ${port}<br>
                    <strong>Environment:</strong> ${process.env.NODE_ENV || 'development'}
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
  `);
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'vesla-test-app-node',
    uptime: process.uptime()
  });
});

app.get('/info', (req, res) => {
  res.json({
    app: 'vesla-test-app',
    runtime: 'nodejs',
    version: process.version,
    hostname: os.hostname(),
    port: port,
    platform: os.platform(),
    arch: os.arch(),
    environment: {
      NODE_ENV: process.env.NODE_ENV || 'development',
      PORT: port
    },
    uptime: process.uptime()
  });
});

app.listen(port, '0.0.0.0', () => {
  console.log(`Vesla Node.js test app listening on port ${port}`);
});
