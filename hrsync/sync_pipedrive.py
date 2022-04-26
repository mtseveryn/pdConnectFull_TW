from hrsync import db
from hrsync import deltek
from hrsync import import_contacts
from hrsync import pipedrive_main
from hrsync import sendmail
from hrsync.config import Config
from pipedrive.client import Client
from hrsync.pipedrive_custom_fields import PipedriveCustomFields

import datetime
import dateutil.parser
import difflib
import json
import requests
import sys


class SyncPipedrive:
    def __init__(self, config_file):
        self.config = config = Config.from_file(config_file)
        self.import_contacts = import_contacts.ImportContact(config_file)

        db.init(url=config.sqlalchemy_url)
        self.session = db.session()

        self.pipedrive_client = Client(domain=config.pipedrive_api_url)
        self.pipedrive_client.set_api_token(config.pipedrive_api_token)
        self.pipedrive_impl = self.pipedrive_client

        self.deltek_client = deltek.DeltekApi(config)
        self.deltek_impl = self.deltek_client

        self._deal_custom_fields_options = None

    @property
    def deal_custom_fields_options(self):
        if self._deal_custom_fields_options is None:
            custom_fields = \
                self.pipedrive_client.deals.get_deal_fields()['data']
            self._deal_custom_fields_options = \
                PipedriveCustomFields.options_by_id(custom_fields)
        return self._deal_custom_fields_options

    def _deltek_get(self, url):
        url = '{deltek_api_url}/{url}'.format(
            url=url, **self.config.to_dict())
        return self.deltek_impl._send(url)

    def _valid_update_time(self, update_time):
        # only check last 24 hours updates
        yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
        if update_time < yesterday:
            return False

        return True

    def _changed(self, record, update_time):
        first = record.first()
        # if we dont have this record in database it has changed
        if first is None:
            print('is not in db')
            return True

        # if what we have in database is older than the update the record has
        # changed.
        if first.datetime < update_time:
            print('datetime < update_time')
            return True

        print('ignored', first.__tablename__, first.pipedrive_id)
        return False

    def _diffs(self, msg, before, after):
        a = [
            '%s:%s' % (key, value or "")
            for (key, value) in sorted(before.items())
            if key in after
        ]
        b = [
            '%s:%s' % (key, value or "")
            for (key, value) in sorted(after.items())
        ]

        for diff in difflib.unified_diff(
                a,
                b,
                fromfile='before {}'.format(msg),
                tofile='after {}'.format(msg)):
            yield diff

    def _diff(self, msg, before, updated):
        diffs = []
        diffs.append(msg)
        if len(before.keys()) == 0:
            diffs.append("** new item created")

        for diff in self._diffs(msg, before, updated):
            diffs.append(diff)
            print(diff)

        output = "\n".join(diffs)
        return output

    def _sendmail(self, message):
        if not self.config.alert_email:
            return

        to = self.config.alert_email
        subject = "Sync Pipedrive/Deltek"
        sendmail.sendmail(
            self.config,
            to,
            subject,
            message)

    def _sendmail_created(self, message, json_str=None):
        if not self.config.new_project_email:
            return

        to = self.config.new_project_email
        subject = "Pipedrive/Deltek new project was created"
        sendmail.sendmail(
            self.config,
            to,
            subject,
            message,
            json_str)

    def _sendmail_won(self, message, json_str):
        if not self.config.won_email:
            return

        to = self.config.won_email
        subject = "Pipedrive/Deltek project won"
        sendmail.sendmail(
            self.config,
            to,
            subject,
            message)

    def _sendmail_lost(self, message, json_str):
        if not self.config.lost_email:
            return

        to = self.config.lost_email
        subject = "Pipedrive/Deltek project was lost"
        sendmail.sendmail(
            self.config,
            to,
            subject,
            message)

    def _sendmail_dormant(self, message, json_str):
        if not self.config.lost_email:
            return

        to = self.config.dormant_email or self.config.lost_email
        subject = "Pipedrive/Deltek project is dormant/innactive"
        sendmail.sendmail(
            self.config,
            to,
            subject,
            message)

    def _send_to_api_db(self, state, json_str, deal_id):
        timestamp = datetime.datetime.utcnow().isoformat()

        data = dict(
            timestamp=timestamp,
            deal_id=deal_id,
            event_name=state,
            deal_data=json_str)

        dev = (self.config.api_dev_url, self.config.api_dev_username, self.config.api_dev_password)
        prod = (self.config.api_prod_url, self.config.api_prod_username, self.config.api_prod_password)
        envs = [dev, prod]
        for url, username, password in envs:
            try:
                self._api_post_deal_change(
                    url,
                    username,
                    password,
                    data)
            except Exception as e:
                import sys
                import traceback
                traceback.print_exc(file=sys.stdout)
                print(e)

    @staticmethod
    def _api_post_deal_change(url, username, password, params):
        print("sending params:\n{}".format(params))

        route="{}/api/v1/security/login".format(url)
        auth = dict(password=password, provider="db", refresh=True, username=username)
        r = requests.post(route, json=auth)
        token = r.json()['access_token']

        route = "{}/api/v1/dealchangesmodelapi/".format(url)
        response = requests.post(
            route,
            json=params,
            headers={"Authorization": "Bearer {}".format(token)})
        print(response)
        print(response.content)

    def replace_pipedrive_fields(self, data):
        data_modified = data.copy()
        for key, value in self.config.to_dict().items():
            if value in data:
                x = key.replace("pipedrive_field_id_", "")
                data_modified[x] = data[value]
                del data_modified[value]
        return data_modified

    def format_deal(self, deal, deltek_link):
        # show summary
        message = """
{id} - {title}
{short_description}
{pipedrive_link}
{deltek_link}
"""
        pipedrive_link = "{}/deal/{}".format(
            self.config.pipedrive_api_url,
            deal['id'])
        short_description = \
            deal[self.config.pipedrive_field_id_short_description]
        message = message.format(
            id=deal['id'],
            title=deal['title'],
            short_description=short_description,
            pipedrive_link=pipedrive_link,
            deltek_link=deltek_link)

        data = deal.copy()
        data = self.replace_pipedrive_fields(data)
        data.update(dict(
            pipedrive_link=pipedrive_link,
            deltek_link=deltek_link))


        json_str = json.dumps(data, indent=4, sort_keys=True)
        return message, json_str

    def get_contact(self, contact_id):
        return self.deltek_client.get_contact(contact_id)

    def get_firm(self, firm_id):
        return self.deltek_client.get_firm(firm_id)

    def get_organization(self, organization_id):
        return self.pipedrive_client.organizations.get_organization(
            organization_id)

    def get_person(self, person_id):
        return self.pipedrive_client.persons.get_person(
            person_id)

    def get_project(self, project_id):
        return self.deltek_client.get_project(project_id)

    def changes_contacts(self):
        # python -m hrsync -c prod.ini deltek-get \
        #    '/contact?fieldFilter=ClientID,ModDate&pageSize=50&order=ModDate_D'
        contacts = self._deltek_get(
            '/contact?pageSize=50&order=ModDate_D')
        for contact in contacts:
            update_time = dateutil.parser.parse(contact['ModDate'])
            if not self._valid_update_time(update_time):
                continue

            record = db.PipedrivePerson.by_deltek_id(
                self.session, contact['ContactID'])
            if not self._changed(record, update_time):
                continue

            yield contact, record, update_time

    def changes_deals(self):
        # done using a pre-configured filter
        deals = self.pipedrive_client.deals.get_all_deals(
            params=dict(filter_id=self.config.pipedrive_filter_id_sync_deals))

        # filter deals where greater than the last updated date
        for deal in deals['data'] or []:
            update_time = dateutil.parser.parse(deal['update_time'])
            if not self._valid_update_time(update_time):
                continue

            record = db.PipedriveDeal.by_pipedrive_id(self.session, deal['id'])
            if not self._changed(record, update_time):
                continue

            yield deal, record, update_time


    def get_deals(self, deals_ids):
        for id in deals_ids:
            deal = self.pipedrive_client.deals.get_deal(id)['data']
            update_time = datetime.datetime.now()

            record = db.PipedriveDeal.by_pipedrive_id(self.session, deal['id'])
            if not self._changed(record, update_time):
                continue

            yield deal, record, update_time


    def changes_firms(self):
        # python -m hrsync -c prod.ini deltek-get \
        #   '/firm?fieldFilter=ClientID,ModDate&pageSize=50&order=ModDate_D'
        firms = self._deltek_get(
            '/firm?pageSize=50&order=ModDate_D')
        for firm in firms:
            update_time = dateutil.parser.parse(firm['ModDate'])
            if not self._valid_update_time(update_time):
                continue

            record = db.PipedriveOrganization.by_deltek_id(
                self.session, firm['ClientID'])
            if not self._changed(record, update_time):
                continue

            yield firm, record, update_time

    def changes_organizations(self):
        # done using a pre-configured filter
        organizations = \
            self.pipedrive_client.organizations.get_all_organizations(
                params=dict(filter_id=self.config.pipedrive_filter_id_sync_organizations))

        # filter organizations where greater than the last updated date
        for organization in organizations['data'] or []:
            update_time = dateutil.parser.parse(organization['update_time'])
            if not self._valid_update_time(update_time):
                continue

            record = db.PipedriveOrganization.by_pipedrive_id(
                self.session, organization['id'])
            if not self._changed(record, update_time):
                continue

            yield organization, record, update_time

    def changes_persons(self):
        # done using a pre-configured filter
        persons = self.pipedrive_client.persons.get_all_persons(
            params=dict(
                filter_id=self.config.pipedrive_filter_id_sync_persons))

        # filter persons where greater than the last updated date
        for person in persons['data'] or []:
            update_time = dateutil.parser.parse(person['update_time'])
            if not self._valid_update_time(update_time):
                continue

            record = db.PipedrivePerson.by_pipedrive_id(
                self.session, person['id'])
            if not self._changed(record, update_time):
                continue

            yield person, record, update_time

    def _update_db(self, first, table, deltek_id, pipedrive_id):
        p = None
        if first is None:
            p = table()
            p.deltek_id = deltek_id
            p.pipedrive_id = pipedrive_id
            self.session.add(p)
        else:
            p = first
            #assert p.deltek_id == deltek_id
            assert p.pipedrive_id == pipedrive_id

        p.datetime = datetime.datetime.utcnow()
        self.session.commit()

    def update_contact(self, contact, record, update_time):
        print('update contact:', contact['ContactID'], contact['flName'])
        if self.config.dry_run:
            return

        person = import_contacts.ImportContact().fill_person(contact)
        first = record.first()
        if first is None:
            before = {}
            updated = self.pipedrive_client.persons.create_person(person)
        else:
            before = self.get_person(first.pipedrive_id)
            updated = self.pipedrive_client.persons.update_person(
                person, first.pipedrive_id)

        #self._sendmail(self._diff('person', before, updated))

        self._update_db(
            first,
            table=db.PipedrivePerson,
            deltek_id=person['ContactID'],
            pipedrive_id=updated['data']['id'])

    def update_firm(self, firm, record, update_time):
        print('update firm:', firm['ClientID'], firm['Name'])
        if self.config.dry_run:
            return

        organization = import_contacts.ImportContact().fill_organization(firm)
        first = record.first()
        if first is None:
            before = {}
            updated = self.pipedrive_client.organizations.create_organization(
                organization)
        else:
            before = self.get_organization(first.pipedrive_id)
            updated = self.pipedrive_client.organizations.update_organization(
                first.pipedrive_id,
                organization)

        #self._sendmail(self._diff('firm', before, updated))

        self._update_db(
            first,
            table=db.PipedriveOrganization,
            deltek_id=firm['ClientID'],
            pipedrive_id=updated['data']['id'])

    def update_organization(self, organization, record, update_time):
        print('update organization:', organization['id'], organization['name'])
        if self.config.dry_run:
            return

        first = record.first()
        if first is None:
            before = address = {}
            updated, address = pipedrive_main.create_firm(
                self, organization)
        else:
            before = self.get_firm(first.deltek_id)[0]
            # pprint.pprint(deltek_impl.get_firm_addresses(client_id))
            updated, address = pipedrive_main.sync_organization(
                self, organization, first.deltek_id)

        #self._sendmail(self._diff('firm', before, updated))

        self._update_db(
            first,
            table=db.PipedriveOrganization,
            deltek_id=updated['ClientID'],
            pipedrive_id=organization['id'])

    def update_person(self, person, record, update_time):
        print('update person:', person["first_name"], person["last_name"])
        if self.config.dry_run:
            return

        first = record.first()
        if first is None:
            before = {}
            updated = pipedrive_main.create_contact(
                self, person)
        else:
            before = self.get_contact(first.deltek_id)[0]
            client_id = None
            if person['org_id'] is not None:
                client_id = db.PipedriveOrganization.by_pipedrive_id(
                    self.session,
                    person['org_id']['value']).first().deltek_id
            try:
                updated = pipedrive_main.sync_person(
                    self, person, client_id, first.deltek_id)
            except:
                pass

        #self._sendmail(self._diff('contact', before, updated))

        self._update_db(
            first,
            table=db.PipedrivePerson,
            deltek_id=updated['ContactID'],
            pipedrive_id=person['id'])

    def get_deltek_regular_project_id(self, deal):
        promos_suffix = ""

        project_number = deal.get(self.config.
            pipedrive_field_id_override_deltek_project_number)

        if project_number is None or project_number.strip() == "":
            project_number = "{}PD".format(deal['id'])

        return "{}{}".format(project_number, promos_suffix)

    def get_deltek_promo_project_id(self, deal):
        promos_suffix = ""

        project_number = deal.get(self.config.
            pipedrive_field_id_override_deltek_promo_project_number)

        if project_number is None or project_number.strip() == "":
            promos_suffix = "P"
            project_number = "{}PD".format(deal['id'])

        return "{}{}".format(project_number, promos_suffix)

    def update_deal(self, deal, record, update_time):
        print('update deal:', deal['id'], deal['title'])
        if self.config.dry_run:
            return

        first = record.first()
        creating = first is None

        before = {}
        deltek_id = promo_deltek_id = self.get_deltek_promo_project_id(deal)
        regular_deltek_id = self.get_deltek_regular_project_id(deal)

        try:
            before = self.get_project(deltek_id)[0]
        except:
            before = {}

        updated = pipedrive_main.sync_deal(
            self, deltek_id, regular_deltek_id, deal, creating)

        # update deal if deltek_id is not already set
        deltek_link = \
            "{deltek_app_url}#!Projects/view/project/0/{deltek_id}/presentation".format(
                deltek_id=deltek_id,
                **self.config.to_dict())

        data = {
            self.config.pipedrive_field_id_deltek_link: deltek_link,
            self.config.pipedrive_field_id_project_number_id: deal['id']
        }

        sent_to_api_db = False
        if creating:
            deal_info, deal_json = self.format_deal(deal, deltek_link)
            message = """A project was created.\n\n{deal_info}""".format(
                deal_info=deal_info)
            self._sendmail_created(message, deal_json)
            self._send_to_api_db('new', deal_json, deal['id'])
            sent_to_api_db = True

        win = deal['status'] == 'won'
        record = db.PipedriveDealStatus.get(self.session, deal['id'])
        if record.status != "won" and win:
            # send email to ppl
            deal_info, deal_json = self.format_deal(deal, deltek_link)
            message = """A project is won and hours should be transfered """\
                      """from the promos project: {deltek_link}\n\n{deal_info}""".format(
                        deltek_link=deltek_link,
                        deal_info=deal_info)
            self._sendmail_won(message, deal_json)
            self._send_to_api_db('won', deal_json, deal['id'])
            sent_to_api_db = True


        # deal with lost
        lost = deal['status'] == 'lost'
        if record.status != "lost" and lost:
            deal_info, deal_json = self.format_deal(deal, deltek_link)
            message = """A deal was lost.\n\n{deal_info}""".format(
                deal_info=deal_info)
            self._sendmail_lost(message, deal_json)
            self._send_to_api_db('lost', deal_json, deal['id'])
            sent_to_api_db = True

        # deal is dormant
        dormant = 'dormant' in deal['status'].lower()
        if 'dormant' not in record.status.lower() and dormant:
            deal_info, deal_json = self.format_deal(deal, deltek_link)
            message = """A deal is dormant/innactive.\n\n{deal_info}""".format(
                deal_info=deal_info)
            self._sendmail_dormant(message, deal_json)
            self._send_to_api_db('dormant', deal_json, deal['id'])
            sent_to_api_db = True


        if not sent_to_api_db:
            deal_info, deal_json = self.format_deal(deal, deltek_link)
            self._send_to_api_db('updated', deal_json, deal['id'])
            sent_to_api_db = True


        record.status = deal['status']
        self.session.commit()

        # TODO send email diff + other descriptif of the project + .json
        self._sendmail(self._diff('project', before, updated))

        return updated, data

    def sync_organization(self, organization_id, update_time):
        if organization_id is None:
            return
        organization = self.pipedrive_client.organizations\
            .get_organization(organization_id)['data']
        record = db.PipedriveOrganization.by_pipedrive_id(
            self.session, organization_id)
        self.update_organization(organization, record, update_time)

    def main(self, deals_ids):
        if self.config.dry_run:
            print("WARNING, we are running in dry_run mode")

        """
        # deltek changes
        for firm, record, update_time in self.changes_firms():
            self.update_firm(firm, record, update_time)

        for contact, record, update_time in self.changes_contacts():
            self.update_contact(contact, record, update_time)

        # pipedrive changes
        for organization, record, update_time in self.changes_organizations():
            self.update_organization(organization, record, update_time)

        for person, record, update_time in self.changes_persons():
            self.update_person(person, record, update_time)
        """

        def do_update_deal(deal, record_deal, update_time):
            # sync organization
            try:
                organization_id = deal['org_id']['value'] \
                    if deal['org_id'] is not None else None
                self.sync_organization(organization_id, update_time)

                # sync person
                person_id = deal['person_id']['value'] \
                    if deal['person_id'] is not None else None

                if person_id is not None:
                    record_person = db.PipedrivePerson.by_pipedrive_id(
                        self.session, person_id)
                    person = self.pipedrive_client.persons\
                        .get_person(person_id)['data']

                    # here for this person we have to create the organization
                    organization_id = person['org_id']['value'] \
                        if person['org_id'] is not None else None

                    self.sync_organization(organization_id, update_time)
                    self.update_person(person, record_person, update_time)
            except Exception as e:
                import sys
                import traceback
                traceback.print_exc(file=sys.stdout)
                print(e)


            # sync projet
            project, data = self.update_deal(deal, record_deal, update_time)
            deltek_project_id = project['WBS1']

            # sync all activities
            deal_id = deal['id']
            activities = self.pipedrive_impl.deals.get_deal_activities(deal_id)
            for activity in activities['data'] or []:
                update_time = dateutil.parser.parse(activity['update_time'])
                #if not self._valid_update_time(update_time):
                #    continue

                if self.config.dry_run:
                    return

                pipedrive_main.sync_activity(
                    self.deltek_impl, deltek_project_id, activity)

            notes = self.pipedrive_impl.notes.get_all_notes(
                params=dict(deal_id=deal_id))
            for note in notes['data'] or []:
                update_time = dateutil.parser.parse(note['update_time'])
                #if not self._valid_update_time(update_time):
                #    continue

                if self.config.dry_run:
                    return

                pipedrive_main.sync_note(
                    self.deltek_impl, deltek_project_id, note)

            emails = self.pipedrive_impl.deals.get_deal_mail_messages(deal_id)
            if emails is None:
                return data

            emails = emails.get('data', [])
            if emails is None:
                return data

            for email in emails:
                email = email['data']
                update_time = dateutil.parser.parse(email['update_time'])
                # TODO we have to do it only once because it will be slow
                # otherwise?
                #if not self._valid_update_time(update_time):
                #    continue

                if self.config.dry_run:
                    return

                try:
                    pipedrive_main.sync_email(
                        self.deltek_impl, deltek_project_id, email)
                except Exception as e:
                    import sys
                    import traceback
                    traceback.print_exc(file=sys.stdout)
                    print(e)

            return data

        # pipedrive changes on deals
        if len(deals_ids) > 0:
            deals = self.get_deals(deals_ids)
        else:
            deals = self.changes_deals()

        for deal, record_deal, update_time in deals:
            data = {}
            current_time_str = \
                datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            try:
                data = do_update_deal(deal, record_deal, update_time)
                data[self.config.pipedrive_field_id_deltek_sync_status] = \
                    "{} - OK".format(current_time_str)
            except Exception as e:
                import sys
                import traceback
                traceback.print_exc(file=sys.stdout)
                print(e)

                message = json.loads(str(e))["Message"]
                data[self.config.pipedrive_field_id_deltek_sync_status] = \
                    "{} - ERROR - {}".format(current_time_str, message)
            finally:
                first = record_deal.first()
                deltek_id = self.get_deltek_promo_project_id(deal)

                self.pipedrive_client.deals.update_deal(deal['id'], data)
                self._update_db(
                    first,
                    table=db.PipedriveDeal,
                    deltek_id=deltek_id,
                    pipedrive_id=deal['id'])


if __name__ == "__main__":
    config_file = sys.argv[1]
    print("{} running hrsync.sync_pipedrive with config_file {}".format(
        datetime.datetime.now(),
        config_file))

    deals_ids = [int(id) for id in sys.argv[2:]]
    print(deals_ids)
    SyncPipedrive(config_file).main(deals_ids)
