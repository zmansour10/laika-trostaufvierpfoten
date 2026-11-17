"""Offline integration checks. These never send reference texts to an AI service."""

from contextlib import ExitStack
from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import generate_letter as generator
import letter_storage
from letter_purposes import PURPOSE_GUIDES, purpose_guide
import studio


class SourceTests(unittest.TestCase):
    def test_actual_library_includes_every_populated_file_in_full(self):
        bundle = generator.load_sources()
        prompt = generator.build_prompt(bundle, generator.LetterBrief())
        payload = json.loads(prompt.split("\n", 1)[1])
        docs = payload["reference_library"]
        included = {doc["name"]: doc["text"] for doc in docs["association_information"] + docs["historical_letters"]}
        for folder in ("letters", "website_info"):
            for path in (generator.DATA_PATH / folder).rglob("*.txt"):
                text = path.read_text(encoding="utf-8-sig")
                name = path.relative_to(generator.DATA_PATH).as_posix()
                if text.strip():
                    self.assertEqual(included[name], text)
                else:
                    self.assertIn(name, bundle.empty_files)
        self.assertNotIn("MyKey", prompt)
        self.assertNotIn("GEMINI_API_KEY", prompt)

    def test_nested_unicode_bom_and_empty_sources(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "letters/nested").mkdir(parents=True)
            (root / "website_info").mkdir()
            (root / "letters/nested/example.TXT").write_text("\ufeffGrüße 🐾\n", encoding="utf-8")
            (root / "website_info/about.txt").write_text("LAIKA", encoding="utf-8")
            (root / "website_info/empty.txt").write_text(" \n", encoding="utf-8")
            bundle = generator.load_sources(root)
            self.assertEqual(bundle.letters[0].text, "Grüße 🐾\n")
            self.assertEqual(bundle.empty_files, ("website_info/empty.txt",))

    def test_missing_and_empty_folder_are_actionable(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(generator.GenerationError, "folder is missing"):
                generator.load_sources(Path(directory))
            (Path(directory) / "letters").mkdir()
            with self.assertRaisesRegex(generator.GenerationError, "non-empty"):
                generator.load_sources(Path(directory))

    def test_oversize_library_is_rejected_without_truncation(self):
        with patch.object(generator, "MAX_CONTEXT_CHARACTERS", 5):
            with self.assertRaisesRegex(generator.GenerationError, "silently omitted"):
                generator.load_sources()

    def test_prompt_preserves_custom_brief_and_date(self):
        brief = generator.LetterBrief(instructions="Neue Förderanfrage", letter_date=date(2027, 1, 2))
        prompt = generator.build_prompt(generator.load_sources(), brief)
        self.assertIn("Neue Förderanfrage", prompt)
        self.assertIn("2027-01-02", prompt)

    def test_each_purpose_sets_audience_and_writing_requirements(self):
        sources = generator.load_sources()
        for guide in PURPOSE_GUIDES:
            with self.subTest(purpose=guide.label):
                prompt = generator.build_prompt(sources, generator.LetterBrief(purpose=guide.label))
                payload = json.loads(prompt.split("\n", 1)[1])
                self.assertEqual(payload["writing_brief"]["recipient"], guide.recipient)
                self.assertEqual(payload["purpose_requirements"]["label"], guide.label)
                self.assertEqual(payload["purpose_requirements"]["intent"], guide.intent)
                self.assertIn(guide.label, payload["final_task"])
                self.assertEqual(len(payload["reference_library"]["historical_letters"]), len(sources.letters))

    def test_custom_audience_is_preserved_and_thanks_has_no_new_appeal(self):
        brief = generator.LetterBrief(purpose="Dankeschreiben", recipient="Ehrenamtliche im Verein")
        payload = json.loads(generator.build_prompt(generator.load_sources(), brief).split("\n", 1)[1])
        self.assertEqual(payload["writing_brief"]["recipient"], brief.recipient)
        self.assertEqual(payload["purpose_requirements"]["label"], "Dankesschreiben")
        self.assertIn("Do not make a new donation", payload["purpose_requirements"]["closing"])


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(generator, "_limiter", generator.RequestLimiter()))
        self.stack.enter_context(patch.object(generator, "provider_key", return_value="test-api-key"))
        self.sources = generator.load_sources()

    def test_all_requested_gemini_models_have_expected_limits(self):
        self.assertEqual([(m.id, m.rpm) for m in generator.MODELS[:3]], [
            ("gemini-3.5-flash-lite", 15), ("gemini-3.8-flash", 5), ("gemini-3.6-flash", 5)])

    def test_gemini_passes_full_prompt_and_disables_tools(self):
        with patch("google.genai.Client") as client_type:
            client = client_type.return_value.__enter__.return_value
            client.models.generate_content.return_value = SimpleNamespace(
                text="Ein neuer Brief.", candidates=[SimpleNamespace(finish_reason="STOP")])
            result = generator.generate_letter(generator.LetterBrief(), sources=self.sources)
            args = client.models.generate_content.call_args.kwargs
            self.assertEqual(args["model"], "gemini-3.5-flash-lite")
            self.assertEqual(args["config"].tools, [])
            self.assertIn(self.sources.letters[0].text.splitlines()[0], args["contents"])
            self.assertEqual(result.text, "Ein neuer Brief.")

    def test_both_openai_models_use_responses_without_tools_or_storage(self):
        for model_id in ("gpt-6-luna", "gpt-4o-mini"):
            with self.subTest(model=model_id), patch("openai.OpenAI") as client_type:
                client = client_type.return_value.__enter__.return_value
                client.responses.create.return_value = SimpleNamespace(status="completed", output_text="A new letter.")
                result = generator.generate_letter(generator.LetterBrief(), model_id, sources=self.sources)
                args = client.responses.create.call_args.kwargs
                self.assertEqual(args["model"], model_id)
                self.assertEqual(args["tools"], [])
                self.assertFalse(args["store"])
                self.assertEqual(result.provider, "OpenAI")

    def test_truncated_response_never_becomes_a_finished_letter(self):
        with patch("google.genai.Client") as client_type:
            client_type.return_value.__enter__.return_value.models.generate_content.return_value = SimpleNamespace(
                text="Partial", candidates=[SimpleNamespace(finish_reason="MAX_TOKENS")])
            with self.assertRaisesRegex(generator.GenerationError, "complete letter"):
                generator.generate_letter(generator.LetterBrief(), sources=self.sources)

    def test_empty_response_is_rejected(self):
        with patch.object(generator, "_gemini_generate", return_value="  "):
            with self.assertRaisesRegex(generator.GenerationError, "no letter"):
                generator.generate_letter(generator.LetterBrief(), sources=self.sources)

    def test_connection_error_never_exposes_credentials(self):
        with patch("google.genai.Client", side_effect=RuntimeError("url?key=SECRET")):
            with self.assertRaises(generator.GenerationError) as error:
                generator.generate_letter(generator.LetterBrief(), sources=self.sources)
            self.assertNotIn("SECRET", str(error.exception))

    def test_missing_key_does_not_call_provider(self):
        with patch.object(generator, "provider_key", return_value=None), patch.object(generator, "_openai_generate") as api:
            with self.assertRaisesRegex(generator.GenerationError, "OPENAI_API_KEY"):
                generator.generate_letter(generator.LetterBrief(), "gpt-6-luna")
            api.assert_not_called()

    def test_copied_judicial_subject_is_rejected_for_other_purposes(self):
        text = "Bitte um Zuweisung von Bußgeldauflagen für lokale tiergestützte Trauerbegleitung\nSehr geehrte Damen und Herren"
        for guide in PURPOSE_GUIDES[1:]:
            with self.subTest(purpose=guide.label), patch.object(generator, "_gemini_generate", return_value=text):
                with self.assertRaisesRegex(generator.GenerationError, "different purpose"):
                    generator.generate_letter(generator.LetterBrief(purpose=guide.label), sources=self.sources)
        with patch.object(generator, "_gemini_generate", return_value=text):
            result = generator.generate_letter(generator.LetterBrief(), sources=self.sources)
            self.assertEqual(result.text, text)

    def test_sliding_window_is_shared_per_model_and_key(self):
        limiter = generator.RequestLimiter()
        model = generator.MODELS[1]
        with patch.object(generator.time, "monotonic", return_value=100.0):
            for _ in range(5):
                limiter.reserve(model, "key-a")
            with self.assertRaisesRegex(generator.GenerationError, "60 seconds"):
                limiter.reserve(model, "key-a")
            limiter.reserve(model, "key-b")
            limiter.reserve(generator.MODELS[0], "key-a")
        with patch.object(generator.time, "monotonic", return_value=160.0):
            limiter.reserve(model, "key-a")


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.data_path = Path(self.stack.enter_context(TemporaryDirectory())) / "data"
        for folder in ("letters", "website_info"):
            shutil.copytree(generator.DATA_PATH / folder, self.data_path / folder)
        self.library = generator.load_sources(self.data_path)
        self.stack.enter_context(patch.object(letter_storage, "LETTERS_PATH", self.data_path / "letters"))
        self.stack.enter_context(patch.object(studio, "load_sources", side_effect=lambda: generator.load_sources(self.data_path)))
        self.config = {"MyKey": "access-key-ä"}
        self.stack.enter_context(patch("dotenv.dotenv_values", return_value=self.config))
        self.stack.enter_context(patch.object(studio, "provider_key", return_value="fake-provider-key"))
        self.generate = self.stack.enter_context(patch.object(studio, "generate_letter", return_value=generator.GeneratedLetter(
            "Betreff: Ein neuer Brief\n\nBitte um Zuweisung von Bußgeldauflagen für lokale Tiergestützte Trauerbegleitung\n"
            "\nSehr geehrte Damen und Herrn,en,\n\nDanke für Ihre Hilfe.",
            "gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite", "Gemini", 7, 1)))
        self.app = AppTest.from_file(str(generator.ROOT / "main.py"))

    def unlock(self):
        self.app.run()
        self.app.text_area(key="key_input").input("access-key-ä")
        self.app.button(key="validate_button").click().run()
        self.assertFalse(self.app.exception)

    def test_unauthenticated_user_cannot_load_references_or_generate(self):
        with patch.object(studio, "load_sources") as loader:
            self.app.run()
            self.app.text_area(key="key_input").input("wrong")
            self.app.button(key="validate_button").click().run()
            self.assertEqual(len(self.app.error), 1)
            self.assertEqual(len(self.app.selectbox), 0)
            loader.assert_not_called()
            self.generate.assert_not_called()

    def test_generate_edit_download_and_lock(self):
        self.unlock()
        self.app.text_area(key="brief_instructions").input("Bitte Soforthilfe hervorheben.")
        self.app.button(key="generate_button").click().run()
        self.assertFalse(self.app.exception)
        brief = self.generate.call_args.args[0]
        self.assertEqual(brief.instructions, "Bitte Soforthilfe hervorheben.")
        self.assertEqual(len(self.generate.call_args.kwargs["sources"].letters), len(self.library.letters))
        self.app.text_area(key="draft_text").input("My edited letter.").run()
        self.assertEqual(self.app.session_state["draft_text"], "My edited letter.")
        self.assertIn("My edited letter.", "\n".join(m.value for m in self.app.markdown))
        self.assertEqual(len(self.app.get("download_button")), 0)
        self.app.button(key="save_letter_button").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.get("download_button")), 1)
        self.app.button(key="lock_button").click().run()
        self.assertEqual(len(self.app.selectbox), 0)
        self.assertNotIn("draft_text", self.app.session_state)
        self.assertFalse(self.app.exception)

    def test_purpose_changes_update_the_default_audience_and_generated_brief(self):
        self.unlock()
        for guide in PURPOSE_GUIDES[1:]:
            with self.subTest(purpose=guide.label):
                self.app.selectbox(key="brief_purpose").select(guide.label).run()
                self.assertFalse(self.app.exception)
                self.assertEqual(self.app.text_input(key="brief_recipient").value, guide.recipient)
                self.app.button(key="generate_button").click().run()
                brief = self.generate.call_args.args[0]
                self.assertEqual(brief.purpose, guide.label)
                self.assertEqual(brief.recipient, guide.recipient)

    def test_switching_purpose_preserves_a_custom_recipient(self):
        self.unlock()
        self.app.text_input(key="brief_recipient").input("Frau Beispiel, Stiftung Test").run()
        self.app.selectbox(key="brief_purpose").select("Förderanfrage").run()
        self.assertEqual(self.app.text_input(key="brief_recipient").value, "Frau Beispiel, Stiftung Test")
        self.app.button(key="generate_button").click().run()
        self.assertEqual(self.generate.call_args.args[0].recipient, "Frau Beispiel, Stiftung Test")

    def test_settings_changes_label_the_existing_draft_until_regenerated(self):
        self.unlock()
        self.app.button(key="generate_button").click().run()
        previous = self.app.session_state["draft_text"]
        self.app.selectbox(key="brief_purpose").select("Spendenaufruf").run()
        self.assertEqual(self.generate.call_count, 1)
        self.assertEqual(self.app.session_state["draft_text"], previous)
        self.assertTrue(any("previous version" in item.value for item in self.app.info))
        self.app.button(key="generate_button").click().run()
        self.assertEqual(self.app.session_state["draft_metadata"]["purpose"], "Spendenaufruf")
        self.assertFalse(any("previous version" in item.value for item in self.app.info))

    def test_saving_uses_latest_edits_and_future_prompts_include_them(self):
        self.unlock()
        self.app.button(key="generate_button").click().run()
        original_count = len(generator.load_sources(self.data_path).letters)
        edited = "Betreff: Überarbeiteter Brief\n\nGrüße von LAIKA 🐾\n"
        # Click while the textarea has a pending edit: preparation must commit it first.
        self.app.text_area(key="draft_text").input(edited)
        self.app.button(key="save_letter_button").click().run()
        self.assertFalse(self.app.exception)
        prepared = self.app.session_state["prepared_download"]
        self.assertEqual(prepared["text"], edited)
        saved_path = self.data_path / "letters" / Path(prepared["path"]).name
        self.assertEqual(saved_path.read_bytes(), edited.encode("utf-8"))
        self.assertEqual(len(generator.load_sources(self.data_path).letters), original_count + 1)
        self.app.button(key="save_letter_button").click().run()
        self.assertEqual(len(generator.load_sources(self.data_path).letters), original_count + 1)
        self.app.text_area(key="draft_text").input("An updated version.").run()
        self.assertNotIn("prepared_download", self.app.session_state)
        self.assertEqual(len(self.app.get("download_button")), 0)
        self.app.button(key="save_letter_button").click().run()
        self.assertEqual(saved_path.read_bytes(), edited.encode("utf-8"))
        self.assertEqual(len(generator.load_sources(self.data_path).letters), original_count + 2)
        self.app.button(key="generate_button").click().run()
        included = self.generate.call_args.kwargs["sources"].letters
        self.assertTrue(any(doc.text == edited for doc in included))
        self.assertTrue(any(doc.text == "An updated version." for doc in included))
        self.assertNotIn("prepared_download", self.app.session_state)

    def test_save_failure_preserves_draft_without_offering_download(self):
        self.unlock()
        self.app.button(key="generate_button").click().run()
        before = self.app.session_state["draft_text"]
        with patch.object(letter_storage.os, "link", side_effect=OSError("Disk full")):
            self.app.button(key="save_letter_button").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["draft_text"], before)
        self.assertEqual(len(self.app.error), 1)
        self.assertEqual(len(self.app.get("download_button")), 0)
        self.assertEqual(len(generator.load_sources(self.data_path).letters), len(self.library.letters))

    def test_rotating_key_revokes_access_and_removes_draft(self):
        self.unlock()
        self.app.button(key="generate_button").click().run()
        self.config["MyKey"] = "rotated"
        self.app.run()
        self.assertEqual(len(self.app.selectbox), 0)
        self.assertNotIn("draft_text", self.app.session_state)
        self.assertNotIn("auth_proof", self.app.session_state)

    def test_generation_failure_preserves_previous_draft(self):
        self.unlock()
        self.app.button(key="generate_button").click().run()
        before = self.app.session_state["draft_text"]
        self.generate.side_effect = generator.GenerationError("Quota reached. Try again later.")
        self.app.button(key="generate_button").click().run()
        self.assertEqual(self.app.session_state["draft_text"], before)
        self.assertEqual(len(self.app.error), 1)
        self.assertFalse(self.app.exception)

    def test_missing_provider_key_disables_generation(self):
        with patch.object(studio, "provider_key", return_value=None):
            self.unlock()
            self.assertTrue(self.app.button(key="generate_button").disabled)
            self.app.selectbox(key="brief_model").select("gpt-6-luna").run()
            self.assertTrue(self.app.button(key="generate_button").disabled)
            self.generate.assert_not_called()

    def test_empty_and_case_sensitive_access_key(self):
        self.app.run()
        self.app.button(key="validate_button").click().run()
        self.assertEqual(len(self.app.warning), 1)
        for value in ("ACCESS-KEY-Ä", "access-key-ä "):
            self.app.text_area(key="key_input").input(value)
            self.app.button(key="validate_button").click().run()
            self.assertEqual(len(self.app.error), 1)
            self.assertEqual(len(self.app.selectbox), 0)


if __name__ == "__main__":
    unittest.main()
