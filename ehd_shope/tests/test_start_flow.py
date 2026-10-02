import unittest

from ehd_shope.handlers.start import build_start_message, build_home_keyboard


class StartFlowTests(unittest.TestCase):
    def test_start_message_contains_english_and_amharic_text(self):
        text = build_start_message()
        self.assertIn("Welcome to our store!", text)
        self.assertIn("እንኳን ወደ ሱቃችን በደህና መጡ", text)

    def test_home_keyboard_has_bilingual_labels(self):
        keyboard = build_home_keyboard()
        labels = [button.text for row in keyboard.inline_keyboard for button in row]

        self.assertIn("🛍 Electronics / ኤሌክትሮኒክስ", labels)
        self.assertIn("🛒 My Cart / የእኔ ጋሪ", labels)
        self.assertIn("🌐 Language / ቋንቋ", labels)


if __name__ == "__main__":
    unittest.main()
