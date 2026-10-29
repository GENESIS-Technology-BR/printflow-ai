"""Runtime-independent tests for gateway upstream validation."""
import subprocess
import unittest


VALIDATOR = r"""
const { URL } = require('node:url');
const raw = process.argv[1];
const upstreamUrl = new URL(raw);
if (upstreamUrl.protocol !== "https:" || upstreamUrl.username || upstreamUrl.password || upstreamUrl.search || upstreamUrl.hash || upstreamUrl.pathname !== "/") {
  throw new Error("invalid upstream");
}
console.log(upstreamUrl.origin);
"""


class GatewayUpstreamTests(unittest.TestCase):
    def check(self, url):
        return subprocess.run(
            ["node", "-e", VALIDATOR, url],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def test_accepts_https_origin(self):
        result = self.check("https://api.example.org")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "https://api.example.org")

    def test_rejects_insecure_or_ambiguous_upstreams(self):
        for url in (
            "http://api.example.org",
            "https://user:password@api.example.org",
            "https://api.example.org/hidden",
            "https://api.example.org/?token=secret",
            "https://api.example.org/#fragment",
        ):
            with self.subTest(url=url):
                self.assertNotEqual(self.check(url).returncode, 0)


if __name__ == "__main__":
    unittest.main()
