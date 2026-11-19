require('dotenv').config();
const os = require('os');
const path = require('path');

const config = {
  agentName: process.env.AGENT_NAME || `agent-${os.hostname().toLowerCase()}`,
  hostname: os.hostname(),
  platform: os.platform(),
  controlPlaneUrl: process.env.CONTROL_PLANE_URL || 'http://localhost:8000',
  controlPlaneWsUrl: process.env.CONTROL_PLANE_WS_URL || 'ws://localhost:8000/api/v1/ws',
  authToken: process.env.AGENT_AUTH_TOKEN || '',
  agentId: process.env.AGENT_ID || '',
  workspaceRoot: process.env.WORKSPACE_ROOT || path.join(os.homedir(), '.orchestrator-workspaces'),
  heartbeatIntervalMs: parseInt(process.env.HEARTBEAT_INTERVAL_MS || '10000', 10),
};

module.exports = config;
