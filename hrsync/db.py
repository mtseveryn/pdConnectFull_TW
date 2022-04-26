import sqlalchemy as sa
from sqlalchemy import Boolean, Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import sessionmaker
from dictalchemy import DictableModel
from sqlalchemy.ext.declarative import declarative_base

import datetime


Base = declarative_base(cls=DictableModel)
engine = None
session = None


class Employee(Base):
    __tablename__ = 'employees'

    bamboo_id = Column(Integer, primary_key=True)
    deltek_employee = Column(String(100))
    deltek_employee_company = Column(String(100))


class Change(Base):
    __tablename__ = 'changes'

    bamboo_id = Column(Integer, primary_key=True)
    datetime = Column(String(100))
    dry_run = Column(Boolean(), default=False)


class Alert(Base):
    __tablename__ = 'alerts'

    bamboo_id = Column(Integer, primary_key=True)
    datetime = Column(String(100))


class PipedriveBase(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)

    pipedrive_id = Column(Integer, unique=True)
    deltek_id = Column(String(100), unique=True)
    origin = Column(Enum("pipedrive", "deltek", "both"))

    datetime = Column(DateTime, default=datetime.datetime.utcnow)

    @classmethod
    def by_pipedrive_id(cls, session, pipedrive_id):
        if not isinstance(pipedrive_id, int):
            raise Exception(
                "piepedrive_id must be a int but was {}".format(pipedrive_id))
        return session.query(cls).filter(cls.pipedrive_id == pipedrive_id)

    @classmethod
    def by_deltek_id(cls, session, deltek_id):
        if not isinstance(deltek_id, str):
            raise Exception(
                "piepedrive_id must be a str but was {}".format(deltek_id))
        return session.query(cls).filter(cls.deltek_id == deltek_id)


class PipedriveOrganization(PipedriveBase):
    __tablename__ = 'pipedrive_organization'


class PipedrivePerson(PipedriveBase):
    __tablename__ = 'pipedrive_person'


class PipedriveDeal(PipedriveBase):
    __tablename__ = 'pipedrive_deal'


class PipedriveEmployee(PipedriveBase):
    __tablename__ = 'piepdrive_employee'


class PipedriveDealStatus(Base):
    __tablename__ = 'piepdrive_deal_status'

    id = Column(Integer, primary_key=True)

    pipedrive_id = Column(Integer, unique=True)
    status = Column(String(100))

    datetime = Column(DateTime, default=datetime.datetime.utcnow)

    @classmethod
    def by_pipedrive_id(cls, session, pipedrive_id):
        if not isinstance(pipedrive_id, int):
            raise Exception(
                "piepedrive_id must be a int but was {}".format(pipedrive_id))
        return session.query(cls).filter(cls.pipedrive_id == pipedrive_id)

    @classmethod
    def get(cls, session, pipedrive_id, default_status="won"):
        record = cls.by_pipedrive_id(session, pipedrive_id).first()
        if record:
            return record

        record = cls()
        record.pipedrive_id = pipedrive_id
        record.status = default_status
        session.add(record)
        return record


def init(url="sqlite:///test.db"):
    global engine, session
    engine = sa.create_engine(url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)
    return engine


def main():
    init()


if __name__ == "__main__":
    main()
