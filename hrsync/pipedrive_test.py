from hrsync.config import Config
from hrsync.sync_pipedrive import SyncPipedrive
import sys


def test_send_to_api(config):
    params = {}
    SyncPipedrive._api_post_deal_change(
        config.api_dev_url,
        config.api_dev_username,
        config.api_dev_password,
        params)


def test(config):
    test_send_to_api(config)


if __name__ == "__main__":
    config_file = sys.argv[1]
    config = Config.from_file(config_file)
    test(config)
