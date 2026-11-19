const fs = require('fs');
const path = require('path');
const config = require('./config');

class ArtifactUploader {
  /**
   * Scans job execution directory for screenshots, video recordings, and trace zips,
   * then uploads them to the Control Plane artifact storage.
   *
   * @param {string} jobDir - Directory where test ran
   * @param {string} jobId - Job ID
   * @param {object} wsClient - Active WebSocket client
   * @returns {Promise<Array<{ filename: string, url: string }>>}
   */
  static async scanAndUpload(jobDir, jobId, wsClient) {
    const uploaded = [];
    const reportDir = path.join(jobDir, 'test-results');

    if (!fs.existsSync(reportDir)) {
      return uploaded;
    }

    const filesToUpload = this.findArtifactFiles(reportDir);
    if (filesToUpload.length === 0) {
      return uploaded;
    }

    wsClient.sendLog(jobId, `\r\n\x1b[90m[Artifacts] Found ${filesToUpload.length} failure artifact(s). Uploading...\x1b[0m\r\n`);

    for (const filePath of filesToUpload) {
      try {
        const filename = path.basename(filePath);
        const fileBuffer = fs.readFileSync(filePath);

        // Upload to control plane multipart endpoint
        const formData = new FormData();
        const blob = new Blob([fileBuffer]);
        formData.append('file', blob, filename);

        const uploadUrl = `${config.controlPlaneUrl}/api/v1/artifacts/upload/${jobId}`;
        const res = await fetch(uploadUrl, {
          method: 'POST',
          body: formData,
        });

        if (res.ok) {
          const data = await res.json();
          uploaded.push({ filename, url: data.url });
          wsClient.sendLog(jobId, `\x1b[32m[Artifacts] Uploaded ${filename} -> ${data.url}\x1b[0m\r\n`);
        } else {
          wsClient.sendLog(jobId, `\x1b[33m[Artifacts] Upload failed for ${filename}: ${res.statusText}\x1b[0m\r\n`, 'stderr');
        }
      } catch (err) {
        wsClient.sendLog(jobId, `\x1b[31m[Artifacts] Error uploading artifact: ${err.message}\x1b[0m\r\n`, 'stderr');
      }
    }

    return uploaded;
  }

  /**
   * Recursively finds .png, .webm, and .zip artifact files.
   */
  static findArtifactFiles(dir) {
    let results = [];
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        results = results.concat(this.findArtifactFiles(fullPath));
      } else {
        const ext = path.extname(entry.name).toLowerCase();
        if (['.png', '.webm', '.zip'].includes(ext)) {
          results.push(fullPath);
        }
      }
    }
    return results;
  }
}

module.exports = ArtifactUploader;
