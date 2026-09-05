import sqlite3
import tempfile
import unittest
from pathlib import Path

from planner_database import PlannerDatabase


class ConnectionLifecycleTests(unittest.TestCase):
    def test_context_closes_connection_after_success_and_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            db = PlannerDatabase(Path(directory) / 'navigator.db')
            for fail in (False, True):
                connection = db.connect()
                try:
                    try:
                        with connection:
                            connection.execute('create table if not exists sample(value)')
                            connection.execute('insert into sample values (1)')
                            if fail:
                                raise ValueError('rollback')
                    except ValueError:
                        pass
                    with self.assertRaises(sqlite3.ProgrammingError):
                        connection.execute('select 1')
                finally:
                    connection.close()
            with db.connect() as reopened:
                self.assertEqual(reopened.execute('select count(*) from sample').fetchone()[0], 1)
