#!/usr/bin/env bash

python -m hrsync -pc prod.ini  dump-deltek-employees | jq '.[] | (.FirstName + " " + .LastName + "," + .EmployeeCompany + "," + .Employee + "," + .Status)' > /tmp/deltek

python -m hrsync -pc prod.ini dump-bamboo-employees | jq '.[]  | .id' | tr -d '"' | xargs -i python -m hrsync -pc prod.ini dump-bamboo-employee {} | jq '.displayName + "," + .employeeNumber + "," + .location' > /tmp/bamboo
