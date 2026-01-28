/**
 * @type {import('semantic-release').GlobalConfig}
 */
module.exports = {
    branches: ['main'],
    plugins: [
        '@semantic-release/commit-analyzer',
        '@semantic-release/release-notes-generator',
        [
            '@semantic-release/exec',
            {
                publishCmd: 'echo "release_published=true" >> $GITHUB_OUTPUT',
                successCmd: [
                    './scripts/create-semantic-release-tags.sh "${nextRelease.version}" "${branch.name}"',
                    'echo "release_version=${nextRelease.version}" >> $GITHUB_OUTPUT'
                ].join(' && ')
            },
        ],
        '@semantic-release/github',
    ],
};