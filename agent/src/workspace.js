const fs = require('fs');
const path = require('path');
const { spawn, execFile } = require('child_process');
const config = require('./config');

class WorkspaceManager {
  /**
   * Prepares an isolated working directory for an assigned job.
   */
  static async prepareWorkspace(job, wsClient) {
    const jobId = job.job_id;
    const project = job.project;
    const jobDir = path.join(config.workspaceRoot, jobId);

    wsClient.sendLog(jobId, `[Workspace] Preparing isolated execution workspace at ${jobDir}...`);

    if (fs.existsSync(jobDir)) {
      fs.rmSync(jobDir, { recursive: true, force: true });
    }
    fs.mkdirSync(jobDir, { recursive: true });

    // Handle Git ingestion
    if (project.git_url) {
      await this.cloneGitProject(project, jobDir, jobId, wsClient);
    } else if (project.zip_storage_path) {
      wsClient.sendLog(jobId, `[Workspace] Ingesting bundle from ${project.zip_storage_path}...`);
      await this.extractBundle(project.zip_storage_path, jobDir, jobId, wsClient);
    }

    return jobDir;
  }

  /**
   * Extracts a zip bundle or copies local source files into the job workspace.
   */
  static extractBundle(bundlePath, targetDir, jobId, wsClient) {
    return new Promise((resolve, reject) => {
      const suiteDir = bundlePath.replace(/\.zip$/, '');
      if (fs.existsSync(suiteDir) && fs.statSync(suiteDir).isDirectory()) {
        // Direct folder copy
        try {
          fs.cpSync(suiteDir, targetDir, { recursive: true });
          wsClient.sendLog(jobId, `[Workspace] Copied files directly from ${suiteDir} into workspace.`);
          return resolve();
        } catch (err) {
          // fallback to tar
        }
      }

      // Extract zip using built-in tar or PowerShell
      const isWin = process.platform === 'win32';
      const cmd = isWin ? 'powershell' : 'unzip';
      const args = isWin
        ? ['-NoProfile', '-Command', `Expand-Archive -Path '${bundlePath}' -DestinationPath '${targetDir}' -Force`]
        : ['-o', bundlePath, '-d', targetDir];

      const child = spawn(cmd, args);
      child.on('close', (code) => {
        if (code === 0) {
          wsClient.sendLog(jobId, `[Workspace] Extracted zip bundle successfully.`);
          resolve();
        } else {
          const err = new Error(`Extraction failed with exit code ${code}`);
          wsClient.sendLog(jobId, `[Workspace] ${err.message}`, 'stderr');
          reject(err);
        }
      });
    });
  }

  /**
   * Clones project repository into workspace with PAT authentication.
   */
  static cloneGitProject(project, targetDir, jobId, wsClient) {
    return new Promise((resolve, reject) => {
      let cloneUrl = project.git_url;
      if (project.git_pat && cloneUrl.startsWith('http')) {
        try {
          const u = new URL(cloneUrl);
          u.username = 'oauth2';
          u.password = project.git_pat;
          cloneUrl = u.toString();
        } catch (e) {
          // fallback to bare url
        }
      }

      wsClient.sendLog(jobId, `[Git] Cloning branch '${project.git_branch || 'main'}'...`);

      const args = [
        'clone',
        '--depth', '1',
        '--branch', project.git_branch || 'main',
        cloneUrl,
        targetDir,
      ];

      const child = spawn('git', args);

      child.stdout.on('data', (d) => wsClient.sendLog(jobId, d.toString(), 'stdout'));
      child.stderr.on('data', (d) => {
        // Redact PAT from console logs
        const safeLog = d.toString().replace(project.git_pat || '____', '********');
        wsClient.sendLog(jobId, safeLog, 'stderr');
      });

      child.on('close', (code) => {
        if (code === 0) {
          wsClient.sendLog(jobId, `[Git] Repository cloned successfully.`);
          resolve();
        } else {
          const err = new Error(`Git clone failed with exit code ${code}`);
          wsClient.sendLog(jobId, `[Git] ${err.message}`, 'stderr');
          reject(err);
        }
      });
    });
  }

  /**
   * Runs dependency installation (npm ci) inside the job directory.
   */
  static installDependencies(jobDir, jobId, wsClient) {
    return new Promise((resolve, reject) => {
      const packageJsonPath = path.join(jobDir, 'package.json');
      if (!fs.existsSync(packageJsonPath)) {
        wsClient.sendLog(jobId, `[Dependencies] Warning: No package.json found in repository root.`);
        return resolve();
      }

      const hasLock = fs.existsSync(path.join(jobDir, 'package-lock.json'));
      const installCmd = hasLock ? 'ci' : 'install';
      const cmdArgs = [installCmd, '--no-audit', '--prefer-offline'];

      wsClient.sendLog(jobId, `[Dependencies] Running 'npm ${installCmd}'...`);

      const isWin = process.platform === 'win32';
      const npmExecutable = isWin ? 'npm.cmd' : 'npm';

      const child = spawn(npmExecutable, cmdArgs, {
        cwd: jobDir,
        shell: isWin,
      });

      child.stdout.on('data', (d) => wsClient.sendLog(jobId, d.toString(), 'stdout'));
      child.stderr.on('data', (d) => wsClient.sendLog(jobId, d.toString(), 'stderr'));

      child.on('close', (code) => {
        if (code === 0) {
          wsClient.sendLog(jobId, `[Dependencies] Dependencies installed successfully.`);
          resolve();
        } else {
          const err = new Error(`npm ${installCmd} failed with exit code ${code}`);
          wsClient.sendLog(jobId, `[Dependencies] Error: ${err.message}`, 'stderr');
          reject(err);
        }
      });
    });
  }
}

module.exports = WorkspaceManager;
