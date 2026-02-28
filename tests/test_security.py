import unittest

from backend.security import hash_password, verify_password


class SecurityTests(unittest.TestCase):
    def test_password_hash_roundtrip(self) -> None:
        expected = "clave1234"
        digest, salt = hash_password(expected)
        self.assertTrue(verify_password(expected, digest, salt))
        self.assertFalse(verify_password("invalida", digest, salt))


if __name__ == "__main__":
    unittest.main()
