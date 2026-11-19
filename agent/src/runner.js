const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

class PlaywrightRunner {
  /**
   * Executes Playwright test suite in the target workspace and streams stdout/stderr.
   *
   * @param {string} jobDir - Directory where repo was cloned/prepared
   * @param {object} job - Job parameters (job_id, cli_arguments, target_tags, environment)
   * @param {object} wsClient - Active WebSocket client for streaming
   * @returns {Promise<{ exitCode: number, durationMs: number, resultsPath: string|null }>}
   */
  static execute(jobDir, job, wsClient) {
    return new Promise((resolve, reject) => {
      const jobId = job.job_id;
      const startTime = Date.now();

      wsClient.sendLog(jobId, `\r\n\x1b[1;36m[Playwright Harness] Initializing test runner in ${jobDir}...\x1b[0m\r\n`);

      const isWin = process.platform === 'win32';
      const npxExecutable = isWin ? 'npx.cmd' : 'npx';

      // Ensure results output directory exists
      const reportDir = path.join(jobDir, 'test-results');
      fs.mkdirSync(reportDir, { recursive: true });
      const resultsJsonPath = path.join(reportDir, 'results.json');

      // Build Playwright CLI arguments
      const args = ['playwright', 'test'];

      // Grep / tags filter
      if (job.target_tags) {
        args.push('--grep', job.target_tags);
      }

      // JSON and standard list reporters
      args.push(`--reporter=list,json`);

      // Additional custom CLI arguments
      if (job.cli_arguments) {
        const extra = job.cli_arguments.trim().split(/\s+/).filter(Boolean);
        args.push(...extra);
      }

      wsClient.sendLog(
        jobId,
        `\x1b[90m$ npx ${args.join(' ')}\x1b[0m\r\n\r\n`
      );

      // Environment variables for Playwright
      const runnerEnv = {
        ...process.env,
        CI: '1',
        FORCE_COLOR: '1',
        PLAYWRIGHT_JSON_OUTPUT_NAME: resultsJsonPath,
        EXECUTION_ENVIRONMENT: job.environment || 'production',
      };

      const child = spawn(npxExecutable, args, {
        cwd: jobDir,
        env: runnerEnv,
        shell: isWin,
      });

      // Stream stdout chunk-by-chunk to WebSocket (<500ms latency per NFR-1)
      child.stdout.on('data', (chunk) => {
        wsClient.sendLog(jobId, chunk.toString(), 'stdout');
      });

      // Stream stderr chunk-by-chunk
      child.stderr.on('data', (chunk) => {
        wsClient.sendLog(jobId, chunk.toString(), 'stderr');
      });

      child.on('error', (err) => {
        wsClient.sendLog(jobId, `\r\n\x1b[1;31m[Playwright Error] Failed to launch npx: ${err.message}\x1b[0m\r\n`, 'stderr');
        reject(err);
      });

      child.on('close', (code) => {
        const durationMs = Date.now() - startTime;
        const color = code === 0 ? '\x1b[1;32m' : '\x1b[1;31m';
        wsClient.sendLog(
          jobId,
          `\r\n${color}[Playwright Harness] Execution finished with exit code ${code} (${(durationMs / 1000).toFixed(2)}s).\x1b[0m\r\n`
        );

        const hasReport = fs.existsSync(resultsJsonPath);
        resolve({
          exitCode: code,
          durationMs,
          resultsPath: hasReport ? resultsJsonPath : null,
        });
      });
    });
  }
}

module.exports = PlaywrightRunner;
