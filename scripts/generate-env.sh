#!/bin/bash
set -eo pipefail

# Script to generate .env file from .env.example with overrides and secrets
# Usage: ENV_OVERRIDES='{}' ENV_SECRETS='{}' ./.github/scripts/generate-env.sh

BUILD_PATH=${1:-build}

if [ ! -d "$BUILD_PATH" ]; then
  echo "Error: $BUILD_PATH directory not found"
  exit 1
fi

ENV_TEMPLATE=""

# Check for environment-specific template first (e.g., .env.stage, .env.production)
if [ -n "$ENVIRONMENT" ] && [ -f "$BUILD_PATH/.env.$ENVIRONMENT" ]; then
  ENV_TEMPLATE="$BUILD_PATH/.env.$ENVIRONMENT"
  echo "Using environment-specific template: .env.$ENVIRONMENT"
elif [ -f "$BUILD_PATH/.env.example" ]; then
  ENV_TEMPLATE="$BUILD_PATH/.env.example"
  echo "Using default template: .env.example"
else
  echo "Error: No .env template found (.env.$ENVIRONMENT or .env.example)"
  exit 1
fi

cp "$ENV_TEMPLATE" "$BUILD_PATH/.env"

# Function to safely update .env value (handles special characters)
update_env_value() {
  local key="$1"
  local value="$2"
  local file="$3"

  if grep -q "^${key}=" "$file"; then
    # Use awk for safe substitution (handles special chars in value)
    awk -v k="$key" -v v="$value" 'BEGIN{FS=OFS="="} $1==k{$2="\""v"\""; print; next} {print}' "$file" > "$file.tmp"
    mv "$file.tmp" "$file"
  fi
}

# Apply overrides from JSON input
if [ -n "$ENV_OVERRIDES" ] && [ "$ENV_OVERRIDES" != "{}" ]; then
  echo "$ENV_OVERRIDES" | jq -r 'to_entries[] | "\(.key)\t\(.value)"' | while IFS=$'\t' read -r key value; do
    update_env_value "$key" "$value" "$BUILD_PATH/.env"
  done
fi

# Apply secrets from JSON input
if [ -n "$ENV_SECRETS" ] && [ "$ENV_SECRETS" != "{}" ]; then
  echo "$ENV_SECRETS" | jq -r 'to_entries[] | "\(.key)\t\(.value)"' | while IFS=$'\t' read -r key value; do
    update_env_value "$key" "$value" "$BUILD_PATH/.env"
  done
fi

echo "✅ .env file generated successfully"
