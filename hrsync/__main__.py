import argparse
import sys

from hrsync.commands import dump
from hrsync.config import Config


class ConfigLoaderAction(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        values = Config.from_file(values) \
            if values is not None else Config()
        setattr(args, self.dest, values)


def main(args):
    main_parser = argparse.ArgumentParser(
        'hrsync', description="Tool to sync Bamboo and Deltek")
    main_parser.add_argument(
        '-c', '--config', type=str, action=ConfigLoaderAction)
    main_parser.add_argument('-p', '--pretty', action="store_true")
    main_parser.add_argument('-j', '--json', action="store_true")

    subparsers = main_parser.add_subparsers()

    # dump bamboo
    s = subparsers.add_parser('dump-bamboo-employees')
    s.set_defaults(func=dump.bamboo_employees)

    s = subparsers.add_parser('dump-bamboo-employee')
    s.add_argument('id')
    s.set_defaults(func=dump.bamboo_employee)

    s = subparsers.add_parser('dump-bamboo-employee-changes')
    s.set_defaults(func=dump.bamboo_employee_changes)

    # dump deltek
    s = subparsers.add_parser('dump-deltek-employees')
    s.set_defaults(func=dump.deltek_employees)

    s = subparsers.add_parser('dump-deltek-employee')
    s.add_argument('Employee')
    s.add_argument('EmployeeCompany')
    s.set_defaults(func=dump.deltek_employee)

    s = subparsers.add_parser('dump-deltek-metadata-employee')
    s.set_defaults(func=dump.deltek_metadata_employee)

    s = subparsers.add_parser('dump-deltek-default-employee')
    s.set_defaults(func=dump.deltek_default_employee)

    s = subparsers.add_parser('deltek-create-employee')
    s.add_argument('-f', "--file")
    s.set_defaults(func=dump.deltek_create_employee)

    s = subparsers.add_parser('deltek-update-employee')
    s.add_argument('-f', "--file")
    s.set_defaults(func=dump.deltek_update_employee)

    s = subparsers.add_parser('dump-deltek-organizations')
    s.set_defaults(func=dump.deltek_organizations)

    s = subparsers.add_parser('dump-deltek-metadata')
    s.add_argument('codeTable')
    s.set_defaults(func=dump.deltek_metadata)

    s = subparsers.add_parser('dump-deltek-codetable')
    s.add_argument('codeTable')
    s.set_defaults(func=dump.deltek_codetable)

    s = subparsers.add_parser('dump-mapping')
    s.set_defaults(func=dump.dump_mapping)

    # test urls
    s = subparsers.add_parser('bamboo-get')
    s.add_argument('url')
    s.set_defaults(func=dump.bamboo_get)

    s = subparsers.add_parser('deltek-get')
    s.add_argument('url')
    s.set_defaults(func=dump.deltek_get)

    s = subparsers.add_parser('pipedrive-get')
    s.add_argument('url')
    s.set_defaults(func=dump.pipedrive_get)

    #sync_parser = subparsers.add_parser('sync')
    options = main_parser.parse_args(args)
    options.func(options)


if __name__ == '__main__':
    main(sys.argv[1:])
