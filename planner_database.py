from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
import uuid

SCHEMA_VERSION = 2


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class PlannerDatabase:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.backup_dir = self.path.parent / 'backups'

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('PRAGMA journal_mode=WAL')
        return con

    def schema_version(self) -> int:
        if not self.path.exists():
            return 0
        with self.connect() as con:
            row = con.execute("select value from app_state where key='schema_version'").fetchone()
            return int(row['value']) if row else 0

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists() and self.path.stat().st_size > 0
        if existed:
            current = self._probe_version()
            if current not in (0, 1, SCHEMA_VERSION):
                self._backup_before_migration(current)
                raise RuntimeError(f'Unsupported planner DB schema version {current}')
            if current == 1:
                self._backup_before_migration(current)
                self._migrate_v1_to_v2()
        with self.transaction() as con:
            self._create_schema(con)
            con.execute(
                "insert into app_state(key,value) values('schema_version',?) on conflict(key) do update set value=excluded.value",
                (str(SCHEMA_VERSION),),
            )
            active = con.execute("select value from app_state where key='active_route_id'").fetchone()
            if not active or not active['value']:
                rid = f'route.{uuid.uuid4()}'
                now = utc_now()
                con.execute(
                    'insert into routes(id,name,is_draft,revision,created_at,updated_at,last_opened_at) values(?,?,?,?,?,?,?)',
                    (rid, 'Draft Route', 1, 0, now, now, now),
                )
                con.execute("insert into app_state(key,value) values('active_route_id',?) on conflict(key) do update set value=excluded.value", (rid,))

    def _probe_version(self) -> int:
        try:
            with sqlite3.connect(self.path) as con:
                row = con.execute("select value from app_state where key='schema_version'").fetchone()
                return int(row[0]) if row else 0
        except sqlite3.Error:
            return 0

    def _backup_before_migration(self, current: int) -> Path:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        target = self.backup_dir / f'navigator-before-v{current}-{stamp}.db'
        shutil.copy2(self.path, target)
        return target

    def _migrate_v1_to_v2(self) -> None:
        """Allow navigation sessions to reference virtual read-only routes.

        Route validity is enforced by RouteService. The old FK prevented a
        navigation session from using built-in routes that intentionally do not
        live in the user-owned routes table.
        """
        con = sqlite3.connect(self.path)
        try:
            con.execute('PRAGMA foreign_keys=OFF')
            con.execute('BEGIN IMMEDIATE')
            session_exists = con.execute(
                "select 1 from sqlite_master where type='table' and name='navigation_sessions'"
            ).fetchone()
            if session_exists:
                progress_exists = con.execute(
                    "select 1 from sqlite_master where type='table' and name='navigation_progress'"
                ).fetchone()
                if progress_exists:
                    con.execute('alter table navigation_progress rename to navigation_progress_v1')
                con.execute('alter table navigation_sessions rename to navigation_sessions_v1')
                con.execute('''
                    create table navigation_sessions(
                      id text primary key,
                      route_id text not null,
                      route_revision_started integer not null,
                      started_at text not null,
                      finished_at text,
                      current_item_id text
                    )
                ''')
                con.execute('''
                    insert into navigation_sessions(id,route_id,route_revision_started,started_at,finished_at,current_item_id)
                    select id,route_id,route_revision_started,started_at,finished_at,current_item_id
                    from navigation_sessions_v1
                ''')
                if progress_exists:
                    con.execute('''
                        create table navigation_progress(
                          session_id text not null references navigation_sessions(id) on delete cascade,
                          route_item_id text not null,
                          status text not null,
                          visited_at text,
                          primary key(session_id, route_item_id)
                        )
                    ''')
                    con.execute('''
                        insert into navigation_progress(session_id,route_item_id,status,visited_at)
                        select session_id,route_item_id,status,visited_at from navigation_progress_v1
                    ''')
                    con.execute('drop table navigation_progress_v1')
                con.execute('drop table navigation_sessions_v1')
            con.execute(
                "insert into app_state(key,value) values('schema_version','2') "
                "on conflict(key) do update set value=excluded.value"
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _create_schema(self, con: sqlite3.Connection) -> None:
        con.executescript('''
        create table if not exists app_state(
          key text primary key,
          value text not null
        );
        create table if not exists user_places(
          id text primary key,
          name text not null,
          category text not null default 'my_place',
          notes text not null default '',
          x real not null,
          y real not null default 0,
          z real not null,
          nav_anchor_point_id integer,
          nav_snap_distance real,
          created_at text not null,
          updated_at text not null
        );
        create table if not exists favorites(
          place_id text primary key,
          created_at text not null
        );
        create table if not exists routes(
          id text primary key,
          name text not null,
          is_draft integer not null default 1,
          revision integer not null default 0,
          created_at text not null,
          updated_at text not null,
          last_opened_at text not null
        );
        create table if not exists route_items(
          id text primary key,
          route_id text not null references routes(id) on delete cascade,
          position integer not null,
          type text not null,
          place_id text,
          temporary_x real,
          temporary_y real,
          temporary_z real,
          nav_anchor_point_id integer,
          scenic_block_id text,
          direction text,
          stop_type text not null default 'stop',
          position_locked integer not null default 0,
          direction_locked integer not null default 0,
          custom_label text,
          unique(route_id, position)
        );
        create index if not exists idx_route_items_route on route_items(route_id, position);
        create table if not exists route_revisions(
          id integer primary key autoincrement,
          route_id text not null references routes(id) on delete cascade,
          revision_number integer not null,
          action text not null,
          before_json text not null,
          after_json text not null,
          is_undone integer not null default 0,
          created_at text not null
        );
        create index if not exists idx_route_revisions_route on route_revisions(route_id,id);
        create table if not exists navigation_sessions(
          id text primary key,
          route_id text not null,
          route_revision_started integer not null,
          started_at text not null,
          finished_at text,
          current_item_id text
        );
        create table if not exists navigation_progress(
          session_id text not null references navigation_sessions(id) on delete cascade,
          route_item_id text not null,
          status text not null,
          visited_at text,
          primary key(session_id, route_item_id)
        );
        ''')

    @contextmanager
    def transaction(self):
        con = self.connect()
        try:
            con.execute('BEGIN IMMEDIATE')
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def get_app_state(self) -> dict:
        with self.connect() as con:
            rows = con.execute('select key,value from app_state').fetchall()
        return {r['key']: r['value'] for r in rows}
