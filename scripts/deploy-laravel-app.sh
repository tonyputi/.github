#!/bin/bash
set -eo pipefail

RELEASES_PATH=$APP_PATH/releases
STORAGE_PATH=$APP_PATH/storage
DEPLOYMENT_COMPLETED=false

# Teardown function to cleanup failed releases
teardown() {
  local exit_code=$?

  if [ "$DEPLOYMENT_COMPLETED" = false ] && [ $exit_code -ne 0 ]; then
    echo ""
    echo "❌ Deployment failed! Cleaning up release directory..."

    if [ -d "$RELEASE_PATH" ]; then
      echo "🧹 Removing failed release: $RELEASE_PATH"
      sudo rm -rf "$RELEASE_PATH"
      echo "✅ Cleanup completed"
    fi

    echo "💡 Previous release (if any) remains active at $APP_PATH/current"
    exit $exit_code
  fi
}

# Set trap to call teardown on error
trap teardown EXIT

echo "🚀 Deployment started for $APP_NAME to $RELEASE_PATH..."

echo "🔐 Setting ownership to $APP_USER:$APP_USER on $APP_PATH..."
sudo chown -R $APP_USER:$APP_USER $APP_PATH

echo "📂 Creating directories..."
sudo -u $APP_USER mkdir -p $RELEASES_PATH
sudo -u $APP_USER mkdir -p $STORAGE_PATH/{app,framework,logs}
sudo -u $APP_USER mkdir -p $STORAGE_PATH/framework/{cache,sessions,testing,views}
sudo -u $APP_USER touch $APP_PATH/database.sqlite

echo "🔗 Creating symbolic links..."
sudo -u $APP_USER ln -sfn $STORAGE_PATH $RELEASE_PATH/storage
sudo -u $APP_USER ln -sfn $APP_PATH/database.sqlite $RELEASE_PATH/database/database.sqlite

echo "🔄 Regenerating autoload with server paths..."
sudo -u $APP_USER composer -d $RELEASE_PATH dump-autoload -o -q

echo "🗄️ Running migrations..."
sudo -u $APP_USER php $RELEASE_PATH/artisan migrate --force --graceful --ansi -qn

echo "⚡ Running post-deploy commands..."
if jq -e '.scripts["post-deploy"]' "$RELEASE_PATH/composer.json" > /dev/null 2>&1; then
  sudo -u $APP_USER composer -d $RELEASE_PATH run post-deploy
fi

echo "🔐 Setting permissions on release..."
sudo find $RELEASE_PATH -type d -exec chmod 775 {} +
sudo find $RELEASE_PATH -type f -exec chmod 664 {} +
sudo chmod 400 $RELEASE_PATH/.env

echo "🔄 Switching to new release..."
sudo -u $APP_USER ln -sfn $RELEASE_PATH $APP_PATH/current
sudo -u $APP_USER ln -sfn $RELEASE_PATH/artisan $APP_PATH/artisan

echo "🔧 Managing Laravel services..."
if command -v manage-laravel-services &>/dev/null; then
  sudo manage-laravel-services "$APP_NAME" "$APP_PATH" "$RELEASE_PATH"
else
  echo "   manage-laravel-services not installed — skipping"
fi

echo "🧹 Cleaning up old releases..."
find $RELEASES_PATH -maxdepth 1 -type d ! -path $RELEASES_PATH | sort | head -n -$RELEASES_COUNT | xargs -r sudo rm -rf

echo "🎉 Deployment completed successfully!"
DEPLOYMENT_COMPLETED=true
