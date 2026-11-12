#!/bin/bash
set -euo pipefail

# Generate .env using the Laravel project's installed phpdotenv parser.
# Usage: ENVIRONMENT=production ENV_SECRETS='{}' ./scripts/generate-env.sh build

BUILD_PATH=${1:-build}
ENVIRONMENT=${ENVIRONMENT:-}

if [ ! -d "$BUILD_PATH" ]; then
  echo "Error: Build directory not found"
  exit 1
fi

if [ -n "$ENVIRONMENT" ] && [ -f "$BUILD_PATH/.env.$ENVIRONMENT" ]; then
  ENV_TEMPLATE="$BUILD_PATH/.env.$ENVIRONMENT"
elif [ "$ENVIRONMENT" = production ]; then
  echo "Error: Production requires .env.production; refusing to use .env.example"
  exit 1
elif [ -f "$BUILD_PATH/.env.example" ]; then
  ENV_TEMPLATE="$BUILD_PATH/.env.example"
else
  echo "Error: No environment template found"
  exit 1
fi

export BUILD_PATH ENV_TEMPLATE ENVIRONMENT
php <<'PHP'
<?php
function fail(string $message): void
{
    file_put_contents('php://stderr', "Error: {$message}\n");
    exit(1);
}

try {
    $path = getenv('BUILD_PATH');
    require $path.'/vendor/autoload.php';
    $contents = file_get_contents(getenv('ENV_TEMPLATE'));
    Dotenv\Dotenv::parse($contents);
    $production = getenv('ENVIRONMENT') === 'production';
    $secrets = [];

    foreach (['ENV_OVERRIDES', 'ENV_SECRETS'] as $source) {
        $json = getenv($source);
        $input = json_decode($json === false || $json === '' ? '{}' : $json, false, 512, JSON_THROW_ON_ERROR);
        if (!$input instanceof stdClass) {
            fail("{$source} must be a JSON object");
        }

        foreach ($input as $key => $value) {
            if (!preg_match('/^[A-Za-z_][A-Za-z0-9_]*$/D', $key) || !is_scalar($value)) {
                fail("{$source} contains an invalid variable name or value type");
            }
            $value = is_bool($value) ? ($value ? 'true' : 'false') : (string) $value;
            if (strpos($value, "\0") !== false) {
                fail("{$source} contains a null byte");
            }
            if ($source === 'ENV_SECRETS') {
                if ($production && trim($value) === '') {
                    fail("Required production secret {$key} is empty");
                }
                $secrets[$key] = $value;
            }

            $quoted = '"'.str_replace(
                ["\\", "\n", "\r", "\t", '"', '$'],
                ["\\\\", '\n', '\r', '\t', '\"', '\$'],
                $value
            ).'"';
            $contents = preg_replace_callback(
                '/^'.preg_quote($key, '/').'\h*=.*$/m',
                static fn () => $key.'='.$quoted,
                $contents,
                -1,
                $count
            );
            if ($count !== 1) {
                fail("Template must define {$key} exactly once");
            }
        }
    }

    $values = Dotenv\Dotenv::parse($contents);
    if ($production && (
        ($values['APP_ENV'] ?? null) !== 'production'
        || !in_array(strtolower($values['APP_DEBUG'] ?? ''), ['false', '(false)', '0'], true)
        || trim($values['APP_KEY'] ?? '') === ''
        || in_array(strtolower($values['APP_KEY']), ['null', '(null)', 'empty', '(empty)', 'true', '(true)', 'false', '(false)'], true)
    )) {
        fail('Production requires APP_ENV=production, APP_DEBUG=false and a non-empty APP_KEY');
    }
    foreach ($secrets as $key => $value) {
        if (($values[$key] ?? null) !== $value) {
            fail("Secret {$key} did not survive dotenv parsing unchanged");
        }
    }

    umask(0077);
    if (file_put_contents($path.'/.env', $contents, LOCK_EX) === false || !chmod($path.'/.env', 0600)) {
        fail('Cannot write the generated environment');
    }
} catch (Throwable $error) {
    // Parser exceptions can contain secret values; never print their details.
    fail('Invalid template or JSON input, or missing project autoloader');
}
echo "Environment generated and validated successfully\n";
PHP
