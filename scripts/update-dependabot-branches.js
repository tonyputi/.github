module.exports = async ({github, context, core}) => {
  const repo = context.repo;
  const {data: repository} = await github.rest.repos.get(repo);
  const base = repository.default_branch;
  const eligible = pr =>
    pr.user.login === 'dependabot[bot]' && pr.user.id === 49699333 &&
    pr.state === 'open' && pr.draft === false && pr.auto_merge !== null &&
    pr.auto_merge !== undefined &&
    pr.head.repo?.id === repository.id && pr.base.repo?.id === repository.id &&
    pr.base.ref === base;
  const pulls = await github.paginate(github.rest.pulls.list, {
    ...repo, state: 'open', base, per_page: 100
  });
  for (const candidate of pulls.filter(eligible)) {
    const pull_number = candidate.number;
    const label = `PR #${pull_number}`;
    try {
      const {data: pr} = await github.rest.pulls.get({...repo, pull_number});
      if (!eligible(pr)) continue;
      const {data: branch} = await github.rest.repos.getBranch({...repo, branch: base});
      const baseSha = branch.commit.sha;
      const headSha = pr.head.sha;
      const {data: comparison} = await github.rest.repos.compareCommitsWithBasehead({
        ...repo, basehead: `${baseSha}...${headSha}`
      });
      if (comparison.merge_base_commit.sha === baseSha) {
        core.info(`${label}: already up to date.`);
        continue;
      }
      if (pr.mergeable === false) {
        core.setFailed(`${label}: merge conflict; resolve manually.`);
        continue;
      }
      if (pr.mergeable !== true) {
        core.warning(`${label}: mergeability unknown; deferred to the next run.`);
        continue;
      }
      const checks = await github.paginate(github.rest.checks.listForRef, {
        ...repo, ref: headSha, filter: 'latest', per_page: 100
      });
      const {data: status} = await github.rest.repos.getCombinedStatusForRef({
        ...repo, ref: headSha
      });
      if (checks.some(check => check.status !== 'completed' ||
          !['success', 'neutral', 'skipped'].includes(check.conclusion)) ||
          ['failure', 'error'].includes(status.state) ||
          status.statuses.some(item => item.state === 'pending')) {
        core.warning(`${label}: checks failed or are pending; no update attempted.`);
        continue;
      }
      const {data: current} = await github.rest.pulls.get({...repo, pull_number});
      const {data: currentRepo} = await github.rest.repos.get(repo);
      const {data: currentBase} = await github.rest.repos.getBranch({...repo, branch: base});
      if (!eligible(current) || current.head.sha !== headSha ||
          current.base.sha !== baseSha || currentBase.commit.sha !== baseSha ||
          currentRepo.default_branch !== base) {
        core.warning(`${label}: head or base changed; deferred to the next run.`);
        continue;
      }
      await github.rest.pulls.updateBranch({
        ...repo, pull_number, expected_head_sha: headSha
      });
      core.info(`${label}: branch update accepted; fresh PR checks and valid human review are required.`);
    } catch (error) {
      core.setFailed(`${label}: API error (${error.status ?? 'unknown'}); no retry. Inspect the PR and rerun after resolution.`);
    }
  }
};
