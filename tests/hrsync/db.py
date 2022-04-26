from hrsync import db

import os
import tempfile
import unittest


class DbTest(unittest.TestCase):
    sqlalchemy_url = 'sqlite:///unittest.db'
    pipedrive_id = 123456789

    def setUp(self):
        db.init(url=DbTest.sqlalchemy_url)
        self.session = db.session()
        p = db.PipedrivePerson.by_pipedrive_id(
            self.session,
            DbTest.pipedrive_id)
        if p:
            p.delete()

    def tearDown(self):
        self.session.close()

    def test_pipedrive_base(self):
        id = 'test_pipedrive_base'
        assert db.PipedrivePerson.by_pipedrive_id(
            self.session, DbTest.pipedrive_id).first() is None

        new_person = db.PipedrivePerson()
        new_person.deltek_id = id
        new_person.pipedrive_id = DbTest.pipedrive_id
        new_person.origin = 'deltek'
        self.session.add(new_person)
        self.session.commit()

        assert db.PipedrivePerson.by_pipedrive_id(
            self.session, DbTest.pipedrive_id).first() is not None

