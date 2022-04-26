from hrsync import db
from hrsync import deltek
from hrsync.config import Config
from pipedrive.client import Client

from hrsync import pipedrive_main

import pprint
import uuid
import sys


class ImportContact:
    def get_pipedrive_organizations(self):
        limit = 500  # 500 is the maximum we can get from pipedrive
        i = 0
        organizations = []
        while True:
            os = \
                self.pipedrive_client.organizations.get_all_organizations(
                    params=dict(limit=limit, start=i*limit))['data']
            if os is None:
                break
            organizations += os
            i = i + 1

        # TODO exclude organization from the Thinkwell group company
        return organizations

    def get_deltek_firms(self):
        firms = self.deltek_client.get_firms()
        return firms

    def get_pipedrive_persons(self):
        limit = 500  # 500 is the maximum we can get from pipedrive
        i = 0
        persons = []
        while True:
            ps = \
                self.pipedrive_client.persons.get_all_persons(
                    params=dict(limit=limit, start=i*limit))['data']
            if ps is None:
                break
            persons += ps
            i = i + 1

        # TODO exclude persons from the Thinkwell group company
        return persons

    def get_deltek_contacts(self):
        contacts = self.deltek_client.get_contacts()
        return contacts

    def firm_address(self, firm):
        address = " ".join([
            firm['PrimaryAddress1'],
            firm['PrimaryAddress2'],
            firm['PrimaryAddress3'],
            firm['PrimaryAddress4'],
            firm['PrimaryCity'],
            firm['PrimaryState'],
            firm['PrimaryCountry'],
            firm['PrimaryZip']
        ])
        return address

    def fill_organization(self, firm):
        organization = {}
        organization['name'] = firm['Name']
        organization['address'] = self.firm_address(firm).strip()
        return organization

    def create_organization(self, firm):
        """
        # testing the creation of an organization
        org = self.create_organization({
            'Name': 'Compagnie de teste',
            'PrimaryAddress1': '4 Houston Center 1331 Lamar',
            'PrimaryAddress2': 'Ste 700',
            'PrimaryAddress3': '',
            'PrimaryAddress4': '',
            'PrimaryCity': 'Houston',
            'PrimaryCountry': 'US',
            'PrimaryEmail': '',
            'PrimaryFax': '',
            'PrimaryPhone': '',
            'PrimaryState': 'TX',
            'PrimaryZip': '77010',
        })
        """
        organization = self.fill_organization(firm)

        if self.config.dry_run:
            return

        org = self.pipedrive_client.organizations.create_organization(
                organization)

        pprint.pprint(org)
        o = db.PipedriveOrganization()
        o.deltek_id = firm["ClientID"]
        o.pipedrive_id = org['data']['id']
        o.origin = "deltek"
        return org

    def fill_person(self, contact):
        person = {}
        person['name'] = contact['flName']
        person['email'] = contact['Email']
        person['phone'] = contact['Phone']
        person[self.config.pipedrive_field_id_job_title] = contact["Title"]
        return person

    def create_person(self, contact):
        """
        # testing the creation of an organization
        person = self.create_person({
            'ContactID': str(uuid.uuid4()),
            'flName': 'Personne de test',
            'Email': 'louis.lynch@evodev.ca',
            'Phone': '514.267.0908',
        })
        """
        person = self.fill_person(contact)

        if self.config.dry_run:
            return

        person_obj = self.pipedrive_client.persons.create_person(
                person)
        p = db.PipedrivePerson()
        p.deltek_id = contact["ContactID"]
        p.pipedrive_id = person_obj['data']['id']
        p.origin = "deltek"

        self.session.add(p)
        self.session.commit()
        return person_obj

    def create_firm(self, organization):
        if self.config.dry_run:
            return

        firm, address = pipedrive_main.create_firm(self, organization)

        o = db.PipedriveOrganization()
        o.deltek_id = firm["ClientID"]
        o.pipedrive_id = organization['id']
        o.origin = "pipedrive"
        self.session.add(o)
        self.session.commit()
        return firm, address

    def create_contact(self, person):
        if self.config.dry_run:
            return

        contact = pipedrive_main.create_contact(self, person)

        p = db.PipedrivePerson()
        p.deltek_id = contact["ContactID"]
        p.pipedrive_id = person['id']
        p.origin = "pipedrive"
        self.session.add(p)
        self.session.commit()
        return contact

    def __init__(self, config_file):
        self.config = config = Config.from_file(config_file)

        db.init(url=config.sqlalchemy_url)
        self.session = db.session()

        self.pipedrive_client = Client(domain=config.pipedrive_api_url)
        self.pipedrive_client.set_api_token(config.pipedrive_api_token)

        self.deltek_client = deltek.DeltekApi(config)
        self.deltek_impl = self.deltek_client

    def main(self):

        if self.config.dry_run:
            print("DRY RUN MODE IS ON NO CHANGES ARE PERFORMED")

        self.import_organizations()
        self.import_persons()

    def import_organizations(self):
        def get():
            organizations = self.get_pipedrive_organizations()
            firms = self.get_deltek_firms()

            organization_by_name = {o['name']: o for o in organizations}
            firm_by_name = {f['Name']: f for f in firms}
            return organizations, firms, organization_by_name, firm_by_name

        organizations, firms, organization_by_name, firm_by_name = get()
        print(len(organizations), len(firms))

        # 1
        # mark all existing relations
        organizations, firms, organization_by_name, firm_by_name = get()
        count = 0
        names = set()
        for organization in organizations:
            name = organization['name']
            if name not in firm_by_name:
                continue

            if not organization['active_flag']:
                continue

            if name not in names:
                count = count + 1
                names.add(name)

            firm = firm_by_name[name]
            client_id = firm['ClientID']
            o = db.PipedriveOrganization().by_deltek_id(
                self.session, client_id).first()
            if o is not None:
                continue

            o = db.PipedriveOrganization().by_pipedrive_id(
                self.session, organization['id']).first()
            if o is not None:
                continue

            o = db.PipedriveOrganization()
            o.pipedrive_id = organization['id']
            o.deltek_id = client_id
            o.origin = "both"
            self.session.add(o)
            self.session.commit()

        pprint.pprint("shared organizations/firms: {}".format(count))

        # 2
        # TODO insert all missing organization in deltek firm
        organizations, firms, organization_by_name, firm_by_name = get()
        count_organization = 0
        for organization in organizations:
            o = db.PipedriveOrganization().by_pipedrive_id(
                self.session, organization['id']).first()
            if o is not None:
                continue

            count_organization = count_organization + 1
            # create in deltek
            print('creating firm')
            if not organization['active_flag']:
                continue
            pprint.pprint(self.create_firm(organization))
        pprint.pprint(
            'would create {} firms'.format(count_organization))

        # 3
        # TODO insert all missing firm in pipedrive organization
        return # TODO remove?
        organizations, firms, organization_by_name, firm_by_name = get()
        count_firm = 0
        for firm in firms:
            client_id = firm['ClientID']
            o = db.PipedriveOrganization().by_deltek_id(
                self.session, client_id).first()
            if o is not None:
                continue

            #  create in pipedrive
            count_firm = count_firm + 1
            print('creating organization')
            pprint.pprint(self.create_organization(firm))
            break  # TODO REMOVE
        pprint.pprint(
            'would create {} organization'.format(count_firm))

    def import_persons(self):
        def get():
            persons = self.get_pipedrive_persons()
            contacts = self.get_deltek_contacts()

            person_by_email = {}
            for person in persons:
                for email in person['email']:
                    person_by_email[email['value'].lower()] = person
            contact_by_email = {c['Email'].lower(): c for c in contacts}
            return persons, contacts, person_by_email, contact_by_email

        persons, contacts, person_by_email, contact_by_email = get()

        print(len(persons), len(contacts))

        count = 0
        for contact in contacts:
            if not contact['Email']:
                continue

            if contact['Email'] in person_by_email:
                count = count + 1

        pprint.pprint("shared persons/contacts: {}".format(count))

        # 1
        # mark all existing relations
        for person in persons:
            emails = person['email']
            found = False
            for email in emails:
                if email['value'].lower() in contact_by_email:
                    email = email['value'].lower()
                    found = True
                    break
            if not found:
                continue

            if not person['active_flag']:
                continue

            contact = contact_by_email[email]
            contact_id = contact['ContactID']
            p = db.PipedrivePerson().by_deltek_id(
                self.session, contact_id).first()
            if p is not None:
                continue

            p = db.PipedrivePerson().by_pipedrive_id(
                self.session, person['id']).first()
            if p is not None:
                continue

            p = db.PipedrivePerson()
            p.pipedrive_id = person['id']
            p.deltek_id = contact_id
            p.origin = "both"
            self.session.add(p)
            self.session.commit()

        # 2
        # insert all missing persons in deltek contacts
        persons, contacts, person_by_email, contact_by_email = get()
        count_person = 0
        for person in persons:
            p = db.PipedrivePerson.by_pipedrive_id(
                self.session, person['id']).first()
            if p is not None:
                continue

            if not person['active_flag']:
                continue

            # create in deltek
            print("creating contact")
            count_person = count_person + 1
            pprint.pprint(self.create_contact(person))
        pprint.pprint(
            'would create {} persons'.format(count_person))

        # 3
        # insert all missing contacts in pipedrive persons
        return # TODO remove?
        persons, contacts, person_by_email, contact_by_email = get()
        count_contact = 0
        for contact in contacts:
            o = db.PipedriveOrganization.by_deltek_id(
                self.session, contact['ClientID']).first()
            if o is not None:
                continue

            # maybe in debug for all this verbosity?
            print("creating person")
            count_contact = count_contact + 1
            pprint.pprint(self.create_person(contact))
            break  # TODO REMOVE

        pprint.pprint(
            'would create {} contacts'.format(count_contact))


if __name__ == "__main__":
    config_file = sys.argv[1]
    ImportContact(config_file).main()


"""
pipedrive organizations:
 {'active_flag': True,
  'activities_count': 0,
  'add_time': '2019-11-14 16:29:07',
  'address': '2343 Avenue de la Salle, Montreal, QC, Canada',
  'address_admin_area_level_1': 'Québec',
  'address_admin_area_level_2': 'Communauté-Urbaine-de-Montréal',
  'address_country': 'Canada',
  'address_formatted_address': '2343 Avenue de la Salle, Montréal, QC H1V 2K9,'
                               'Canada',
  'address_locality': 'Montréal',
  'address_postal_code': 'H1V 2K9',
  'address_route': 'Avenue de la Salle',
  'address_street_number': '2343',
  'address_sublocality': 'Mercier-Hochelaga-Maisonneuve',
  'address_subpremise': '',
  'category_id': None,
  'cc_email': 'thinkwell-sandbox-29104d@pipedrivemail.com',
  'closed_deals_count': 0,
  'company_id': 7057330,
  'country_code': None,
  'done_activities_count': 0,
  'email_messages_count': 0,
  'files_count': 0,
  'first_char': 'd',
  'followers_count': 1,
  'id': 1,
  'label': None,
  'last_activity_date': None,
  'last_activity_id': None,
  'lost_deals_count': 0,
  'name': 'Dunder Mifflin',
  'next_activity_date': None,
  'next_activity_id': None,
  'next_activity_time': None,
  'notes_count': 0,
  'open_deals_count': 0,
  'owner_id': {'active_flag': True,
               'email': 'louis.lynch@evodev.ca',
               'has_pic': False,
               'id': 10608613,
               'name': 'Louis Lynch',
               'pic_hash': None,
               'value': 10608613},
  'owner_name': 'Louis Lynch',
  'people_count': 1,
  'picture_id': None,
  'reference_activities_count': 0,
  'related_closed_deals_count': 0,
  'related_lost_deals_count': 0,
  'related_open_deals_count': 0,
  'related_won_deals_count': 0,
  'undone_activities_count': 0,
  'update_time': '2019-11-21 19:35:47',
  'visible_to': '3',
  'won_deals_count': 0}

deltek firms:
 {'AjeraSync': 'N',
  'AlaskaNative': 'N',
  'AnnualRevenue': 0.0,
  'AvailableForCRM': 'Y',
  'BillingAddress1': 'Asia TV LTD.',
  'BillingAddress2': 'Hygeia Building, 3rd Floor',
  'BillingAddress3': '66/68 College Rd',
  'BillingAddress4': '',
  'BillingCity': 'Harrow HA1 BE',
  'BillingCountry': '',
  'BillingEmail': '',
  'BillingFax': '',
  'BillingPhone': '',
  'BillingState': '',
  'BillingZip': '',
  'Category': '',
  'Client': '2664',
  'ClientID': 'A39F5877121E49E4B1B18253F7A89CC4',
  'ClientInd': 'Y',
  'Competitor': 'N',
  'CreateDate': '2016-11-01T22:47:17.190',
  'CreateUser': 'KIRSTENT',
  'CreateUserName': 'Kirsten Taylor-Hall',
  'CurrentStatus': '',
  'CustCNClientName': '',
  'CustCNVendorName': '',
  'CustCompany': 'N',
  'CustDRIVClient': 'N',
  'CustFirmName': '',
  'CustYearClientAdded': '',
  'CustomCurrencyCode': 'USD',
  'DisabledVetOwnedSmallBusiness': 'N',
  'DisadvBusiness': 'N',
  'EightA': 'N',
  'Employees': 0,
  'ExportInd': 'N',
  'FedID': '',
  'GovernmentAgency': 'N',
  'HBCU': 'N',
  'HUBZone': 'N',
  'HasHierarchy': 0,
  'HasPhoto': 0,
  'IQID': '',
  'Incumbent': 'N',
  'Invoice': '',
  'InvoiceUnpaid': '',
  'Memo': '',
  'MinorityBusiness': 'N',
  'ModDate': '2016-11-01T22:47:17.190',
  'ModUser': 'KIRSTENT',
  'ModUserName': 'Kirsten Taylor-Hall',
  'Name': 'Zee TV Europe',
  'Org': '',
  'OrgName': '',
  'OutstandingAR': '',
  'Owner': '',
  'ParentID': '',
  'ParentLevel1': '',
  'ParentLevel2': '',
  'ParentLevel3': '',
  'ParentLevel4': '',
  'ParentName': '',
  'PaymentAddress1': '',
  'PaymentAddress2': '',
  'PaymentAddress3': '',
  'PaymentAddress4': '',
  'PaymentCity': '',
  'PaymentCountry': '',
  'PaymentEmail': '',
  'PaymentFax': '',
  'PaymentPhone': '',
  'PaymentState': '',
  'PaymentZip': '',
  'PhotoModDate': '',
  'PrimaryAddress1': 'Asia TV LTD.',
  'PrimaryAddress2': 'Hygeia Building, 3rd Floor',
  'PrimaryAddress3': '66/68 College Rd',
  'PrimaryAddress4': '',
  'PrimaryCity': 'Harrow HA1 BE',
  'PrimaryCountry': '',
  'PrimaryEmail': '',
  'PrimaryFax': '',
  'PrimaryPhone': '',
  'PrimaryState': '',
  'PrimaryZip': '',
  'PriorWork': 'N',
  'QBOID': '',
  'QBOLastUpdated': '',
  'ReadyForApproval': 'Y',
  'ReadyForProcessing': 'N',
  'RecentPRRole': 'sysOwner',
  'RecentPRRoleDescription': 'Owner',
  'RecentWBS1': '0246OPP2016',
  'RecentWBSName': 'Zee TV India Theme Park - London',
  'Recommend': 'N',
  'SFID': '',
  'SFLastModifiedDate': '',
  'SmallBusiness': 'N',
  'SocioEconomicStatus': '',
  'SortName': '',
  'Specialty': '',
  'SpecialtyType': '',
  'Status': 'A',
  'TLInternalKey': '',
  'TLSyncModDate': '',
  'TopTPContactID': '3DB0982CEE4F4EC69633CE78627F7ED0',
  'TopTPCreateEmployee': '001027',
  'TopTPCreateUserName': 'KIRSTENT',
  'TopTPStartDate': '2017-01-27T19:30:26.997',
  'TopTPSubject': 'Update',
  'Type': 'IP',
  'TypeOfTIN': '',
  'VName': '',
  'Vendor': '',
  'VendorInd': 'N',
  'VetOwnedSmallBusiness': 'N',
  'WebSite': '',
  'WomanOwned': 'N',
  'desc_CustFirmName': '',
  'emOwner': '',
  'emOwnerEmail': '',
  'emOwnerLocation': '',
  'emOwnerPhone': '',
  'emOwnerTitle': '',
  'emOwnerfl': '',
  'emParentfl': ''},
"""
