#!/bin/sh

# Script to create semantic release tags
# Usage: create-semantic-release-tags.sh <version> <branch>

set -e

VERSION="$1"
BRANCH="$2"

if [ -z "$VERSION" ] || [ -z "$BRANCH" ]; then
    echo "Usage: $0 <version> <branch>"
    exit 1
fi

# Validate semantic version format (X.Y.Z or X.Y.Z-prerelease)
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
    echo "::error::Invalid version format: $VERSION (expected X.Y.Z or X.Y.Z-prerelease)"
    exit 1
fi

echo "Processing version: $VERSION on branch: $BRANCH"

# Parse version components using sed
MAJOR=$(echo "$VERSION" | sed 's/\([0-9]\+\)\..*$/\1/')
MINOR=$(echo "$VERSION" | sed 's/^[0-9]\+\.\([0-9]\+\)\..*$/\1/')

echo "Parsed - Major: $MAJOR, Minor: $MINOR"

# Determine if this is a prerelease based on version format
if [ "${VERSION#*-}" != "$VERSION" ]; then
    SUFFIX=$(echo "$VERSION" | sed 's/^[0-9]\+\.[0-9]\+\.[0-9]\+-\(.*\)$/\1/')
    MAJOR_TAG="v$MAJOR-$SUFFIX"
    MINOR_TAG="v$MAJOR.$MINOR-$SUFFIX"

    echo "Creating prerelease tags for version $VERSION on branch $BRANCH"
    echo "Tags to create: $MAJOR_TAG, $MINOR_TAG"

    git tag -f "$MAJOR_TAG" -m "Release $MAJOR_TAG (latest: v$VERSION)"
    git tag -f "$MINOR_TAG" -m "Release $MINOR_TAG (latest: v$VERSION)"
    git push origin "$MAJOR_TAG" "$MINOR_TAG" --force

    echo "✓ Created prerelease tags: $MAJOR_TAG, $MINOR_TAG"
else
    MAJOR_TAG="v$MAJOR"
    MINOR_TAG="v$MAJOR.$MINOR"

    echo "Creating stable tags for version $VERSION on branch $BRANCH"
    echo "Tags to create: $MAJOR_TAG, $MINOR_TAG"

    git tag -f "$MAJOR_TAG" -m "Release $MAJOR_TAG (latest: v$VERSION)"
    git tag -f "$MINOR_TAG" -m "Release $MINOR_TAG (latest: v$VERSION)"
    git push origin "$MAJOR_TAG" "$MINOR_TAG" --force

    echo "✓ Created stable tags: $MAJOR_TAG, $MINOR_TAG"
fi

echo "Script completed successfully"
