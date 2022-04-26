import logging
import pprint


log = logging.getLogger(__name__)


class Config:
    dry_run = True

    deltek_api_url = None
    deltek_app_url = None

    deltek_username = None
    deltek_password = None
    deltek_database = None

    deltek_client_id = None
    deltek_client_secret = None

    bamboo_subdomain = None
    bamboo_api_key = None

    pipedrive_api_url = None
    pipedrive_api_token = None

    pipedrive_filter_id_sync_deals = -1
    pipedrive_filter_id_sync_persons = -1
    pipedrive_filter_id_sync_organizations = -1

    # deal fields
    pipedrive_field_id_sync_with_deltek = None
    pipedrive_field_id_project_number_id = None
    pipedrive_field_id_project_number_master_code = None
    pipedrive_field_id_project_number_phase = None

    pipedrive_field_id_short_description = None
    pipedrive_field_id_total_project_budget = None
    pipedrive_field_id_commercial_deal_details = None
    pipedrive_field_id_lead_studio = None
    pipedrive_field_id_support_studio = None
    pipedrive_field_id_origin = None
    pipedrive_field_id_estimated_project_start = None
    pipedrive_field_id_estimated_project_end = None
    pipedrive_field_id_team_drive_link = None
    pipedrive_field_id_deltek_link = None
    pipedrive_field_id_project_type = None
    pipedrive_field_id_override_deltek_project_number = None
    pipedrive_field_id_override_deltek_promo_project_number = None
    pipedrive_field_id_equity_project = None
    pipedrive_field_id_deltek_sync_status = None
    pipedrive_field_id_project_location = None

    # people field
    pipedrive_field_id_job_title = None

    force_organization = None
    force_deal_stage = False
    force_deal_stage_value = None

    sqlalchemy_url = None

    smtp_host = None
    smtp_sender = None
    smtp_username = None
    smtp_password = None

    admin_email = None
    alert_email = None

    won_email = None
    lost_email = None
    dormant_email = None
    new_project_email = None

    api_dev_url = None
    api_dev_username = None
    api_dev_password = None

    api_prod_url = None
    api_prod_username = None
    api_prod_password = None

    @staticmethod
    def from_file(filename):
        with open(filename, 'r') as f:
            return Config.from_string(f.read())

    @staticmethod
    def from_string(string):
        config = Config()
        for line in string.split('\n'):
            line = line.strip()
            if not line:
                continue

            if line.startswith("#"):
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            if key not in dir(config) or key.startswith("_"):
                log.warn(
                    "Parameter {} is invalid and will be ignored.".format(key))
                continue

            if isinstance(getattr(Config(), key), bool):
                value = value == 'true'
            elif isinstance(getattr(Config(), key), int):
                value = int(value)

            setattr(config, key, value)
        return config

    def to_dict(self):
        d = {}
        for member in dir(self):
            if member.startswith('_'):
                continue

            obj_member = getattr(self, member)
            if callable(obj_member):
                continue

            d[member] = obj_member
        return d

    def __str__(self):
        return pprint.pformat(self.to_dict())
