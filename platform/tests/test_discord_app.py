import unittest

from app.integrations.discord_app import DiscordApp


class DiscordAppTests(unittest.TestCase):
    def test_auth_header_normalizes_bot_prefix(self):
        app = DiscordApp("Bot example-token")
        self.assertEqual(app.headers["Authorization"], "Bot example-token")

    def test_empty_token_rejected(self):
        with self.assertRaises(ValueError):
            DiscordApp("")


if __name__ == "__main__":
    unittest.main()
