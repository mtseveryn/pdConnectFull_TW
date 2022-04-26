from hrsync.sync_pipedrive import SyncPipedrive

import datetime
import os
import tempfile
import unittest


class ConfigTest(unittest.TestCase):
    url = "http://api-web.local/"
    username = "admin"
    password = "admin"

    def setUp(self):
        pass

    def tearDown(self):
        pass


    def test_api_post_deal_change(self):
        timestamp = datetime.datetime.utcnow().isoformat()

        data = dict(
            timestamp=timestamp,
            deal_id=2,
            event_name='updated',
            deal_data="{}")

        SyncPipedrive._api_post_deal_change(
            self.url,
            self.username,
            self.password,
            data)


