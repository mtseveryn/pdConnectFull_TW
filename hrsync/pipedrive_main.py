from hrsync import deltek
from hrsync.config import Config
from pipedrive.client import Client

import datetime
import dateutil.parser
import pprint
import requests
import uuid
import sys

from hrsync import db

from html.parser import HTMLParser


def sync_organization(context, pipedrive_organization, client_id):
    deltek_impl = context.deltek_impl

    # deltek info
    firm = {}
    firm["ClientID"] = client_id
    #firm["Client"] = ""
    #firm["ClientName"] = pipedrive_organization['name']
    #firm["Company"] = pipedrive_organization['name']
    #firm["FirmName"] = pipedrive_organization['name']

    firm["Name"] = pipedrive_organization['name']
    #firm["CustFirmName"] = pipedrive_organization['name']
    #firm["dest_CustFirmName"] = pipedrive_organization['name']
    firm["CustCNClientName"] = pipedrive_organization['name']
    #firm["Vendor"] = ''
    #firm["VName"] = ''
    firm['ClientInd'] = 'Y'

    #pprint.pprint(deltek_impl.get_metadata_firm_required())
    #pprint.pprint(deltek_impl.get_firm(client_id))
    print("updating firm: ", client_id, firm['Name'])
    deltek_impl.update_firm(firm, client_id)

    # update address
    update_deltek_firm_address = pipedrive_organization['address']
    address = {}
    if pipedrive_organization['address_street_number'] is None:
        address['Address1'] = pipedrive_organization['address_street_number']
    else:
        address['Address1'] = "{} {}".format(
            pipedrive_organization['address_street_number'],
            pipedrive_organization['address_route'])
    address['City'] = pipedrive_organization['address_locality']

    if pipedrive_organization['address_admin_area_level_1']:
        address['StateDescription'] = \
            pipedrive_organization['address_admin_area_level_1']

    if pipedrive_organization['address_postal_code']:
        address['Zip'] = pipedrive_organization['address_postal_code']

    address['Country'] = pipedrive_organization['address_country']
    if address['Country'] == 'South Korea':
        address['Country'] = "Korea, Republic of"
    # indicate that this is the current address
    address['PrimaryInd'] = "Y"

    if address['Address1'] is None:
        del address['Address1']

    if address['City'] is None:
        address['City'] = "Unknown"

    # get the id of the PrimaryInd alway
    try:
        primary_id = [a["CLAddressID"] for a in deltek_impl.get_firm_addresses(client_id) if a['PrimaryInd'] == "Y"]
        if len(primary_id) == 1:
            address['CLAddressID'] = primary_id[0]
    except:
        pass

    if address['Country'] is None:
        address['Country'] = "Unknown"

    print(address)
    deltek_impl.create_firm_address(address, client_id)

    #deltek_impl.get_contact("2f6b3558-831a-41b4-956e-98b01053493d")
    #pprint.pprint(deltek_impl._send("https://vantagepointpreview.deltekfirst.com/ThinkwellGroup/api/firm/8e20a94e0a4a11eaae5cc705cee689cc/address/2f6b3558-831a-41b4-956e-98b01053493d", method="POST", params=address))
    #pprint.pprint(deltek_impl._send("https://vantagepointpreview.deltekfirst.com/ThinkwellGroup/api/contact/2f6b3558-831a-41b4-956e-98b01053493d", method="POST", params=address))
    return firm, address


def filter_label(objects, label):
    for obj in objects:
        if "label" in obj and obj["label"] == label:
            return obj["value"]
    return ""


def sync_person(context, pipedrive_person, client_id, contact_id):
    contact = {}
    contact["ClientID"] = client_id
    if contact_id is not None:
        contact["ContactID"] = contact_id
    job_title = pipedrive_person[
        context.config.pipedrive_field_id_job_title]

    if job_title is not None:
        contact["Title"] = job_title[:50]

    contact["FirstName"] = pipedrive_person["first_name"]
    contact["LastName"] = pipedrive_person["last_name"] or "unknown"
    contact["Phone"] = filter_label(pipedrive_person["phone"], "work")[:20]
    contact["Email"] = filter_label(pipedrive_person["email"], "work")
    contact["PrimaryInd"] = "Y"
    try:
        context.deltek_impl.update_contact(contact, contact_id)
    except:
        import sys
        import traceback
        traceback.print_exc(file=sys.stdout)
        print(contact)
        print(e)
        raise e
    return contact


def create_firm(context, pipedrive_organization):
    client_id = str(uuid.uuid4()).replace('-', '')
    return sync_organization(context, pipedrive_organization, client_id)


def create_contact(context, pipedrive_person):
    client_id = None
    org_id = pipedrive_person['org_id']
    if org_id is not None and org_id['value'] is not None:
        client_id = db.PipedriveOrganization.by_pipedrive_id(
            context.session,
            org_id['value']).first().deltek_id
    contact_id = str(uuid.uuid4()).replace('-', '')
    return sync_person(context, pipedrive_person, client_id, contact_id)


def get_deltek_project_type(context):
    data = context.deltek_client.get_codetable('ProjectType')
    project_types = {}
    for element in data:
        code = element['Code']
        description = element['Description']
        project_types[description] = code
    return project_types


def get_contact_id(context, deal):
    person_id = deal['person_id']['value'] \
        if deal['person_id'] is not None else None

    if person_id is None:
        return None

    record = db.PipedrivePerson.by_pipedrive_id(
        context.session, person_id).first()

    person = context.pipedrive_client.persons.get_person(person_id)['data']

    # if the result is None we could create the person
    if record is None:
        create_contact(context, person)
        contact_id = db.PipedrivePerson.by_pipedrive_id(
            context.session, person_id).first().deltek_id

    else:
        contact_id = record.deltek_id
        client_id = None
        if person['org_id'] is not None:
            organization_id = person['org_id']['value']
            client_id = db.PipedriveOrganization.by_pipedrive_id(
                context.session,
                organization_id).first().deltek_id

        sync_person(context, person, client_id, contact_id)

    return contact_id


def get_client_id(context, deal):
    organization_id = deal['org_id']['value'] \
        if deal['org_id'] is not None else None

    if organization_id is None:
        return None

    record = db.PipedriveOrganization.by_pipedrive_id(
        context.session, organization_id).first()

    organization = context.pipedrive_client.organizations\
        .get_organization(organization_id)['data']

    if record is None:
        create_firm(context, organization)
        client_id = db.PipedriveOrganization.by_pipedrive_id(
            context.session, organization_id).first().deltek_id
    else:
        sync_organization(context, organization, organization_id)
        client_id = record.deltek_id


    return client_id


def deltek_probability(p):
    possible_values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 99]
    p = int(p)
    if p in possible_values:
        return p

    return round(p / 5.) * 5


def sync_deal(context, promo_deltek_id, regular_deltek_id, data, creating=False):
    pipedrive_impl = context.pipedrive_impl
    deltek_impl = context.deltek_impl

    project = {}
    #project['Fee'] = float(data['value'])
    # Is this the compensation?
    project['Revenue'] = float(data['value'])
    if data['probability'] is not None:
        project['Probability'] = deltek_probability(data['probability'])

    # point 22
    #project['Currency'] = data['currency']
    project["BillingCurrencyCode"] = data['currency']
    project["ProjectCurrencyCode"] = data['currency']

    project['EstStartDate'] = data[
        context.config.pipedrive_field_id_estimated_project_start]
    project['EstCompletionDate'] = data[
        context.config.pipedrive_field_id_estimated_project_end]
    project['PlanStartDate'] = data[
        context.config.pipedrive_field_id_estimated_project_start]
    project['PlanEndDate'] = data[
        context.config.pipedrive_field_id_estimated_project_end]

    if project['EstStartDate'] is None: del project['EstStartDate']
    if project['EstCompletionDate'] is None: del project['EstCompletionDate']
    if project['PlanStartDate'] is None: del project['PlanStartDate']
    if project['PlanEndDate'] is None: del project['PlanEndDate']

    pipedrive_supervisor = {
        "Adam Lajoie": "AL1705",
        "Amin Rashmani": "ME0001",
        "Craig Hanna": "001002",
        "Empiy Yang": "EY0718",
        "Francois Bergeron": "001001",
        "Francois Perron": "FP0001",
        "Gabrielle Maryse Bucaya": "ML0149",
        "Garron Rodgers": "010474",
        "Gladys Dastas": "ME0015",
        "Hugues Sweeney": "ML0142",
        "Jesse Cannady": "010470",
        "Joe Zenas": "001004",
        "Peden Bhutia": "ME0002",
        "Robert Fraser": "20010",
        "Seth Harrington": "010377",
        "Tina Blankeney": "ML0126",
        "ffang@thinkwellgroup.com": "FF0715"
    }
    supervisor = pipedrive_supervisor.get(data['owner_name'])
    # TODO if none we should check in Bamboo? or get names/employeeNumbers from
    # deltek.
    if supervisor is not None:
        # point 24
        #project['Supervisor'] = supervisor
        project["BusinessDeveloperLead"] = supervisor


    # Origin / Source
    key = context.config.pipedrive_field_id_origin
    id = data[key]
    if id is not None:
        source = context.deal_custom_fields_options[key][int(id)]
        if source is not None:
            project['Source'] = source

    #project['Stage'] = data['status']
    """
    $ python -m hrsync -pc prod.ini pipedrive-get '/stages' | jq '.data[] | ((.id|tostring) + ": " +  .name)'
    "57: TWG Internal"
    "60: 1st Conversation"
    "77: Ongoing Conversations"
    "61: Proposal Due"
    "62: Proposal Sent"
    "63: Negotiations"
    "65: Contracting"
    "76: Deep Archive (periodic touch-points)"


    $ python -m hrsync -pc prod.ini deltek-get '/codeTable/CFGProjectStage' | jq '.[] | (.Code + ": " + .Description)'
    "Vetting: 1%"
    "RFP/Compet: 10%"
    "RFP/SOLE: 20%"
    "PropSubCOM: 30%"
    "PropSubSOL: 40%"
    "ActiveComm: 50%"
    "ModReq: 60%"
    "Accepted: 70%"
    "TWGSUBLOA: 80%"
    "Negotiate: 90%"
    "WON/LOA: 100%"
    "Pro Denied: 07"
    "Dead: 08"
    "Passed: 09"
    "T&M: 99 PM"
    "Denied: 09 Passed"
    "Outbound: 01 - Outbound"
    "Inbound: 02 - Inbound"
    "Proposal D: 03 - Proposal Due"
    "Proposal S: 04 - Proposal Sent"
    "In Negotia: 05 - Negotiations Started"
    "Contract: 06 - Contracting"
    "~WDEF~: 07 - Won"
    "Dormant: 08 - Dormant"
    "Lost: 09 - Lost"
    "Long: 00 - Long Leads"
    """

    # https://docs.google.com/spreadsheets/d/1P1EWaWZN5g3-ukP4Qg6-_oq7nlrdZebZxUczVDTau58/edit#gid=0
    stage_mapping = {
        54: 'Outbound',
        55: 'Outbound',
        56: 'Outbound',
        60: 'Inbound',
        77: 'Inbound',
        61: 'Proposal D',
        62: 'Proposal S',
        63: 'In Negotia',
        65: 'Contract',
        59: 'Dormant',
        70: 'Dormant',
        71: 'Dormant',
        72: 'Dormant',
        73: 'Dormant',
        74: 'Dormant',
        75: 'Dormant',
        76: 'Dormant',
        57: 'Long'
    }

    # force a stage in test.ini because the stage do not match with prod
    project["Status"] = "A"
    if context.config.force_deal_stage:
        project['Stage'] = context.config.force_deal_stage_value
    elif data['status'] == 'won':
        project['Stage'] = "~WDEF~"
    elif data['status'] == 'lost':
        project["Status"] = "I"
        project['Stage'] = "Lost"
    else:
        stage = stage_mapping.get(data['stage_id'])
        if stage is not None:
            project['Stage'] = stage

    if project.get('Stage') == "Dormant":
        project["Status"] = "D"

    # $ python -m hrsync -pc prod.ini deltek-get '/organization'
    pipedrive_organization = {
        "Abu Dhabi": "AD:BIZ",
        "Beijing": "BJ:BIZ",
        "Hong Kong": "HK:BIZ",
        "Los Angeles": "US:BIZ",
        "Montreal": "ML:BIZ",
        "KSA": "SA:BIZ",
        "Health": "US:BIZ",
        "Joe Outbound Tracking": None,
        "Media": "US:MED",
        "TWG (Promo)": "US:PNR"
    }

    # python -m hrsync -pc test.ini deltek-get '/project/3' | grep Master
    key = context.config.pipedrive_field_id_lead_studio
    id = int(data[key])
    organization_id = context.deal_custom_fields_options[key][id]
    organization = pipedrive_organization.get(organization_id)

    if organization is None:
        raise Exception("Can't synchronize organization {}".format(organization_id))

    project['Org'] = organization
    if context.config.force_organization:
        project['Org'] = context.config.force_organization

    # region is from lead studio
    key = context.config.pipedrive_field_id_lead_studio
    id = data[key]
    if id is not None:
        region = context.deal_custom_fields_options[key][int(id)]
        if region is not None and region != "TWG (Promo)":
            project['CustDivision'] = region

    # Custom fields
    team_drive_link = data[context.config.pipedrive_field_id_team_drive_link]
    if team_drive_link is not None and team_drive_link.strip():
        project['CustTeamDriveLink'] = team_drive_link

    # limit to 255 but add ... at the end of the field.
    short_desc = data[context.config.pipedrive_field_id_short_description] or ''
    if len(short_desc) > 250:
        project['CustShortDescription'] = "{}...".format(short_desc[0:250])
    else:
        project['CustShortDescription'] = short_desc[0:255]

    mastercode = \
        data[context.config.pipedrive_field_id_project_number_master_code]
    project['CustMasterCode'] = mastercode

    phase = None
    key = context.config.pipedrive_field_id_project_number_phase
    if data[key]:
        value = data[key]
        if "," in value:
            value = value.split(",")[0]
        id = int(value)
        phase = context.deal_custom_fields_options[key][id]
        phase = phase.replace(".", "")
        project['CustPhase'] = phase

    # ProjectType
    '''
    $ python -m hrsync -pc prod.ini pipedrive-get /dealFields
     "name": "Project Type",
            "options": [
                {
                    "id": 72,
                    "label": "Corporate Brand Experiences"
                },
                {
                    "id": 73,
                    "label": "Cultural Experiences"
                },
                {
                    "id": 74,
                    "label": "Live Shows & Events"
                },
                {
                    "id": 75,
                    "label": "Mixed-Use Developments"
                },
                {
                    "id": 76,
                    "label": "Museum & Exhibits"
                },
                {
                    "id": 77,
                    "label": "Theme Park & Resorts"
                },
                {
                    "id": 78,
                    "label": "Thinkwell Health"
                },
                {
                    "id": 79,
                    "label": "TW Media"
                }
            ],


    $ python -m hrsync -pc test.ini deltek-get /codeTable/ProjectType
    Parameter pipedrive_field_id_project_type is invalid and will be ignored.
    [
    {
        "Code": "01",
        "Description": "Theme Park & Resorts",
        "Seq": 0
    },
    {
        "Code": "02",
        "Description": "Museum & Exhibits",
        "Seq": 1
    },
    {
        "Code": "03",
        "Description": "Urban Attractions",
        "Seq": 2
    },
    {
        "Code": "04",
        "Description": "Live Shows & Events",
        "Seq": 3
    },
    {
        "Code": "05",
        "Description": "Mixed-Use Developments",
        "Seq": 4
    },
    {
        "Code": "06",
        "Description": "Cultural Experiences",
        "Seq": 5
    },
    {
        "Code": "08",
        "Description": "Corporate Brand Experiences",
        "Seq": 6
    },
    {
        "Code": "07",
        "Description": "TW Media",
        "Seq": 7
    },
    {
        "Code": "011",
        "Description": "New Type/Not Applicable",
        "Seq": 8
    }
    '''
    key = context.config.pipedrive_field_id_project_type
    value = data[key]
    if value:
        if "," in value:
            value = value.split(",")[0]
        id = int(value)
        deltek_project_type = get_deltek_project_type(context)
        project_type = deltek_project_type.get(context.deal_custom_fields_options[key][id])
        if project_type:
            project['ProjectType'] = project_type

    # fix contact and client id
    project['ClientID'] = get_client_id(context, data)
    project['ContactID'] = get_contact_id(context, data)

    # Project Location
    key = context.config.pipedrive_field_id_project_location
    value = data[key]
    if value:
        if "," in value:
            value = value.split(",")[0]
        id = int(value)
        project_location = context.deal_custom_fields_options[key][id]
        project['CustRegionGlobal'] = project_location

        # pipedrive to deltek
        # point 23
        locations = {
            "AFRICA": None,
            "ANTARTICA": None,
            "ASIA": None,
            "AUSTRALIA": None,
            "EUROPE": None,
            "MIDDLE-EAST": None,
            "Middle-East SAUDI ARABIA": "Saudi Arabia",
            "North America - USA": "United States",
            "North America - CANADA": "Canada",
            "SOUTH AMERICA": None,
            "OTHER": None
        }
        country = locations.get(project_location)
        if country is not None:
            project["Country"] = country

    # here we have to save two projects
    wsbkey = promo_deltek_id
    project["WBS1"] = wsbkey

    def format_number():
        numbers = []
        if mastercode:
            numbers.append(mastercode)
        if phase:
            numbers.append(phase)
        return ".".join(numbers)

    def format_title():
        title = []
        number = format_number()
        if number:
            title.append(number)

        title.append(data['title'])
        return " - ".join(title)

    # add promo in
    title = format_title()
    project['Name'] = "{} PROMO".format(title)
    # these are mandatory fields
    # N = Regular project; P = Promotional
    project["ChargeType"] = 'P'
    # N - None; W - Warning; E - Error
    project["BudgetedFlag"] = "W"
    # 'Codes': {'B': 'Budget Worksheet', 'P': 'Project Planning'},
    project["BudgetSource"] = 'B'

    # only if project is created
    creating = False
    if creating:
        project["WBS1ReadyForProcessing"] = "N"
        project["ReadyForApproval"] = "N"
        project["ReadyForProcessing"] = "N"
    updated_promo = deltek_impl.update_project(project, wsbkey)[0]

    # for regular we dont mark them as ready for processing
    if creating:
        project["WBS1ReadyForProcessing"] = "N"
        project["ReadyForApproval"] = "N"
        project["ReadyForProcessing"] = "N"

    equity_project = None
    key = context.config.pipedrive_field_id_equity_project
    if data[key]:
        id = int(data[key])
        equity_project = context.deal_custom_fields_options[key][id]

    # equity project mean we only creates a promo for it not the regular project
    if equity_project is not None and equity_project.lower() == "yes":
        return updated_promo

    # If we have TWG (Promo) we dont open the regular project.
    if organization == "US:PNR":
        return updated_promo

    project['Name'] = "{}".format(title)
    project["SiblingWBS1"] = promo_deltek_id
    wsbkey = regular_deltek_id
    project["WBS1"] = wsbkey
    project["ChargeType"] = 'R'


    pipedrive_organization_regular = {
        "Abu Dhabi": "AD:PRO",
        "Beijing": "BJ:PRO",
        "Hong Kong": "HK:PRO",
        "Los Angeles": "US:PDM",
        "Montreal": "ML:PRO",
        "KSA": "SA:PRO",
        "Health": "US:HLT",
        "Joe Outbound Tracking": None,
        "Media": "US:MED"
    }
    if not context.config.force_organization:
        project['Org'] = pipedrive_organization_regular.get(organization_id)
    deltek_impl.update_project(project, wsbkey)

    # Here we should open one regular for each support studio:
    key = context.config.pipedrive_field_id_support_studio
    ids = data[key]
    if ids:
        for id in str(ids).split(","):
            region = context.deal_custom_fields_options[key][int(id)]
            organization = pipedrive_organization_regular[region]
            org = organization.split(":")[0]

            wsbkey = "{}-{}".format(regular_deltek_id, org)
            project['CustDivision'] = region
            project['Name'] = "{} ({})".format(title, org)
            #project["SiblingWBS1"] = promo_deltek_id
            project["WBS1"] = wsbkey
            project["ChargeType"] = 'R'

            # no compensation for support studio
            if "Revenue" in project:
                del project["Revenue"]
            # project["Revenue"] = 0.0

            deltek_impl.update_project(project, wsbkey)

    return updated_promo


def sync_activity(deltek_impl, deltek_id, data):
    activity = {}
    activity['ActivityID'] = 'pipedrive-activity-{}'.format(data['id'])
    activity['WBS1'] = deltek_id
    activity['Subject'] = 'pipedrive: {}'.format(data['subject'])

    # In terms of Activities, we need to know when the Deal is Created,
    # Owner of the Deal, Notes, activities
    # (Calls, Meetings, Emails, Files - Google Drive)
    # TODO owner of the deal? is it en employee?

    # does not seems to be supported. we might put that into notes, but Francois
    # Bergerons does not insist on having the activities.

    activity['Notes'] = data['note'] or ""

    # python -m hrsync -pc test.ini deltek-get /codeTable/CFGActivityType
    deltek_types = {
        1: "EMail",
        2: "Mailing",
        3: "Meeting",
        4: "Merge",
        6: "Phone Call",
        7: "Task",
        8: "Touchpoint",
        9: "Note"
    }
    # left pipedrive: right deltek
    pipedrive_type = {
        "call": "Phone Call",
        "meeting": "Meeting",
        "task": "Task",
        "deadline": "Touchpoint",
        "email": "EMail",
        "lunch": "Meeting"
    }
    activity['Type'] = pipedrive_type[data['type']]
    activity['CreateDate'] = data['add_time']

    start_date_str = "{} {}".format(data['due_date'], data['due_time'])
    start_date = dateutil.parser.parse(start_date_str)
    activity['StartDate'] = start_date.isoformat()

    duration_str = data['duration']
    if ":" in duration_str:
        duration = datetime.timedelta(
            hours=int(duration_str.split(":")[0]),
            minutes=int(duration_str.split(":")[1]))
        activity['EndDate'] = (start_date + duration).isoformat()
    else:
        activity['EndDate'] = start_date.isoformat()

    deltek_impl.update_activity(activity)


def strip_html(text):
    parts = []
    parser = HTMLParser()
    parser.handle_data = parts.append
    parser.feed(text)
    return ''.join(parts)


def sync_note(deltek_impl, deltek_id, data):
    note = {}
    note['ActivityID'] = 'pipedrive-note-{}'.format(data['id'])
    note['WBS1'] = deltek_id
    content = data['content'] or ""
    note['Subject'] = strip_html(content)
    note['Notes'] = content
    note['Type'] = "Note"

    add_time_str = data['add_time']
    add_time = datetime.datetime.strptime(add_time_str, '%Y-%m-%d %H:%M:%S')
    note['StartDate'] = add_time.isoformat()
    note['EndDate'] = add_time.isoformat()

    deltek_impl.update_activity(note)

def sync_email(deltek_impl, deltek_id, data):
    note = {}
    note['ActivityID'] = 'pipedrive-email-{}'.format(data['id'])
    note['WBS1'] = deltek_id
    subject = data['subject'] or ""
    body_url = data['body_url']
    content = requests.get(body_url).text
    note['Subject'] = strip_html(subject)
    note['Notes'] = content
    note['Type'] = "EMail"

    add_time_str = data['add_time']
    #    2020-05-27T07:48:07.000Z
    add_time = datetime.datetime.strptime(add_time_str, '%Y-%m-%dT%H:%M:%S.000Z')
    note['StartDate'] = add_time.isoformat()
    note['EndDate'] = add_time.isoformat()

    deltek_impl.update_activity(note)


def main(config_file):
    config = Config.from_file(config_file)
    #print(config)
    if config.dry_run:
        print("EXITING - DRY RUN MODE")
        return

    db.init(url=config.sqlalchemy_url)

    client = Client(domain=config.pipedrive_api_url)
    client.set_api_token(config.pipedrive_api_token)

    activities_response = client.activities.get_all_activities()
    persons_response = client.persons.get_all_persons()
    organizations_response = client.organizations.get_all_organizations()
    deals_response = client.deals.get_all_deals()

    deltek_impl = deltek.DeltekApi(config)

    context = object()
    context.deltek_impl = deltek_impl
    context.session = db.session()

    def debug_pipedrive():
        print("# Activities")
        pprint.pprint(activities_response)
        print()

        print("# Persons")
        pprint.pprint(persons_response)
        print()

        print("# Organizations")
        pprint.pprint(organizations_response)
        print()

        print("# Deals")
        pprint.pprint(deals_response)
        print()

    def debug_deltek():
        print("# debug deltek")

        # todo filter firm and project with id and ModDate,ModUser
        print("\n\n# Activities")
        pprint.pprint(deltek_impl.get_activities(extra_args="?limit=1"))
        print("\n\n# Contact")
        pprint.pprint(deltek_impl.get_contact('A7074D7216F14673BBCFE70C921755B4'))
        print("\n\n# Firm")
        pprint.pprint(deltek_impl.get_firm("A0BFCF2BE7594B11903AC0825912B9CC"))
        print("\n\n# Employees")
        pprint.pprint(deltek_impl.get_employees(extra_args="?limit=1"))
        return

        pprint.pprint(deltek_impl.get_projects(
            extra_args=
                "?fieldFilter=WBS1,WBS2,WBS3,WBSNumber,ModDate,ModUser"))
        pprint.pprint(deltek_impl.get_contacts(
            extra_args=
                "?fieldFilter=ClientID,ContactID,Email,ModDate,ModUser"))
        pprint.pprint(deltek_impl.get_employees(
            extra_args="?fieldFilter=Employee,EmployeeCompany,"
                "EmployeeCompanyName,Email,ModDate,ModUser"))
        pprint.pprint(deltek_impl.get_firms(
            extra_args="?fieldFilter=ClientID,ModDate,ModUser"))

        #pprint.pprint(deltek_impl.get_contacts(extra_args="?limt=1"))
        #pprint.pprint(deltek_impl.get_projects(extra_args="?limit=10"))
        #wbskey = "GESRS.02"
        #project = deltek_impl.get_project(wbskey)[0]


        # update the project...
        #pprint.pprint(deltek_impl.get_metadata_project())
        #pprint.pprint(project)
        name = "[SD] Google GMS Customer Experience CEN2"
        new_project = {
            'CLAddress': '...',
            'Name': name,
            'Level1Name': name
        }
        pprint.pprint(new_project)
        #deltek_impl.update_project(new_project, wbskey)

    #debug_pipedrive()
    #debug_deltek()

    """
    # organizations
    organization = organizations_response['data'][0]
    sync_organization(context, organization)

    # persons
    person = persons_response['data'][0]
    sync_person(context, person)
    """

    # deals
    # TODO put field id in the configuration file
    deals = client.deals.get_all_deals(
        params=dict(
            filter_id=config.pipedrive_filter_id_sync_deals))
    for deal in deals['data']:
        sync_deal(client, deltek_impl, deal)


if __name__ == "__main__":
    config_file = sys.argv[1]
    main(config_file)
