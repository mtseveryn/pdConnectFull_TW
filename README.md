Back up Copy from Original Source -- Not cloned to Local - For that see PDConnect Repo

# Usage:
main:
    dump bamboo employe
    dump bamboo changes
    dump deltek employe
    diff [-f,--full]
    sync [-y,--yes]

    [-c,--config=config.ini]

example:
    python -m hrsync -c test.ini dump-bamboo-employee-changes


# APIs documentation
https://docs.google.com/document/d/1yxTvZsCKUDi81mUFvx6YMjSbjxdZn8qM1joM-GlfLRU/edit#


# BambooHR
https://thinkwellgroupsandbox.bamboohr.com
Username:  fbergeron@thinkwellgroup.com
Password: Bamboo1234


Creating a API Key:
https://help.quantumworkplace.com/article/1119-creating-a-bamboohr-api-key-for-integration

API Documentation: https://www.bamboohr.com/api/documentation/employees.php

API user
user: Thinkwell API
email: louis.lynch@evodev.ca
password: B5364376-9cf0-11e9-bfe3-839a72ad3df6

API Key name: hrsync
API key: f1d05448ffa9b66e80def5e804df337ac0f6d770
Subdomain: thinkwellgroupsandbox

Python BambooHR api:
https://pypi.org/project/PyBambooHR/
pip install PyBambooHR

```python
from PyBambooHR import PyBambooHR

bamboo = PyBambooHR(subdomain='yoursub', api_key='yourapikeyhere')

employees = bamboo.get_employee_directory()
```


# Deltek
https://vantagepointpreview.deltekfirst.com/ThinkwellGroup/app/
DaltW
Deltek1234

API Documentation: https://documenter.getpostman.com/view/4108327/RVu7ETjY?version=latest

API
Client_Id=MJdeWdVPU00UtdUJN8tP0g98IEjM/sMkUDXFnUveqA8=
client_secret=070fe6d88570477caa069b2713ca24c1
url=https://vantagepointpreview.deltekfirst.com/ThinkwellGroup/api

This command returns an authentification token
```bash
curl -v -X POST https://vantagepointpreview.deltekfirst.com/ThinkwellGroup/api/token -H 'content-type: application/x-www-form-urlencoded' -d 'Client_Id=MJdeWdVPU00UtdUJN8tP0g98IEjM%2FsMkUDXFnUveqA8%3D&client_secret=070fe6d88570477caa069b2713ca24c1&Username=DaltW&Password=deltek1234&Integrated=N&grant_type=password&database=ThinkwellGroup_Preview'
# ouput json:
# {"access_token":"yokLe5JmsYcRagL9YTv2LUHxF8yND0Qexo8UzxxHGrnnq0RgpFNuafp71MZZ5j04m9kUStJBW-lX1L13N7FB4VyJy55oWTdu5Bjh-tGvLdMpYzXjc9L97eq9dJGhI6exHMC8-1rrPbcQh69kR63u4-PQmb0wR3n4PVr7vwleEVZrGlP_7mPmQZgXf9TsJm_K1SXmp0Oe-heg0l37qb_p97LkwURdykKBbWxvXZ6Eh8-mNW2PT4LTwnFHXRaFWa-4ZUxTy_C8l2RXiq-hUJ7AF8MFN5MvutyOd0nN-ovobtyLECqHhBsGF3cfVBRt4ZGkQLv0O4PvnEJ6xolS2xgSFLah7zPDBd0EObNE5qpgpw64RF9JuVAswBu-hAf3Dfsm","token_type":"bearer","expires_in":1799,"refresh_token":"HHPWIUl+zXss2Jwdx6oncBn9zmz/a+yhCHpXp0cLYJEzWWJwQL/EqO1/wqxPMnF9"}


oauth_token=$(curl -v -X POST https://vantagepointpreview.deltekfirst.com/ThinkwellGroup/api/token -H 'content-type: application/x-www-form-urlencoded' -d 'Client_Id=MJdeWdVPU00UtdUJN8tP0g98IEjM%2FsMkUDXFnUveqA8%3D&client_secret=070fe6d88570477caa069b2713ca24c1&Username=DaltW&Password=deltek1234&Integrated=N&grant_type=password&database=ThinkwellGroup_Preview' | jq .access_token | tr -d '"')

# here 
curl --request GET \
--url 'https://vantagepointpreview.deltekfirst.com/ThinkwellGroup/api/contact?limit=1' \
--header "authorization: Bearer ${oauth_token}" \
--header 'content-type: application/json'

curl --request GET \
--url 'https://vantagepointpreview.deltekfirst.com/ThinkwellGroup/api/employee?limit=1' \
--header "authorization: Bearer ${oauth_token}" \
--header 'content-type: application/json'
```

```bash
 python -m hrsync -c prod.ini deltek-get '/firm?fieldFilter=ClientID,ModDate&pageSize=10&order=ModDate_D'
 python -m hrsync -c prod.ini deltek-get '/contact?fieldFilter=ContactID,ClientID,ModDate&pageSize=10&order=ModDate_D'
```

# Deltek CodeTable

```
{{url}}/metadata/codeTable/{{codeTable}}
```

https://documenter.getpostman.com/view/4108327/RVu7ETjY?version=latest#22c76458-e111-4e9d-aa7b-a678ba9fc309

:
# Mapping BambooHR + Deltek fields
https://docs.google.com/spreadsheets/d/1cZ2u380m0sKD7-YG_WdV42bP1kSBmnpauwageRf7b5A/edit?ts=5d1cc188#gid=1574189150


# Pipedrive
https://thinkwell-sandbox-29104d.pipedrive.com/auth/login?return_url=https%3A%2F%2Fthinkwell-sandbox-29104d.pipedrive.com%2Factivities
user: louis.lynch@evodev.ca
password: Pipedrive1234

https://docs.google.com/document/d/1Z-edO3x-HmgIqNkmRQMhtNVgBDNkhZFGn0R_sNxbpIE/edit
https://docs.google.com/spreadsheets/d/16HSE3T63iwqNRoYc60wrf5jviJJcg2SVFjvU_m2vSwY/edit#gid=0

```bash
# execute only once
python -m hrsync.import_contacts test.ini
python -m hrsync.sync_pipedrive test.ini
```

```bash
python -m hrsync -pc prod.ini pipedrive-get /dealFields
python -m hrsync -pc prod.ini pipedrive-get /deals/2366
python -m hrsync -pc prod.ini pipedrive-get /users
```

```bash
python -m hrsync -pc prod.ini deltek-get '/codeTable/CFGProjectStage' | jq '.[] | (.Code + ": " + .Description)'
python -m hrsync -pc prod.ini pipedrive-get '/stages' | jq '.data[] | ((.id|tostring) + ": " +  .name)'
```

Pipedrive    -> Deltek
------------------------
Activities   -> Activity
Persons      -> Contact
Organisation -> Firm
Deals        -> Project

# Other Library References
argparse
    https://docs.python.org/3/library/argparse.html#other-utilities

