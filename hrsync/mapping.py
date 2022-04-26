from hrsync import bamboo, deltek
from hrsync import sendmail
from hrsync.config import Config

import datetime
import difflib
import pprint

from hrsync import db


# bamboo, deltek
def location_to_employee_company(location, values, *args):
    """
    This method should transform a bamboo location to a deltek location
    >>> localtion = 'ML - TWG Montreal'
    >>> assert location_to_employee_company(localtion) == 'ML'
    """

    # bamboo to deltek:
    LA = 'US - TWG Los Angeles'
    MTL = 'ML - TWG Montreal'
    ABU = 'AD - TWG Abu Dhabi'
    BEIJING = 'BJ - TWG Beijing'

    # Hong Kong?
    # pprint.pprint(bamboo_impl.bamboo.get_meta_lists())
    locations = {
        'Realisations-Montréal': MTL,
        'Thinkwell Group': LA,
        'Thinkwell Group Abu Dhabi Studio': ABU,
        'Thinkwell Group Beijing Studio': BEIJING,
        'Thinkwell Group Inc.': LA,
        'Thinkwell Group LA Studio': LA,
        'Thinkwell Group Studio Montréal': MTL,

        'Montréal': MTL,

        'Si Ke Wei Lai (aka TW Beijing Studio)': BEIJING,
        'Thinkwell Abu Dhabi Office': ABU,
        'Thinkwell LA Studio': LA,
        'Thinkwell Studio Montréal': MTL
    }
    #'Thinkwell Headquarters': ?,

    return locations[location].split(' - ')[0]


def country(value, values, *args):
    countries = {
        "United States": "US",
        "Canada": "CA"
    }

    return countries.get(value, value)


def date(value, values, *args):
    from dateutil.parser import parse
    if value == '0000-00-00':
        return None
    return "{}.000".format(parse(value).isoformat())


def gender(value, values, *args):
    if value == "Male":
        return "M"
    if value == "Female":
        return "F"
    return ""


def ethnicity(value, values, *args):
    # bamboo => deltek
    mapping = {
        "White": "White",
        "Black or African American": "Black",
        "Hispanic or Latino": "Hispanic or Latino",
        "Native Hawaiian or Other Pacific Islander": "Pacific Islander",
        "Asian": "Asian",
        "American Indian or Alaska Native": "Native",
        "Two or More Races":  "Two or More Races"
    }
    return mapping.get(value, None)


def language(value, values, *args):
    # TODO
    return "en-US"


def supervisor_name(value, values, *args):
    # strip multiple spaces
    return value.replace('  ', ' ').strip()


def supervisor(value, values, bamboo_impl, deltek_impl, *args):
    id = values.get('supervisorEId', None)
    if not id:
        return None

    supervisor = bamboo_impl.get_employee(id)
    return supervisor['employeeNumber']


def sanitize_date(value, values, *args):
    if value == "0000-00-00":
        return None
    return value


def annual_pay_rate(value, values, *args):
    """value = '30.000 USD'"""
    payPer = values['payPer']

    money_digits = "0123456789.,"

    amount = "".join([c for c in value if c in money_digits])
    if len(amount.strip()) == 0:
        return None
    amount = float(amount)

    if payPer.lower() == 'hour':
        return amount * 40 * 52

    if payPer.lower() == 'week':
        return amount * 52

    if payPer.lower() == 'year':
        return amount

    return None


def pay_per(value, values, *args):
    if value.lower() == 'hour':
        return "H"
    if value.lower() == 'year':
        return "S"
    return None


def status(value, values, *args):
    "Active: A"
    return value[0]

def work_phone(value, values, *args):
    if values['workPhoneExtension'] is None or \
            not values['workPhoneExtension'].strip():
        return values['workPhone']

    return "{} #{}".format(
        values['workPhone'], values['workPhoneExtension'])


mapping = [
    #('id', 'AlienNumber'),
    ('address1', 'Address1'),
    ('address2', 'Address2'),
    ('city', 'City'),
    ('country', 'Country', country),
    ('dateOfBirth', 'CustDateofBirth', date),
    #('location', 'Org', org),
    #('location', 'Location'), # noqa
    ('department', 'CustDepartment'),
    #('division', 'HomeCompany'), # noqa
    ('displayName', 'PreferredName'),
    #('division', 'HomeCompany'), # noqa
    ('employeeNumber', 'Employee'),
    #('employmentStatus', 'Type'), # noqa
    ('ethnicity', 'CustEthnicity', ethnicity),
    ('firstName', 'FirstName'),
    #('gender', 'Gender', gender),
    ('gender', 'CustGender'),
    ('hireDate', 'HireDate', date),
    ('homeEmail', 'CustPersonalEmail'),
    ('homePhone', 'HomePhone'),
    ('jobTitle', 'Title'),
    ('lastName', 'LastName'),
    ('location', 'EmployeeCompany', location_to_employee_company),
    ('middleName', 'MiddleName'),
    ('mobilePhone', 'MobilePhone'),
    #('payGroup', 'BillingCategory'), # noqa
    #('payPer', 'PayRateMeth'), # noqa
    # "RaiseDate or DateofLastRaise" # noqa
    #('payRateEffectiveDate', 'RaiseDate', date),
    ('payRateEffectiveDate', 'CustDateofLastRaise', date),
    ('payRate', 'CustCurrentNetSalary', annual_pay_rate),
    #('payPer', 'PayType', pay_per), # noqa
    #('payRate', 'JobCostRate', pay_rate), # noqa
    #('payPer', 'JobCostType', pay_per), # noqa
    ('preferredName', 'PreferredName'),
    ('ssn', 'SSN'),
    ('state', 'State'),
    ('status', 'Status', status),
    #('supervisor', 'SupervisorName', supervisor_name), # noqa
    ('supervisor', 'Supervisor', supervisor),
    ('terminationDate', 'TerminationDate', sanitize_date),
    ('workEmail', 'EMail'),
    ('workPhone', 'WorkPhone', work_phone),
    ('zipcode', 'ZIP'),

    #('unknown', 'Language', language),
]


def diffs(old_deltek, new_deltek):
    a = [
        '%s:%s' % (key, value or "")
        for (key, value) in sorted(old_deltek.items())
        if key in new_deltek
    ]
    b = [
        '%s:%s' % (key, value or "")
        for (key, value) in sorted(new_deltek.items())
    ]

    for diff in difflib.unified_diff(
            a,
            b,
            fromfile='old_deltek',
            tofile='new_deltek'):
        yield diff


def bamboo_to_deltek(b, d, bamboo_impl, deltek_impl, bsk, dsk):
    for field in mapping:
        func = None

        if len(field) == 2:
            bamboo_key, deltek_key = field

            def f(x, *args):
                return x
            func = f  # simply affect the data unchanged

        elif len(field) == 3:
            bamboo_key, deltek_key, func = field

        if bamboo_key not in b and bamboo_key != "unknown":
            continue
        d[deltek_key] = func(
            b.get(bamboo_key, ""), b, bamboo_impl, deltek_impl, bsk, dsk)


def print_diffs(old_deltek, new_deltek):
    for diff in diffs(old_deltek, new_deltek):
        print(diff)


def send_alert(session, id, last_changed, config, to, subject, message):
    alert = session.query(db.Alert).get(id)
    if alert is None:
        alert = db.Alert()
        alert.bamboo_id = id
        alert.datetime = ""
        session.add(alert)

    # we send the alert only once if the last change is
    # higher than the last time we sent an alert.
    if last_changed > alert.datetime:
        sendmail.sendmail(
            config,
            to,
            subject,
            message)
    alert.datetime = last_changed
    session.commit()


def main(args):
    config = Config.from_file(args[1])
    bamboo_impl = bamboo.BambooApi(config)
    deltek_impl = deltek.DeltekApi(config)

    db.init(url=config.sqlalchemy_url)
    session = db.session()

    since = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    print("fetching changes since: {}".format(since.isoformat()))
    changes = bamboo_impl.get_employee_changes(since=since)
    pprint.pprint(changes)
    employees = changes.get('employees', {}) or {}

    # last time it changed on bamboo
    last_changed = {
        id: values['lastChanged']
        for id, values in employees.items()
        if values['action'] in ('Updated', 'Inserted')
    }

    # last change we recorded
    changes = {
        id: session.query(db.Change).get(id)
        for id, values in employees.items()
    }

    # all bamboo employe that are not up to date
    bs = []
    for id, values in employees.items():
        valid = values['action'] in ('Updated', 'Inserted') and (
                changes[id] is None or
                changes[id].datetime < last_changed[id]
            )
        if not valid:
            continue

        employe = bamboo_impl.get_employee(id)
        if employe["employmentHistoryStatus"] == "Contractor":
            continue
        bs.append(employe)

    # if there is no new changes just stop
    if len(bs) == 0:
        return

    # and if changed are already taken into account
    ds = deltek_impl.get_employees()

    bsk = {"{}".format(b['id']): b for b in bs}
    dsk = {"{}".format(d['Employee']): d for d in ds}

    # to get employeeNumber from bamboo we have to check employe changes,
    # because the directory does not return employe_number
    # bsk = {b.get('employeeNumber', None): b for b in bs}
    # dsk = {d['Employee']: d for d in ds}

    ids = [b for b in bsk.keys()]

    for id in ids:
        try:
            b = bsk[id]
            print("updating user id:{} - {} {} ({})".format(
                id, b["firstName"], b["lastName"], b["employeeNumber"]))

            # we dont want to sync Contractor
            if b["employmentHistoryStatus"] == "Contractor":
                print("Skipping Contractor")
                continue

            new_deltek = {}
            bamboo_to_deltek(b, new_deltek, bamboo_impl, deltek_impl, bsk, dsk)

            # Here make sure we dont already have a Employee and EmployeCompany
            # at deltek
            employee = session.query(db.Employee).get(int(id))
            if employee is None:
                # here we should check if a deltek employee already exists
                # with this employee number
                Employee = new_deltek['Employee']
                EmployeeCompany = new_deltek['EmployeeCompany']
            else:
                # this can change so we are better check in local database.
                # in the case where it change in bamboo it is still gooing to
                # be the same in Deltek, so we refer to it with the old
                # Employee and EmployeeCompany
                Employee = employee.deltek_employee
                EmployeeCompany = employee.deltek_employee_company

                if \
                    new_deltek['Employee'] != employee.deltek_employee or \
                    new_deltek['EmployeeCompany'] != \
                        employee.deltek_employee_company:

                    message = "Bamboo employe changed but it cant be " \
                        "reflected in deltek.\n" \
                        "Bamboo id:{} - {} {} ({})\n" \
                        "Deltek {} {}\n".format(
                            id,
                            b["firstName"],
                            b["lastName"],
                            b["employeeNumber"],
                            Employee,
                            EmployeeCompany)

                    if config.dry_run != 'true':
                        send_alert(
                            session,
                            id,
                            last_changed[id],
                            config,
                            config.alert_email.split(","),
                            'Bamboo employee does not match with deltek',
                            message)

                    raise Exception(message)

            pprint.pprint("Deltek diff:")
            old_deltek = deltek_impl.get_employee(Employee, EmployeeCompany)[0]
            print(old_deltek)
            print_diffs(old_deltek, new_deltek)

            # email the diff
            diffs_ = list(diffs(old_deltek, new_deltek))
            if not diffs_:
                continue

            to = config.alert_email.split(",")
            subject = "HR Sync - Employee was updated"
            message = "\n".join(diffs_)
            sendmail.sendmail(
                config,
                to,
                subject,
                message)

            # check config if it is a dry run dont perform the update. It
            # would exit here.
            if config.dry_run != 'true':
                deltek_impl.update_employee(new_deltek, Employee, EmployeeCompany)

                if employee is None:
                    employee = db.Employee()
                employee.bamboo_id = int(id)
                employee.deltek_employee = new_deltek['Employee']
                employee.deltek_employee_company = new_deltek['EmployeeCompany']
                session.add(employee)
                session.commit()
            else:
                print("DRY_RUN mode so it will not do anything")

            # add change for this employe in db
            change = session.query(db.Change).get(id)
            if change is None:
                change = db.Change()
                change.bamboo_id = id
                change.dry_run = config.dry_run == 'true'
                session.add(change)
            change.datetime = last_changed[id]
            session.commit()

        except Exception:
            import traceback
            message = traceback.format_exc()
            print(message)

            send_alert(
                session,
                id,
                last_changed[id],
                config,
                config.admin_email.split(","),
                'Error with hrsync',
                message)


if __name__ == "__main__":
    import sys
    main(sys.argv)
