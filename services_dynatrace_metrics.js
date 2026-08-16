/**
 * Dynatrace Custom Metrics Pusher
 * Add this to each Node.js service (product, user, order)
 * Uses metrics.ingest scope — already available!
 * 
 * Pushes: response_time, request_count, error_count, cpu_usage, memory_usage
 */

const os = require('os');
const process = require('process');

const DT_URL = process.env.DYNATRACE_URL || 'https://isz24970.live.dynatrace.com';
const DT_TOKEN = process.env.DYNATRACE_TOKEN || '';
const SERVICE_NAME = process.env.SERVICE_NAME || 'unknown-service';

/**
 * Push custom metrics to Dynatrace via MINT protocol
 * Format: metric.key,dim1=val1 value timestamp
 */
async function pushMetricsToDynatrace(metrics) {
    if (!DT_TOKEN) return;

    const timestamp = Math.floor(Date.now() / 1000);
    const lines = [];

    for (const [key, value] of Object.entries(metrics)) {
        if (value !== null && value !== undefined) {
            lines.push(
                `custom.perf.${key},service=${SERVICE_NAME} ${value} ${timestamp}`
            );
        }
    }

    if (lines.length === 0) return;

    try {
        const http = require('http');
        const https = require('https');
        const url = new URL(`${DT_URL}/api/v2/metrics/ingest`);
        const body = lines.join('\n');

        const options = {
            hostname: url.hostname,
            port: url.port || 443,
            path: url.pathname,
            method: 'POST',
            headers: {
                'Authorization': `Api-Token ${DT_TOKEN}`,
                'Content-Type': 'text/plain',
                'Content-Length': Buffer.byteLength(body)
            }
        };

        const client = url.protocol === 'https:' ? https : http;
        const req = client.request(options, (res) => {
            if (res.statusCode === 202) {
                console.log(`[DT Metrics] Pushed ${lines.length} metrics for ${SERVICE_NAME}`);
            } else {
                console.log(`[DT Metrics] HTTP ${res.statusCode}`);
            }
        });

        req.on('error', (e) => console.log(`[DT Metrics] Error: ${e.message}`));
        req.write(body);
        req.end();

    } catch (e) {
        console.log(`[DT Metrics] Failed: ${e.message}`);
    }
}

/**
 * Collect system metrics
 */
function getSystemMetrics() {
    const cpus = os.cpus();
    let totalIdle = 0, totalTick = 0;
    cpus.forEach(cpu => {
        for (const type in cpu.times) {
            totalTick += cpu.times[type];
        }
        totalIdle += cpu.times.idle;
    });
    const cpuUsage = 100 - Math.floor(100 * totalIdle / totalTick);

    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const memUsage = Math.floor(100 * (totalMem - freeMem) / totalMem);

    const memMB = Math.floor(process.memoryUsage().heapUsed / 1024 / 1024);

    return { cpuUsage, memUsage, heapUsedMB: memMB };
}

/**
 * Middleware to track response time per request
 * Add to Express: app.use(dynatraceMiddleware)
 */
function dynatraceMiddleware(req, res, next) {
    const start = Date.now();

    res.on('finish', () => {
        const duration = Date.now() - start;
        const isError = res.statusCode >= 400;

        const sys = getSystemMetrics();

        pushMetricsToDynatrace({
            response_time_ms: duration,
            request_count: 1,
            error_count: isError ? 1 : 0,
            cpu_usage_pct: sys.cpuUsage,
            memory_usage_pct: sys.memUsage,
            heap_used_mb: sys.heapUsedMB,
            status_code: res.statusCode
        });
    });

    next();
}

/**
 * Push metrics on interval (background)
 */
function startMetricsCollection(intervalMs = 30000) {
    setInterval(() => {
        const sys = getSystemMetrics();
        pushMetricsToDynatrace({
            cpu_usage_pct: sys.cpuUsage,
            memory_usage_pct: sys.memUsage,
            heap_used_mb: sys.heapUsedMB
        });
    }, intervalMs);

    console.log(`[DT Metrics] Started background collection every ${intervalMs/1000}s`);
}

module.exports = { dynatraceMiddleware, startMetricsCollection, pushMetricsToDynatrace };
