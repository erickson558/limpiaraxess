import unittest

from backend.i18n import get_language, set_language, t


class I18nTests(unittest.TestCase):
    def setUp(self) -> None:
        # Restore default language before each test
        set_language("es")

    def tearDown(self) -> None:
        # Restore default language after each test
        set_language("es")

    def test_default_language_is_spanish(self) -> None:
        self.assertEqual(get_language(), "es")

    def test_set_language_switches_to_english(self) -> None:
        set_language("en")
        self.assertEqual(get_language(), "en")

    def test_set_language_ignores_unknown_codes(self) -> None:
        set_language("fr")
        # Should remain "es" (unchanged)
        self.assertEqual(get_language(), "es")

    def test_translation_returns_spanish_by_default(self) -> None:
        set_language("es")
        self.assertEqual(t("btn_exit"), "Salir")

    def test_translation_returns_english_when_set(self) -> None:
        set_language("en")
        self.assertEqual(t("btn_exit"), "Exit")

    def test_translation_supports_format_kwargs(self) -> None:
        set_language("es")
        result = t("autoclose_active", sec=30)
        self.assertIn("30", result)
        self.assertIn("s", result)

    def test_translation_returns_key_for_unknown_keys(self) -> None:
        result = t("nonexistent_key_xyz")
        self.assertEqual(result, "nonexistent_key_xyz")

    def test_donate_url_in_btn_donate(self) -> None:
        # btn_donate must exist in both languages
        set_language("es")
        es_text = t("btn_donate")
        set_language("en")
        en_text = t("btn_donate")
        self.assertIn("cerveza", es_text)
        self.assertIn("beer", en_text)


if __name__ == "__main__":
    unittest.main()
