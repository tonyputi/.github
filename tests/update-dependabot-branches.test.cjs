const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {spawnSync} = require('node:child_process');
const {test} = require('node:test');

const workflow = readFileSync(`${__dirname}/../.github/workflows/update-dependabot-branches.yml`, 'utf8');
const script = workflow.split('          script: |\n')[1]
  .split('\n').map(line => line.replace(/^ {12}/, '')).join('\n');
const run = new (Object.getPrototypeOf(async function () {}).constructor)('github', 'context', 'core', script);
const repository = {id: 1, default_branch: 'main'};
const pull = () => ({
  number: 1, user: {login: 'dependabot[bot]', id: 49699333},
  state: 'open', draft: false, auto_merge: {}, mergeable: true,
  head: {repo: {id: 1}, sha: 'head'}, base: {repo: {id: 1}, ref: 'main', sha: 'base'}
});

async function exercise(options = {}) {
  const updates = [], warnings = [], failures = [], calls = [];
  let pullReads = 0, branchReads = 0, repoReads = 0, active = 0;
  const github = {
    rest: {
      repos: {
        get: async () => ({data: ++repoReads > 1 && options.newDefault ?
          {...repository, default_branch: 'other'} : repository}),
        getBranch: async () => ({data: {commit: {sha:
          ++branchReads > 1 && options.newBase ? 'new-base' : 'base'}}}),
        compareCommitsWithBasehead: async args => {
          calls.push(['compare', args]);
          return {data: {merge_base_commit: {sha: options.upToDate ? 'base' : 'ancestor'}}};
        },
        getCombinedStatusForRef: async () => ({data: options.status ?? {state: 'pending', statuses: []}})
      },
      checks: {listForRef: Symbol('checks')},
      pulls: {
        list: Symbol('pulls'),
        get: async ({pull_number}) => {
          pullReads++;
          const pr = structuredClone((options.pulls ?? [pull()]).find(pr => pr.number === pull_number));
          if (pullReads === 1) options.changeFirst?.(pr);
          if (pullReads === 2) options.change?.(pr);
          return {data: pr};
        },
        updateBranch: async args => {
          assert.equal(active++, 0, 'branch updates must be serial');
          await new Promise(resolve => setImmediate(resolve));
          active--;
          if (options.apiError && (!options.failNumber || args.pull_number === options.failNumber)) {
            throw Object.assign(new Error('private API detail'), {status: options.apiError});
          }
          updates.push(args);
        }
      }
    },
    paginate: async (endpoint, args) => {
      calls.push(['paginate', args]);
      if (options.readError) throw Object.assign(new Error('read denied'), {status: 403});
      return endpoint === github.rest.pulls.list ? options.pulls ?? [pull()] : options.checks ?? [];
    }
  };
  const core = {
    info: () => {}, warning: message => warnings.push(message), setFailed: message => failures.push(message)
  };
  await run(github, {repo: {owner: 'example', repo: 'project'}}, core);
  return {updates, warnings, failures, calls};
}

test('updates an eligible behind PR with the expected head guard', async () => {
  const {updates, calls} = await exercise();
  assert.deepEqual(updates, [{owner: 'example', repo: 'project', pull_number: 1, expected_head_sha: 'head'}]);
  assert.equal(calls[1][1].basehead, 'base...head');
  assert.equal(calls[0][1].per_page, 100);
});

const ineligible = {
  human: pr => { pr.user.login = 'human'; },
  'wrong bot ID': pr => { pr.user.id = 123; },
  draft: pr => { pr.draft = true; },
  closed: pr => { pr.state = 'closed'; },
  fork: pr => { pr.head.repo.id = 2; },
  'deleted head repository': pr => { pr.head.repo = null; },
  'other base repository': pr => { pr.base.repo.id = 2; },
  'other base branch': pr => { pr.base.ref = 'release'; },
  'auto-merge disabled': pr => { pr.auto_merge = null; },
  'auto-merge absent': pr => { delete pr.auto_merge; }
};
for (const [name, change] of Object.entries(ineligible)) {
  test(`ignores ${name} PRs`, async () => {
    const pr = pull();
    change(pr);
    assert.deepEqual((await exercise({pulls: [pr]})).updates, []);
  });
  test(`rechecks eligibility before updating: ${name}`, async () => {
    const result = await exercise({change});
    assert.deepEqual(result.updates, []);
  });
}

test('rechecks eligibility after listing candidates', async () => {
  const result = await exercise({changeFirst: pr => { pr.auto_merge = null; }});
  assert.deepEqual(result.updates, []);
});

test('uses the live head rather than the candidate list head', async () => {
  const changeHead = pr => { pr.head.sha = 'live-head'; };
  const {updates, calls} = await exercise({changeFirst: changeHead, change: changeHead});
  assert.equal(updates[0].expected_head_sha, 'live-head');
  assert.equal(calls[1][1].basehead, 'base...live-head');
});

test('repeated events do not update a branch that already contains the base', async () => {
  assert.equal((await exercise()).updates.length, 1);
  assert.deepEqual((await exercise({upToDate: true})).updates, []);
});

for (const [name, options] of Object.entries({
  'head race': {change: pr => { pr.head.sha = 'new-head'; }},
  'PR base race': {change: pr => { pr.base.sha = 'new-base'; }},
  'base ref race': {newBase: true},
  'default branch change': {newDefault: true}
})) {
  test(`defers without retry on ${name}`, async () => {
    const result = await exercise(options);
    assert.deepEqual(result.updates, []);
    assert.equal(result.warnings.length, 1);
  });
}

for (const mergeable of [false, null]) {
  test(`does not update when mergeability is ${mergeable}`, async () => {
    const pr = pull();
    pr.mergeable = mergeable;
    const result = await exercise({pulls: [pr]});
    assert.deepEqual(result.updates, []);
    assert.equal(result.failures.length + result.warnings.length, 1);
  });
}

for (const conclusion of ['failure', 'cancelled', 'timed_out', 'action_required', 'stale', null]) {
  test(`reports check conclusion ${conclusion} without updating`, async () => {
    const result = await exercise({checks: [{status: 'completed', conclusion}]});
    assert.deepEqual(result.updates, []);
    assert.equal(result.warnings.length, 1);
  });
}

test('does not update with pending checks', async () => {
  assert.deepEqual((await exercise({checks: [{status: 'in_progress', conclusion: null}]})).updates, []);
});
for (const state of ['failure', 'error', 'pending']) {
  test(`does not update with ${state} commit status`, async () => {
    const result = await exercise({status: {state, statuses: [{state}]}});
    assert.deepEqual(result.updates, []);
    assert.equal(result.warnings.length, 1);
  });
}
test('accepts successful, neutral and skipped checks', async () => {
  const checks = ['success', 'neutral', 'skipped'].map(conclusion => ({status: 'completed', conclusion}));
  assert.equal((await exercise({checks})).updates.length, 1);
});

for (const apiError of [403, 409, 422, 500]) {
  test(`reports API ${apiError} without retrying or exposing error details`, async () => {
    const result = await exercise({apiError});
    assert.deepEqual(result.updates, []);
    assert.equal(result.failures.length, 1);
    assert.ok(result.failures[0].includes(String(apiError)));
    assert.ok(!result.failures[0].includes('private API detail'));
  });
}

test('read permission errors fail closed', async () => {
  await assert.rejects(exercise({readError: true}), /read denied/);
});

test('processes two PRs serially', async () => {
  const result = await exercise({pulls: [pull(), {...pull(), number: 2}]});
  assert.deepEqual(result.updates.map(update => update.pull_number), [1, 2]);
});

test('an API failure is reported without preventing later eligible PRs from being processed', async () => {
  const result = await exercise({pulls: [pull(), {...pull(), number: 2}], apiError: 422, failNumber: 1});
  assert.deepEqual(result.updates.map(update => update.pull_number), [2]);
  assert.equal(result.failures.length, 1);
});

test('workflow serializes repository runs without cancelling active work', () => {
  assert.match(workflow, /concurrency:\n  group: dependabot-branch-update-\$\{\{ github.repository \}\}\n  cancel-in-progress: false/);
  assert.match(workflow, /timeout-minutes: 10/);
  assert.match(workflow, /retries: 0/);
  assert.match(workflow, /github.ref == format\('refs\/heads\/\{0\}', github.event.repository.default_branch\)/);
  assert.match(workflow, /github.event.deleted == false/);
  assert.doesNotMatch(workflow, /actions\/checkout|pulls\.merge|createReview|exec\(/);
  for (const action of workflow.matchAll(/^\s+uses: (.+)/gm)) assert.match(action[1], /@[a-f0-9]{40} #/);
  assert.match(workflow, /repositories: \$\{\{ github.event.repository.name \}\}/);
});

const credentials = workflow.split('        run: |\n')[1].split('\n\n')[0]
  .split('\n').map(line => line.replace(/^ {10}/, '')).join('\n');
for (const missing of ['APP_ID', 'APP_KEY']) {
  test(`missing ${missing} fails before token creation`, () => {
    const result = spawnSync('bash', ['-c', credentials], {
      env: {APP_ID: 'placeholder', APP_KEY: 'placeholder', [missing]: ''}, encoding: 'utf8'
    });
    assert.equal(result.status, 1);
    assert.match(result.stdout, /::error::/);
    assert.ok(workflow.indexOf('name: Validate credentials') < workflow.indexOf('name: Create a repository-scoped App token'));
  });
}
test('credential validation accepts nonempty values without printing them', () => {
  const result = spawnSync('bash', ['-c', credentials], {
    env: {APP_ID: 'placeholder', APP_KEY: 'placeholder'}, encoding: 'utf8'
  });
  assert.equal(result.status, 0);
  assert.equal(result.stdout + result.stderr, '');
});
