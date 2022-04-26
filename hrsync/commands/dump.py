from hrsync import bamboo, deltek
import hrsync.mapping
from pipedrive.client import Client

import json


# Utils
def printer(options, value):
    if options.pretty:
        value = json.dumps(value, indent=4, sort_keys=True)
    else:
        value = json.dumps(value)
    print(value)


# Bamboo
def bamboo_employees(options):
    impl = bamboo.BambooApi(options.config)
    printer(options, impl.get_employees())


def bamboo_employee(options):
    impl = bamboo.BambooApi(options.config)
    printer(options, impl.get_employee(options.id))


def bamboo_employee_changes(options):
    impl = bamboo.BambooApi(options.config)
    printer(options, impl.get_employee_changes())


# Deltek
def deltek_employees(options):
    impl = deltek.DeltekApi(options.config)
    printer(options, impl.get_employees())


def deltek_employee(options):
    impl = deltek.DeltekApi(options.config)
    printer(
        options, impl.get_employee(options.Employee, options.EmployeeCompany))


def deltek_create_employee(options):
    impl = deltek.DeltekApi(options.config)
    with open(options.file, 'r') as f:
        employees = json.loads(f.read())

    for employee in employees:
        defaults = impl.get_metadata_employee_required()
        defaults.update(employee)
        params = defaults
        printer(options, impl.create_employee(params))


def deltek_update_employee(options):
    impl = deltek.DeltekApi(options.config)
    with open(options.file, 'r') as f:
        employees = json.loads(f.read())

    for employee in employees:
        printer(options, impl.update_employee(employee))


def deltek_metadata_employee(options):
    impl = deltek.DeltekApi(options.config)
    printer(options, impl.get_metadata_employee())


def deltek_default_employee(options):
    impl = deltek.DeltekApi(options.config)
    printer(options, impl.get_default_employee())


def deltek_organizations(options):
    impl = deltek.DeltekApi(options.config)
    printer(options, impl.get_organizations())


def deltek_metadata(options):
    impl = deltek.DeltekApi(options.config)
    printer(options, impl.get_metadata(options.codeTable))


def deltek_codetable(options):
    impl = deltek.DeltekApi(options.config)
    printer(options, impl.get_codetable(options.codeTable))


def dump_mapping(options):
    items = [x[0:2] for x in hrsync.mapping.mapping]

    print("# Bamboo: Deltek")
    bamboo_sorted = sorted(items, key=lambda x: x[0])
    for bamboo_, deltek_ in bamboo_sorted:
        print("{}: {}".format(bamboo_, deltek_))

    print()
    print("# Deltek: Bamboo")
    deltek_sorted = sorted(items, key=lambda x: x[0])
    for deltek_, bamboo_ in deltek_sorted:
        print("{}: {}".format(deltek_, bamboo_))


def bamboo_get(options):
    client = bamboo.BambooApi(options.config)
    printer(options, client.bamboo._query(options.url, params={}))


def deltek_get(options):
    impl = deltek.DeltekApi(options.config)
    url = '{deltek_api_url}/{url}'.format(
        url=options.url, **options.config.to_dict())
    printer(options, impl._send(url))


def pipedrive_get(options):
    client = Client(domain=options.config.pipedrive_api_url)
    client.set_api_token(options.config.pipedrive_api_token)
    printer(options, client._get(client.BASE_URL + options.url))
