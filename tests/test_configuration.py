from contextlib import ExitStack
import unittest
from unittest.mock import MagicMock, patch

import configuration
from generate_letter import provider_key


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.secrets = {}
        self.local_values = {}
        self.stack.enter_context(patch.object(configuration.st, "secrets", self.secrets))
        self.stack.enter_context(patch.dict(configuration.os.environ, {}, clear=True))
        self.stack.enter_context(patch.object(configuration, "dotenv_values", return_value=self.local_values))

    def test_cloud_secrets_take_precedence_over_environment_and_env_file(self):
        self.secrets["MyKey"] = "cloud-key"
        configuration.os.environ["MyKey"] = "environment-key"
        self.local_values["MyKey"] = "local-key"
        self.assertEqual(configuration.read_setting("MyKey"), "cloud-key")

    def test_environment_and_local_fallback_without_secrets_file(self):
        unavailable = MagicMock()
        unavailable.__getitem__.side_effect = FileNotFoundError("No secrets.toml")
        with patch.object(configuration.st, "secrets", unavailable):
            self.local_values["MyKey"] = "local-key"
            self.assertEqual(configuration.read_setting("MyKey"), "local-key")
            configuration.os.environ["MyKey"] = "environment-key"
            self.assertEqual(configuration.read_setting("MyKey"), "environment-key")

    def test_unconfigured_or_non_string_values_do_not_enable_access(self):
        self.assertIsNone(configuration.read_setting("MyKey"))
        for value in ("", 123, False, {"value": "nested"}):
            self.secrets["MyKey"] = value
            self.assertIsNone(configuration.read_setting("MyKey"))

    def test_access_key_preserves_exact_whitespace_and_unicode(self):
        self.secrets["MyKey"] = "  Grüße 🐾\n"
        self.assertEqual(configuration.read_setting("MyKey"), "  Grüße 🐾\n")

    def test_ai_providers_use_cloud_secrets_and_strip_api_key_whitespace(self):
        self.secrets.update(GEMINI_API_KEY=" cloud-gemini ", OPENAI_API_KEY=" cloud-openai\n")
        self.assertEqual(provider_key("Gemini"), "cloud-gemini")
        self.assertEqual(provider_key("OpenAI"), "cloud-openai")

    def test_google_alias_in_cloud_wins_over_local_gemini_key(self):
        self.secrets["GOOGLE_API_KEY"] = "cloud-google"
        self.local_values["GEMINI_API_KEY"] = "local-gemini"
        self.assertEqual(provider_key("Gemini"), "cloud-google")
