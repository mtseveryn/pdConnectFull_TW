from PyBambooHR import PyBambooHR
import datetime
import pprint

bamboo = PyBambooHR.PyBambooHR(
    subdomain='thinkwellgroupsandbox',
    api_key='f1d05448ffa9b66e80def5e804df337ac0f6d770')

#employees = bamboo.get_employee_directory()
#print(json.dumps(employees))

one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
changes = bamboo.get_employee_changes(since=one_hour_ago)
pprint.pprint(changes)


#print(len(employees))
#employe0 = employees[0]
#pprint.pprint(employe0)

# we could check for employee changes
#      def get_employee_changes(self, since=None):
# one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
# bamboo.get_employee_changes(since=one_hour_ago)

# https://www.bamboohr.com/api/documentation/changes.php

# we could check for employe fields list this seems to list more data than just
# the basics. It uses the listFields
# https://www.bamboohr.com/api/documentation/employees.php#listFields
