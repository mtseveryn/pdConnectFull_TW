import sys


def read_csv(filename):
    lines = []
    for line in open(filename).readlines():
        lines.append(line.strip().replace('"', '').split(","))
    return lines

def location_to_employee_company(location):
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


def main(bamboo, deltek):
    bs = read_csv(bamboo)
    ds = {l[0].strip(): l[1:] for l in read_csv(deltek)}

    for b in bs:
        name = b[0].replace("  ", " ").strip()
        ds_fields = ds.get(name, ['', '', ''])
        bamboo_number = "{}{}".format(location_to_employee_company(b[2]), b[1])
        deltek_number = "{}{}".format(ds_fields[0], ds_fields[1])
        ok = bamboo_number == deltek_number
        ok_str = "OK " if ok else "ERR"
        print(",".join([ok_str, name, bamboo_number, deltek_number]))


if __name__ == "__main__":
    a = sys.argv[1]
    b = sys.argv[2]
    main(a, b)
