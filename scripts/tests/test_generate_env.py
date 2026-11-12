"""Run with DOTENV_AUTOLOAD=/path/to/laravel/vendor/autoload.php python3 -m unittest discover -s scripts/tests."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "generate-env.sh"
AUTOLOAD = Path(os.environ["DOTENV_AUTOLOAD"]).resolve()
TEMPLATE = "APP_ENV=production\nAPP_DEBUG=false\nAPP_KEY=\nPASSWORD=\nAPP_NAME=Example\nREF=\"${APP_NAME}\"\n"


class GenerateEnvTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.build = Path(self.temp.name)
        (self.build / "vendor").mkdir()
        (self.build / "vendor/autoload.php").symlink_to(AUTOLOAD)
        self.template = self.build / ".env.production"
        self.template.write_text(TEMPLATE)

    def generate(self, secrets=None, overrides=None, environment="production"):
        return subprocess.run(
            ["bash", str(SCRIPT), str(self.build)],
            env={
                **os.environ,
                "ENVIRONMENT": environment,
                "ENV_SECRETS": json.dumps({"APP_KEY": "test-application-key"} if secrets is None else secrets),
                "ENV_OVERRIDES": json.dumps({} if overrides is None else overrides),
            },
            capture_output=True,
            text=True,
            check=False,
        )

    def parsed(self):
        result = subprocess.run(
            ["php", "-d", "error_reporting=8191", "-r",
             'require $argv[1]; echo json_encode(Dotenv\\Dotenv::parse(file_get_contents($argv[2])));',
             str(AUTOLOAD), str(self.build / ".env")],
            capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)

    def test_valid_production_and_interpolation(self):
        result = self.generate()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual("test-application-key", self.parsed()["APP_KEY"])
        self.assertEqual("Example", self.parsed()["REF"])
        self.assertEqual(0o600, (self.build / ".env").stat().st_mode & 0o777)

    def test_production_does_not_fall_back_to_example(self):
        self.template.rename(self.build / ".env.example")
        self.assertNotEqual(0, self.generate().returncode)
        self.assertFalse((self.build / ".env").exists())

    def test_non_production_can_use_example(self):
        self.template.rename(self.build / ".env.example")
        self.assertEqual(0, self.generate(environment="testing").returncode)

    def test_non_production_can_use_specific_template(self):
        self.template.rename(self.build / ".env.stage")
        self.assertEqual(0, self.generate(environment="stage").returncode)

    def test_missing_key(self):
        self.assertNotEqual(0, self.generate(secrets={}).returncode)

    def test_empty_secret(self):
        for value in ["", "  ", None]:
            with self.subTest(value=value):
                self.assertNotEqual(0, self.generate(secrets={"APP_KEY": value}).returncode)

    def test_unknown_secret_is_not_silently_ignored(self):
        self.assertNotEqual(0, self.generate(secrets={"APP_KEY": "test-key", "TYPO": "value"}).returncode)

    def test_unsafe_production_settings(self):
        for overrides in [{"APP_ENV": "local"}, {"APP_DEBUG": "true"}, {"APP_DEBUG": ""}]:
            with self.subTest(overrides=overrides):
                self.assertNotEqual(0, self.generate(overrides=overrides).returncode)

    def test_reserved_empty_or_null_key(self):
        for key in ["null", "(null)", "empty", "(empty)", "false", "(false)"]:
            with self.subTest(key=key):
                self.assertNotEqual(0, self.generate(secrets={"APP_KEY": key}).returncode)

    def test_round_trip_special_characters_without_logging_them(self):
        password = 'test-"quotes"-\\slashes-$dollar-${APP_NAME}-=equals-\ttab-\nnewline-\rcarriage-#hash-è'
        result = self.generate(secrets={"APP_KEY": "test-key", "PASSWORD": password})
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(password, self.parsed()["PASSWORD"])
        self.assertNotIn(password, result.stdout + result.stderr)

    def test_secrets_override_regular_overrides(self):
        result = self.generate(overrides={"APP_KEY": "overridden-key"})
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual("test-application-key", self.parsed()["APP_KEY"])

    def test_multiple_secrets_and_unused_optional_values(self):
        self.template.write_text(TEMPLATE + "AWS_ACCESS_KEY_ID=\nAWS_SECRET_ACCESS_KEY=\n")
        result = self.generate(secrets={
            "APP_KEY": "test-key", "AWS_ACCESS_KEY_ID": "test-id", "AWS_SECRET_ACCESS_KEY": "test-secret",
        })
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual("test-secret", self.parsed()["AWS_SECRET_ACCESS_KEY"])
        self.assertEqual("", self.parsed()["PASSWORD"])

    def test_malformed_json_does_not_expose_values(self):
        secret = "test-sensitive-json"
        result = subprocess.run(
            ["bash", str(SCRIPT), str(self.build)],
            env={**os.environ, "ENVIRONMENT": "production", "ENV_SECRETS": '{"APP_KEY": "' + secret},
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn(secret, result.stdout + result.stderr)

    def test_invalid_json_and_value_types(self):
        for value in [[], "invalid", {"APP_KEY": ["invalid"]}]:
            with self.subTest(value=value):
                self.assertNotEqual(0, self.generate(secrets=value).returncode)

    def test_invalid_template_does_not_expose_values(self):
        secret = 'test-sensitive-value'
        self.template.write_text(TEMPLATE + f'BROKEN="{secret}" unexpected\n')
        result = self.generate()
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn(secret, result.stdout + result.stderr)

    def test_duplicate_secret_key(self):
        self.template.write_text(TEMPLATE + "APP_KEY=\n")
        self.assertNotEqual(0, self.generate().returncode)

    def test_invalid_input_preserves_existing_env(self):
        existing = self.build / ".env"
        existing.write_text("existing environment\n")
        self.assertNotEqual(0, self.generate(overrides={"APP_DEBUG": "true"}).returncode)
        self.assertEqual("existing environment\n", existing.read_text())


if __name__ == "__main__":
    unittest.main()
