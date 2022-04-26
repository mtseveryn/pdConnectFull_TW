import json
import logging
import requests
import urllib.parse
import uuid

from hrsync.config import Config


log = logging.getLogger(__name__)


class DeltekCache:
    def __init__(self, employees_filename):
        self.employees_filename = employees_filename

    def get_employees(self):
        with open(self.employees_filename, 'r') as f:
            self.employees = json.load(f)
        return self.employees

    def get_employe(self, Employee, EmployeeCompany):
        # should we build employ key here from Employee and EmployeCompany?
        for employee in self.employees:
            if \
                    employee['Employee'] == Employee and \
                    employee['EmployeeCompany'] == EmployeeCompany:
                return employee
        return None

    def create_employe(self, Employee, EmployeeCompany):
        pass

    def update_employe(self, Employee, EmployeeCompany):
        pass


class DeltekApi:
    @staticmethod
    def token(config):
        """
        returns a dictionary that looks like this:
        {"access_token":"yokLe5JmsYcRagL9YTv2LUHxF8yND0Qexo8UzxxHGrnnq0RgpFNuafp71MZZ5j04m9kUStJBW-lX1L13N7FB4VyJy55oWTdu5Bjh-tGvLdMpYzXjc9L97eq9dJGhI6exHMC8-1rrPbcQh69kR63u4-PQmb0wR3n4PVr7vwleEVZrGlP_7mPmQZgXf9TsJm_K1SXmp0Oe-heg0l37qb_p97LkwURdykKBbWxvXZ6Eh8-mNW2PT4LTwnFHXRaFWa-4ZUxTy_C8l2RXiq-hUJ7AF8MFN5MvutyOd0nN-ovobtyLECqHhBsGF3cfVBRt4ZGkQLv0O4PvnEJ6xolS2xgSFLah7zPDBd0EObNE5qpgpw64RF9JuVAswBu-hAf3Dfsm","token_type":"bearer","expires_in":1799,"refresh_token":"HHPWIUl+zXss2Jwdx6oncBn9zmz/a+yhCHpXp0cLYJEzWWJwQL/EqO1/wqxPMnF9"}

        access_token - have to be used in every subsequent queries
        expires_in - is an expiration makerd in seconds
        refresh_token - is the value needed to refresh the token.
            It must be done before expiration
        """
        # url ecode all config
        url_encoded_config = {k: urllib.parse.quote(str(v), safe='')
                              for k, v in config.to_dict().items()}

        data = 'Username={deltek_username}&' \
            'Password={deltek_password}&' \
            'grant_type=password&' \
            'Integrated=N&database={deltek_database}&' \
            'Client_Id={deltek_client_id}&' \
            'client_secret={deltek_client_secret}' \
            .format(**url_encoded_config)

        headers = {
            'content-type': 'application/x-www-form-urlencoded'
        }
        url = '{deltek_api_url}/token'.format(**config.to_dict())
        response = requests.request(
            'POST', url,
            headers=headers,
            data=data,
            timeout=30)

        values = json.loads(response.text)
        return values

    def __init__(self, config):
        self.config = config
        self._token = None

    def get_access_token(self):
        # TODO expire _token if expiry is passed
        if self._token is None:
            self._token = DeltekApi.token(self.config)

        try:
            access_token = self._token["access_token"]
        except Exception as e:
            print(self._token)
            raise e

        return access_token

    def _employekey(self, Employee, EmployeeCompany):
        return urllib.parse.quote(
            "{Employee}|{EmployeeCompany}".format(
                Employee=Employee, EmployeeCompany=EmployeeCompany),
            safe='')

    def get_activity(self, activity_id):
        """
        ContactID: id of contact
        ClientID: firm id
        """
        url = '{deltek_api_url}/activity/{contact_id}'.format(
            activity_id=activity_id,
            **self.config.to_dict())
        return self._send(url)

    def get_activities(self, extra_args=""):
        #extra_args = extra_args or "&fieldFilter=PrincipalTitle,WBSNumber"

        url = '{deltek_api_url}/activity{extra_args}'.format(
            extra_args=extra_args,
            **self.config.to_dict())
        return self._send(url)

    def get_contacts(self, extra_args=""):
        #extra_args = extra_args or "&fieldFilter=PrincipalTitle,WBSNumber"

        url = '{deltek_api_url}/contact{extra_args}'.format(
            extra_args=extra_args,
            **self.config.to_dict())
        return self._send(url)

    def get_contact(self, contact_id):
        """
        ContactID: id of contact
        ClientID: firm id
        """
        url = '{deltek_api_url}/contact/{contact_id}'.format(
            contact_id=contact_id, **self.config.to_dict())
        return self._send(url)

    def get_employees(self, extra_args=""):
        url = '{deltek_api_url}/employee{extra_args}'.format(
            extra_args=extra_args,
            **self.config.to_dict())
        return self._send(url)

    def get_employee(self, Employee, EmployeeCompany):
        employekey = self._employekey(Employee, EmployeeCompany)
        url = '{deltek_api_url}/employee/{employekey}'.format(
            deltek_api_url=self.config.deltek_api_url, employekey=employekey)
        return self._send(url)

    def get_firms(self, extra_args=""):
        #extra_args = extra_args or "&fieldFilter=PrincipalTitle,WBSNumber"

        url = '{deltek_api_url}/firm{extra_args}'.format(
            extra_args=extra_args,
            **self.config.to_dict())
        return self._send(url)

    def get_firm(self, client_id):
        url = '{deltek_api_url}/firm/{client_id}'.format(
            client_id=client_id, **self.config.to_dict())
        return self._send(url)

    def get_firm_addresses(self, client_id):
        url = '{deltek_api_url}/firm/{client_id}/address'.format(
            client_id=client_id, **self.config.to_dict())
        return self._send(url)

    def get_projects(self, extra_args=""):
        extra_args = extra_args or "&fieldFilter=PrincipalTitle,WBSNumber"

        url = '{deltek_api_url}/project{extra_args}'.format(
            extra_args=extra_args,
            **self.config.to_dict())
        return self._send(url)

    def get_project(self, wbskey):
        url = '{deltek_api_url}/project/{wbskey}'.format(
            wbskey=wbskey, **self.config.to_dict())
        return self._send(url)

    def get_organizations(self):
        url = '{deltek_api_url}/organization'.format(**self.config.to_dict())
        return self._send(url)

    def _filter_metadata(self, fields, field_true):
        "DefaultValue can be [CURRENTCOMPANY] [TODAY] it should be replaced"
        CURRENTCOMPANY = "ML"
        TODAY = "2019-07-05"

        defaults = {}
        for field in fields['Fields']:
            name = field['FieldName']
            value = field['DefaultValue']
            type_ = field['FieldType']

            if not field[field_true]:
                continue

            #print(", ".join([name, value, type_]))
            if value == "[CURRENTCOMPANY]":
                value = CURRENTCOMPANY
            if value == "[TODAY]":
                value = TODAY
            if value == "[GUID]":
                value = str(uuid.uuid4()).replace("-", "")

            defaults[name] = value
        return defaults

    def get_metadata_contact(self):
        url = '{deltek_api_url}/metadata/contact'.format(
            **self.config.to_dict())
        return self._send(url)

    def get_metadata_contact_required(self):
        fields = self.get_metadata_contact()['CO']
        return self._filter_metadata(fields, 'Required')

    def get_metadata_contact_updateable(self):
        fields = self.get_metadata_contact()['CO']
        return self._filter_metadata(fields, 'Updateable')

    def get_metadata_employee(self):
        url = '{deltek_api_url}/metadata/employee'.format(
            **self.config.to_dict())
        return self._send(url)

    def get_metadata_employee_required(self):
        fields = self.get_metadata_employee()['EM']
        return self._filter_metadata(fields, 'Required')

    def get_metadata_employee_updateable(self):
        fields = self.get_metadata_employee()['EM']
        return self._filter_metadata(fields, 'Updateable')

    def get_metadata_firm(self):
        url = '{deltek_api_url}/metadata/firm'.format(
            **self.config.to_dict())
        return self._send(url)

    def get_metadata_firm_address(self):
        url = '{deltek_api_url}/metadata/firm'.format(
            **self.config.to_dict())
        result = self._send(url)
        return result['CLAddress']

    def get_metadata_firm_updateable(self):
        fields = self.get_metadata_firm()['Contacts']
        return self._filter_metadata(fields, 'Updateable')

    def get_metadata_firm_required(self):
        fields = self.get_metadata_firm()['Contacts']
        return self._filter_metadata(fields, 'Required')

    def get_metadata_project(self):
        url = '{deltek_api_url}/metadata/project'.format(
            **self.config.to_dict())
        return self._send(url)

    def get_metadata_project_updateable(self):
        fields = self.get_metadata_project()['PR']
        return self._filter_metadata(fields, 'Updateable')

    def get_metadata_project_required(self):
        fields = self.get_metadata_project()['PR']
        return self._filter_metadata(fields, 'Required')

    def create_employee(self, params):
        url = '{deltek_api_url}/employee'.format(
            deltek_api_url=self.config.deltek_api_url)

        params = self._filter_params(params)
        required = self.get_metadata_employee_required()
        for k, v in required.items():
            if k not in params:
                params[k] = required[k]

        # change None for empty string
        params = {k: (v or "") for k, v in params.items()}
        if "ChangeEmployee" in params:
            params["Employee"] = params["ChangeEmployee"]
        return self._send(url, method='POST', params=params)

    def create_firm_address(self, address, client_id):
        url = '{deltek_api_url}/firm/{client_id}/address'.format(
            client_id=client_id, **self.config.to_dict())

        params = address
        try:
            return self._send(url, method='POST', params=params)
        except:
            # when this happen it means that the address already exists
            return

    def update_activity(self, activity):
        activity_id = activity['ActivityID']
        params = activity
        put_url = '{deltek_api_url}/activity/{activity_id}'.format(
            activity_id=activity_id, **self.config.to_dict())
        post_url = '{deltek_api_url}/activity'.format(
            **self.config.to_dict())
        return self._send_put_post(put_url, post_url, params)


    def update_contact(self, contact, contact_id):
        params = contact
        put_url = '{deltek_api_url}/contact/{contact_id}'.format(
            contact_id=contact_id, **self.config.to_dict())
        post_url = '{deltek_api_url}/contact'.format(
            **self.config.to_dict())
        return self._send_put_post(put_url, post_url, params)

    def update_employee(self, employee, Employee, EmployeeCompany):
        employekey = self._employekey(Employee, EmployeeCompany)
        url = '{deltek_api_url}/employee/{employekey}'.format(
            deltek_api_url=self.config.deltek_api_url, employekey=employekey)

        updateable = self.get_metadata_employee_updateable()
        params = {}
        for k, v in updateable.items():
            if k in employee:
                params[k] = employee[k]

        return self._send(url, method='PUT', params=params)

    def update_firm(self, firm, client_id):

        updateable = self.get_metadata_firm_updateable()
        params = {}
        for k, v in updateable.items():
            if k in firm:
                params[k] = firm[k]

        # TODO remove:
        params = firm

        put_url = '{deltek_api_url}/firm/{client_id}'.format(
            client_id=client_id, **self.config.to_dict())
        post_url = '{deltek_api_url}/firm'.format(
                **self.config.to_dict())
        return self._send_put_post(put_url, post_url, params)

    def update_project(self, project, wbskey):
        url = '{deltek_api_url}/project/{wbskey}'.format(
            wbskey=wbskey, **self.config.to_dict())

        #updateable = self.get_metadata_project_updateable()
        #params = {}
        #for k, v in updateable.items():
        #    if k in project:
        #        params[k] = project[k]
        params = project

        put_url = '{deltek_api_url}/project/{wbskey}'.format(
            wbskey=wbskey, **self.config.to_dict())
        post_url = '{deltek_api_url}/project'.format(
            **self.config.to_dict())
        return self._send_put_post(put_url, post_url, params)

    def get_metadata(self, codeTable):
        url = '{deltek_api_url}/metadata/codeTable/{codeTable}'.format(
            codeTable=codeTable, **self.config.to_dict())
        return self._send(url)

    def get_codetable(self, codeTable):
        url = '{deltek_api_url}/codeTable/{codeTable}'.format(
            codeTable=codeTable, **self.config.to_dict())
        return self._send(url)

    def _filter_params(self, params):
        return {k: v for k, v in params.items() if v is not None}

    def _send(self, url, method='GET', params=None):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(self.get_access_token())
        }

        status_code = None
        response = None
        n = 0
        while status_code not in [200, 201, 202, 500]:
            if n == 1:
                log.error("tried to reach '{}' with method '{}' "
                          "but it failed {} times"
                          .format(url, method, n))
                log.error("response.status_code: {}"
                          .format(response.status_code))
                log.error("response.text: {}"
                          .format(response.text))
                raise Exception(response.text)
            response = requests.request(
                method, url, headers=headers, data=json.dumps(params),
                allow_redirects=False, timeout=120)
            status_code = response.status_code
            n = n + 1

        """
        # very often this anoying thing happen
        ipdb> response.status_code
        401
        ipdb> response.text
        '{"Message":"Session is invalid or timed out"}'
        """
        return json.loads(response.text)

    def _send_put_post(self, put_url, post_url, params):
        try:
            return self._send(put_url, method='PUT', params=params)
        except Exception as e1:
            try:
                return self._send(post_url, method='POST', params=params)
            except Exception as e2:
                e2_msg = json.loads(str(e2)).get('Message')
                if e2_msg == "":
                    raise e1
                raise e2


if __name__ == "__main__":
    config = Config()
    token = DeltekApi.token(config)
    access_token = token["access_token"]
    print(access_token)
