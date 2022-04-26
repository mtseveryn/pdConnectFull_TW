from hrsync.config import Config

import os
import tempfile
import unittest


class ConfigTest(unittest.TestCase):
    url = "http://localhost/api"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_from_string(self):
        config = Config.from_string("deltek_api_url={}".format(self.url))

        assert config.deltek_api_url == self.url

    def test_from_file(self):
        tmp = tempfile.mktemp()
        with open(tmp, 'w') as f:
            f.write("deltek_api_url={}".format(self.url))
        config = Config.from_file(tmp)

        assert config.deltek_api_url == self.url
        os.unlink(tmp)

    def test_strip(self):
        config = Config.from_string("dry_run = true ")
        assert config.dry_run is True
