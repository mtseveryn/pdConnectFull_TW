import sys

from hrsync import db


def main(args):
    from_url = args[1]
    to_url = args[2]

    db.init(url=from_url)
    from_session = db.session()

    db.init(url=to_url)
    to_session = db.session()

    models = [
        db.Employee,
        db.Change,
        db.Alert,
        db.PipedriveOrganization,
        db.PipedrivePerson,
        db.PipedriveDeal,
        db.PipedriveEmployee,
        db.PipedriveDealStatus
    ]

    for model in models:
        results = from_session.query(model).all()
        for result in results:
            clone = model(**result.asdict())
            to_session.add(clone)
        to_session.commit()

    print("done")


if __name__ == "__main__":
    args = sys.argv
    main(args)
