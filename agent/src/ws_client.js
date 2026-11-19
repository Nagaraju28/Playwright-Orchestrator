const WebSocket = require('ws');
const config = require('./config');

class AgentWebSocketClient {
  constructor(options = {}) {
    this.agentId = options.agentId || config.agentId;
    this.wsUrl = options.wsUrl || `${config.controlPlaneWsUrl}/agent/${this.agentId}`;
    this.ws = null;
    this.isConnected = false;
    this.reconnectTimer = null;
    this.onMessageHandler = null;
  }

  connect() {
    if (!this.agentId) {
      console.warn('[AgentWS] Cannot connect without agentId. Register agent first.');
      return;
    }

    console.log(`[AgentWS] Connecting to Control Plane at ${this.wsUrl}...`);
    this.ws = new WebSocket(this.wsUrl);

    this.ws.on('open', () => {
      this.isConnected = true;
      console.log('[AgentWS] WebSocket connection established successfully.');
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    });

    this.ws.on('message', (data) => {
      try {
        const payload = JSON.parse(data.toString());
        if (this.onMessageHandler) {
          this.onMessageHandler(payload);
        }
      } catch (err) {
        console.error('[AgentWS] Failed to parse incoming message:', err);
      }
    });

    this.ws.on('close', () => {
      this.isConnected = false;
      console.warn('[AgentWS] WebSocket disconnected. Scheduling reconnect in 5s...');
      this.scheduleReconnect();
    });

    this.ws.on('error', (err) => {
      console.error('[AgentWS] WebSocket error:', err.message);
      this.ws.close();
    });
  }

  scheduleReconnect() {
    if (!this.reconnectTimer) {
      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null;
        this.connect();
      }, 5000);
    }
  }

  sendLog(jobId, logLine, streamType = 'stdout') {
    if (!this.isConnected || !this.ws) {
      console.warn('[AgentWS] Cannot send log, socket offline:', logLine);
      return;
    }
    const message = {
      type: 'LOG_STREAM',
      job_id: jobId,
      agent_id: this.agentId,
      stream: streamType,
      data: logLine,
      timestamp: new Date().toISOString(),
    };
    this.ws.send(JSON.stringify(message));
  }

  close() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) this.ws.close();
  }
}

module.exports = AgentWebSocketClient;
