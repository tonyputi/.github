
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
                successCmd: `
                    VERSION="\${nextRelease.version}"
                    BRANCH="\${branch.name}"
                    
                    # Parse version components using sed (avoid template conflicts)
                    MAJOR=$(echo "$VERSION" | sed 's/\\([0-9]\\+\\)\\..*$/\\1/')
                    MINOR=$(echo "$VERSION" | sed 's/^[0-9]\\+\\.\\([0-9]\\+\\)\\..*$/\\1/')
                    
                    # Stable release: create v1, v1.2
                    MAJOR_TAG="v$MAJOR"
                    MINOR_TAG="v$MAJOR.$MINOR"
                    
                    echo "Creating stable tags for version $VERSION on branch $BRANCH"
                    git tag -f "$MAJOR_TAG" -m "Release $MAJOR_TAG (latest: v$VERSION)"
                    git tag -f "$MINOR_TAG" -m "Release $MINOR_TAG (latest: v$VERSION)"
                    git push origin "$MAJOR_TAG" "$MINOR_TAG" --force
                    
                    echo "✓ Created stable tags: $MAJOR_TAG, $MINOR_TAG"

                    echo "release_version=$VERSION" >> $GITHUB_OUTPUT
                `
            },
        ],
        '@semantic-release/github',
    ]
};