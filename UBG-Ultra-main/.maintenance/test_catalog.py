"""Validate every catalog launch URL through the actual HTTP handler."""
import concurrent.futures
import json
import threading
import unittest
import urllib.request
import play


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = play.HubServer(('127.0.0.1', 0), play.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_entire_catalog(self):
        with urllib.request.urlopen(self.base + '/api/games') as response:
            data = json.load(response)
        self.assertGreater(data['count'], 1000)
        self.assertEqual(data['count'], len({g['name'].casefold() for g in data['games']}))
        def check(game):
            request = urllib.request.Request(self.base + '/' + game['link'].lstrip('/'), method='HEAD')
            with urllib.request.urlopen(request, timeout=15) as response:
                self.assertEqual(response.status, 200, game['name'])
                self.assertIn('text/html', response.headers['Content-Type'], game['name'])
                self.assertGreater(int(response.headers['Content-Length']), 0, game['name'])
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(check, data['games']))
        print('Validated', data['count'], 'nonempty HTML launch paths')

    def test_library_traversal(self):
        for path in ['/library/../play.py', '/library/%2e%2e/play.py', '/library/%2e%2e%5cplay.py']:
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(self.base + path)
            self.assertEqual(error.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
