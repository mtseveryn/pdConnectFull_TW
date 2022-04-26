from hrsync.pipedrive_custom_fields import PipedriveCustomFields

import unittest


class PipedriveCustomFieldsTest(unittest.TestCase):
    def test_options_by_id(self):
        true = True
        false = False
        custom_fields = [{
            "active_flag": true,
            "add_time": "2020-01-08 06:58:50",
            "add_visible_flag": false,
            "bulk_edit_allowed": true,
            "details_visible_flag": true,
            "edit_flag": true,
            "field_type": "enum",
            "filtering_allowed": true,
            "id": 12504,
            "important_flag": true,
            "index_visible_flag": true,
            "key": "9fea1b21cbe975bf99cbb57986c22ebc1cb36767",
            "last_updated_by_user_id": 8893244,
            "mandatory_flag": false,
            "name": "Sync with Deltek",
            "options": [
                {
                    "id": 70,
                    "label": "Yes"
                }
            ],
            "order_nr": 47,
            "searchable_flag": false,
            "sortable_flag": true,
            "update_time": "2020-01-08 06:58:50"
        }]

        options = PipedriveCustomFields.options_by_id(custom_fields)
        key = "9fea1b21cbe975bf99cbb57986c22ebc1cb36767"
        assert options[key][70] == "Yes"
