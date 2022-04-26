from PyBambooHR import PyBambooHR

import datetime
import json


class BambooCache:
    def __init__(self, employees_filename):
        self.employees_filename = employees_filename

    def get_employees(self):
        with open(self.employees_filename, 'r') as f:
            return json.load(f)


class BambooApi:
    def __init__(self, config):
        self.config = config
        self._bamboo = None

    @property
    def bamboo(self):
        if self._bamboo is None:
            self._bamboo = PyBambooHR.PyBambooHR(
                subdomain=self.config.bamboo_subdomain,
                api_key=self.config.bamboo_api_key)
            self._bamboo.employee_fields['payPer'] = (
                'paid_per',
                'The employee\'s CURRENT pay per. ie: '
                '"Hour", "Day", "Week", "Month", "Quarter", "Year".')
        return self._bamboo

    def get_employees(self):
        return self.bamboo.get_employee_directory()

    def get_employee(self, id, *args, **kwargs):
        return self.bamboo.get_employee(id, *args, **kwargs)

    def get_employee_changes(self, since=None):
        """
        returns something like this:
        {'employees': {'108': {'action': 'Deleted',
                       'id': '108',
                       'lastChanged': '2019-07-19T16:06:56+00:00'},
               '109': {'action': 'Deleted',
                       'id': '109',
                       'lastChanged': '2019-07-23T20:53:27+00:00'},
               '110': {'action': 'Deleted',
                       'id': '110',
                       'lastChanged': '2019-08-06T16:53:57+00:00'}},
                        'latest': '2019-08-06T16:53:57+00:00'}
        """
        one_hour_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        since = since or one_hour_ago
        return self.bamboo.get_employee_changes(since=since)
