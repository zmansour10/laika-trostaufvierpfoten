from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from letter_storage import LetterSaveError, save_letter


class LetterStorageTests(unittest.TestCase):
    def test_exact_content_duplicates_and_new_versions(self):
        with TemporaryDirectory() as directory:
            letters = Path(directory) / "letters"
            text = "Grüße 🐾\n\nReviewed letter.  \n"
            first = save_letter(text, letters)
            self.assertEqual(first.read_bytes(), text.encode("utf-8"))
            self.assertEqual(save_letter(text, letters), first)
            second = save_letter(text + "Edited.", letters)
            self.assertNotEqual(second, first)
            self.assertEqual(first.read_bytes(), text.encode("utf-8"))
            self.assertEqual(len(list(letters.glob("*.txt"))), 2)
            self.assertEqual(len(list(letters.glob("*.tmp"))), 0)

    def test_failed_publish_leaves_no_partial_reference(self):
        with TemporaryDirectory() as directory:
            letters = Path(directory)
            with patch("letter_storage.os.link", side_effect=OSError("Disk full")):
                with self.assertRaises(LetterSaveError):
                    save_letter("A reviewed letter.", letters)
            self.assertEqual(list(letters.iterdir()), [])

    def test_blank_letter_does_not_create_a_file(self):
        with TemporaryDirectory() as directory:
            letters = Path(directory) / "letters"
            with self.assertRaises(LetterSaveError):
                save_letter(" \n\t", letters)
            self.assertFalse(letters.exists())
