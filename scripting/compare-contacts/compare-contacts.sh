
get_contacts() {
    python -m hrsync -c prod.ini pipedrive-get '/persons?limit=500&start=0'    > /tmp/persons1.json
    python -m hrsync -c prod.ini pipedrive-get '/persons?limit=500&start=500'  > /tmp/persons2.json
    python -m hrsync -c prod.ini pipedrive-get '/persons?limit=500&start=1000' > /tmp/persons3.json
    python -m hrsync -c prod.ini pipedrive-get '/persons?limit=500&start=1500' > /tmp/persons4.json
    python -m hrsync -c prod.ini pipedrive-get '/persons?limit=500&start=2000' > /tmp/persons5.json
    python -m hrsync -c prod.ini pipedrive-get '/persons?limit=500&start=2500' > /tmp/persons6.json
    python -m hrsync -c prod.ini pipedrive-get '/persons?limit=500&start=3000' > /tmp/persons7.json

    python -m hrsync -c prod.ini deltek-get '/contact' > /tmp/contacts.json
}

get_firms() {
    python -m hrsync -c prod.ini pipedrive-get '/organizations?limit=500&start=0'    > /tmp/organizations1.json
    python -m hrsync -c prod.ini pipedrive-get '/organizations?limit=500&start=500'  > /tmp/organizations2.json
    python -m hrsync -c prod.ini pipedrive-get '/organizations?limit=500&start=1000' > /tmp/organizations3.json
    python -m hrsync -c prod.ini pipedrive-get '/organizations?limit=500&start=1500' > /tmp/organizations4.json
    python -m hrsync -c prod.ini pipedrive-get '/organizations?limit=500&start=2000' > /tmp/organizations5.json

    python -m hrsync -c prod.ini deltek-get '/firm' > /tmp/firms.json
}

process_contacts() {
    jq '.data[] | ( (.id|tostring) + ":" + .name + ":" + .email[].value )' /tmp/persons{1..7}.json  | sort | uniq > /tmp/persons.csv
    jq '.[] | ( .ContactID + ":" + .flName + ":" + .Email )' /tmp/contacts.json | sort | uniq > /tmp/contacts.csv


    jq '.data[] | ( .email[].value )' /tmp/persons{1..7}.json  | sort | uniq > /tmp/persons-email.csv
    jq '.[] | ( .Email )' /tmp/contacts.json | sort | uniq > /tmp/contacts-emails.csv

    # show commons by emails
    #comm -12 <(tr 'A-Z' 'a-z' < /tmp/contacts-emails.csv) <(tr 'A-Z' 'a-z' < /tmp/persons-email.csv)
    comm -12 <(tr 'A-Z' 'a-z' < /tmp/contacts-emails.csv) <(tr 'A-Z' 'a-z' < /tmp/persons-email.csv) | wc -l

    jq '.data[] | ( .first_name + " " + .last_name )' /tmp/persons{1..7}.json  | sort | uniq > /tmp/persons-name.csv
    jq '.[] | ( .FirstName + " " + .LastName )' /tmp/contacts.json | sort | uniq > /tmp/contacts-name.csv
    # show commons by name
    #comm -12 <(tr 'A-Z' 'a-z' < /tmp/contacts-name.csv) <(tr 'A-Z' 'a-z' < /tmp/persons-name.csv)
    comm -12 <(tr 'A-Z' 'a-z' < /tmp/contacts-name.csv) <(tr 'A-Z' 'a-z' < /tmp/persons-name.csv) | wc -l
}

process_firms() {
    jq '.data[] | ( .name )' /tmp/organizations{1..5}.json  | sort | uniq > /tmp/organizations-name.csv
    jq '.[] | ( .Name )' /tmp/firms.json | sort | uniq > /tmp/firms-name.csv
    #jq '.data[0]' /tmp/organizations{1..5}.json 
    #jq '.[0]' /tmp/firms.json

    wc -l /tmp/firms-name.csv
    wc -l /tmp/organizations-name.csv
    comm -12 <(tr 'A-Z' 'a-z' < /tmp/organizations-name.csv | sort) <(tr 'A-Z' 'a-z' < /tmp/firms-name.csv | sort) | wc -l
}

#get_contacts
process_contacts

#get_firms
#process_firms
