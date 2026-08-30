import sqlite3
import tempfile
import unittest
from pathlib import Path


class PlannerDatabaseTests(unittest.TestCase):
    def test_initialize_creates_schema_and_active_draft(self):
        from planner_database import PlannerDatabase
        with tempfile.TemporaryDirectory() as td:
            db = PlannerDatabase(Path(td) / 'navigator.db')
            db.initialize()
            self.assertEqual(db.schema_version(), 2)
            state = db.get_app_state()
            self.assertTrue(state['active_route_id'])
            with db.connect() as con:
                row = con.execute('select name,is_draft,revision from routes where id=?', (state['active_route_id'],)).fetchone()
            self.assertEqual(tuple(row), ('Draft Route', 1, 0))

    def test_transaction_rolls_back_all_writes(self):
        from planner_database import PlannerDatabase
        with tempfile.TemporaryDirectory() as td:
            db = PlannerDatabase(Path(td) / 'navigator.db'); db.initialize()
            try:
                with db.transaction() as con:
                    con.execute("insert into favorites(place_id,created_at) values('x','now')")
                    con.execute("insert into favorites(place_id,created_at) values('x','now')")
            except sqlite3.IntegrityError:
                pass
            with db.connect() as con:
                count = con.execute("select count(*) from favorites where place_id='x'").fetchone()[0]
            self.assertEqual(count, 0)

    def test_existing_version_is_preserved_and_backup_directory_available(self):
        from planner_database import PlannerDatabase
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = PlannerDatabase(root / 'navigator.db'); db.initialize()
            self.assertTrue(db.backup_dir.is_dir())
            self.assertEqual(db.schema_version(), 2)
    def test_v1_database_migrates_sessions_to_virtual_route_capable_schema_with_backup(self):
        from planner_database import PlannerDatabase
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); path = root / 'navigator.db'
            with sqlite3.connect(path) as con:
                con.executescript("""
                create table app_state(key text primary key,value text not null);
                create table routes(
                  id text primary key,name text not null,is_draft integer not null default 1,revision integer not null default 0,
                  created_at text not null,updated_at text not null,last_opened_at text not null
                );
                create table navigation_sessions(
                  id text primary key,route_id text not null references routes(id) on delete cascade,
                  route_revision_started integer not null,started_at text not null,finished_at text,current_item_id text
                );
                create table navigation_progress(
                  session_id text not null references navigation_sessions(id) on delete cascade,
                  route_item_id text not null,status text not null,visited_at text,primary key(session_id,route_item_id)
                );
                """)
                con.execute("insert into app_state(key,value) values('schema_version','1')")
                con.execute("insert into app_state(key,value) values('active_route_id','route.old')")
                con.execute("insert into routes values('route.old','Old',0,0,'now','now','now')")
                con.execute("insert into navigation_sessions values('nav.old','route.old',0,'now',NULL,'item.old')")
                con.execute("insert into navigation_progress values('nav.old','item.old','active',NULL)")
            db = PlannerDatabase(path); db.initialize()
            self.assertEqual(db.schema_version(), 2)
            backups = list(db.backup_dir.glob('navigator-before-v1-*.db'))
            self.assertEqual(len(backups), 1)
            with db.connect() as con:
                session = con.execute("select route_id,current_item_id from navigation_sessions where id='nav.old'").fetchone()
                progress = con.execute("select status from navigation_progress where session_id='nav.old'").fetchone()
                fks = con.execute('pragma foreign_key_list(navigation_sessions)').fetchall()
            self.assertEqual(tuple(session), ('route.old', 'item.old'))
            self.assertEqual(progress['status'], 'active')
            self.assertFalse(any(row['table'] == 'routes' for row in fks))

