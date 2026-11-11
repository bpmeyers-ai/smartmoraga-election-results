// Serialize workflows as well; this handles Pages backend lag after a run ends.
module.exports = async function deployPages({github, core, context, artifactId,
  sleep = ms => new Promise(resolve => setTimeout(resolve, ms)),
  createAttempts = 12, pollAttempts = 60}) {
  if (!/^\d+$/.test(String(artifactId))) throw new Error('Missing Pages artifact ID');
  const repo = context.repo;
  let deployment;
  for (let attempt = 0; attempt < createAttempts; attempt++) {
    try {
      const oidc = await core.getIDToken();
      core.setSecret(oidc);
      deployment = (await github.request('POST /repos/{owner}/{repo}/pages/deployments', {
        ...repo, artifact_id: Number(artifactId), pages_build_version: context.sha, oidc_token: oidc
      })).data;
      break;
    } catch (error) {
      // Never retry permission, artifact, or validation errors as collisions.
      if (error.status !== 400 || !/due to in progress deployment/i.test(error.message) || attempt + 1 === createAttempts) throw error;
      core.info('Pages still has a deployment in progress; waiting 15 seconds.');
      await sleep(15000);
    }
  }
  if (!deployment) throw new Error('Pages deployment was not created');
  const deployment_id = deployment.id || deployment.status_url?.split('/').pop();
  if (!deployment_id) throw new Error('Pages returned no deployment identifier');
  const terminal = new Set(['deployment_failed', 'deployment_perms_error',
    'deployment_content_failed', 'deployment_cancelled', 'deployment_lost']);
  try {
    for (let attempt = 0; attempt < pollAttempts; attempt++) {
      await sleep(5000);
      const {data} = await github.request('GET /repos/{owner}/{repo}/pages/deployments/{deployment_id}', {...repo, deployment_id});
      core.info(`Pages deployment status: ${data.status}`);
      if (data.status === 'succeed') {
        core.setOutput('page_url', deployment.page_url);
        return;
      }
      if (terminal.has(data.status)) throw new Error(`Pages deployment failed: ${data.status}`);
    }
    throw new Error('Timed out waiting for Pages deployment');
  } catch (error) {
    // Cancel only the deployment this run created, never a competing run.
    try {
      await github.request('POST /repos/{owner}/{repo}/pages/deployments/{deployment_id}/cancel', {...repo, deployment_id});
    } catch { core.warning('Could not cancel this run’s unfinished Pages deployment.'); }
    throw error;
  }
};
