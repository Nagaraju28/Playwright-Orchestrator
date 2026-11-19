const os = require('os');
const fs = require('fs');
const config = require('./config');
const AgentWebSocketClient = require('./ws_client');
const WorkspaceManager = require('./workspace');
const PlaywrightRunner = require('./runner');
const ArtifactUploader = require('./artifacts');

class AgentDaemon {
  constructor() {
    this.agentId = config.agentId;
    this.authToken = config.authToken;
    this.status = 'IDLE';
    this.currentJobId = null;
    this.wsClient = null;
    this.heartbeatInterval = null;
  }

  async start() {
    console.log('========================================================');
    console.log(` Starting Playwright Orchestrator Agent Daemon`);
    console.log(` Host: ${config.hostname} | Platform: ${config.platform}`);
    console.log('========================================================');

    // Register with Control Plane if needed
    if (!this.agentId || !this.authToken) {
      await this.register();
    }

    // Connect WebSocket
    this.wsClient = new AgentWebSocketClient({ agentId: this.agentId });
    this.wsClient.onMessageHandler = (msg) => this.handleMessage(msg);
    this.wsClient.connect();

    // Start Heartbeat Loop
    this.startHeartbeat();
  }

  async register() {
    console.log(`[Agent] Registering node '${config.agentName}' with Control Plane at ${config.controlPlaneUrl}...`);
    try {
      const response = await fetch(`${config.controlPlaneUrl}/api/v1/agents/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: config.agentName,
          hostname: config.hostname,
          platform: config.platform,
          max_concurrent_jobs: 1,
        }),
      });

      if (!response.ok) {
        throw new Error(`Registration failed: ${response.statusText}`);
      }

      const data = await response.json();
      this.agentId = data.id;
      this.authToken = data.auth_token;
      console.log(`[Agent] Registered successfully! Agent ID: ${this.agentId}`);
    } catch (err) {
      console.error(`[Agent] Registration error: ${err.message}`);
    }
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(async () => {
      if (!this.agentId) return;

      const freeMemPercent = Math.round((os.freemem() / os.totalmem()) * 100);
      const metrics = {
        free_mem_percent: freeMemPercent,
        uptime_sec: Math.round(os.uptime()),
        load_avg: os.loadavg(),
      };

      try {
        await fetch(`${config.controlPlaneUrl}/api/v1/agents/heartbeat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Agent-Token': this.authToken,
          },
          body: JSON.stringify({
            agent_id: this.agentId,
            status: this.status,
            current_job_id: this.currentJobId,
            system_metrics: metrics,
          }),
        });
      } catch (err) {
        // Silently retry on next tick
      }
    }, config.heartbeatIntervalMs);
  }

  async handleMessage(msg) {
    console.log('[Agent] Received command from Control Plane:', msg);
    if (msg.type === 'EXECUTE_JOB') {
      const jobId = msg.job_id;
      this.status = 'BUSY';
      this.currentJobId = jobId;

      try {
        this.wsClient.sendLog(jobId, `\r\n\x1b[1;34m[Agent] Starting pipeline for job ${jobId}...\x1b[0m\r\n`);

        // 1. Prepare Workspace & Ingestion (TASK-201, TASK-203)
        const jobDir = await WorkspaceManager.prepareWorkspace(msg, this.wsClient);

        // 2. Install Dependencies (TASK-203)
        await WorkspaceManager.installDependencies(jobDir, jobId, this.wsClient);

        // 3. Playwright Execution Harness (TASK-301)
        const result = await PlaywrightRunner.execute(jobDir, msg, this.wsClient);

        // 4. Artifact Scanning & Upload (TASK-402)
        const artifacts = await ArtifactUploader.scanAndUpload(jobDir, jobId, this.wsClient);

        // 5. Ingest JSON Results (TASK-401)
        if (result.resultsPath && fs.existsSync(result.resultsPath)) {
          try {
            const reportData = JSON.parse(fs.readFileSync(result.resultsPath, 'utf8'));
            await fetch(`${config.controlPlaneUrl}/api/v1/jobs/${jobId}/results`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(reportData),
            });
            this.wsClient.sendLog(jobId, `\x1b[32m[Metrics] Successfully indexed test report in Control Plane.\x1b[0m\r\n`);
          } catch (reportErr) {
            this.wsClient.sendLog(jobId, `\x1b[33m[Metrics] Warning: Could not post test report: ${reportErr.message}\x1b[0m\r\n`);
          }
        }

        // Notify Control Plane of completion
        this.wsClient.sendLog(jobId, JSON.stringify({
          type: 'JOB_EXECUTION_FINISHED',
          job_id: jobId,
          exit_code: result.exitCode,
          duration_ms: result.durationMs,
          results_path: result.resultsPath,
          artifacts_count: artifacts.length,
        }));
      } catch (err) {
        this.wsClient.sendLog(jobId, `\r\n\x1b[1;31m[Agent Error] Job execution failed: ${err.message}\x1b[0m\r\n`, 'stderr');
      } finally {
        this.status = 'IDLE';
        this.currentJobId = null;
      }
    }
  }

  stop() {
    if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
    if (this.wsClient) this.wsClient.close();
    console.log('[Agent] Daemon stopped.');
  }
}

if (require.main === module) {
  const daemon = new AgentDaemon();
  daemon.start().catch((err) => {
    console.error('[Agent] Fatal error starting daemon:', err);
    process.exit(1);
  });

  process.on('SIGINT', () => {
    daemon.stop();
    process.exit(0);
  });
}

module.exports = AgentDaemon;
