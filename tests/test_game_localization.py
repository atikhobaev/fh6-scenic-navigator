import json, struct, zipfile, unittest, tempfile
from pathlib import Path
from game_localization import parse_str_bytes, read_stringtable_zip, build_place_name_map, refresh_place_names, find_stringtables_dir, localization_coverage


def make_section(entries):
    blob=b''; rows=[]
    for h,s in entries:
        off=len(blob); blob += s.encode('utf-8')+b'\0'; rows.append((h,off))
    size=12+8*len(rows)+len(blob)
    return struct.pack('<III',size,len(blob),len(rows))+b''.join(struct.pack('<II',*r) for r in rows)+blob

def make_str(table, entries):
    values=make_section([(h,v) for h,k,v in entries]); keys=make_section([(h,k) for h,k,v in entries])
    head=b'\x00\x08'+table.encode()+b'\0'; head=head.ljust(0x80,b'\0')+struct.pack('<III',0x8c,0x8c,0x8c+len(values))
    return head+values+keys

def make_zip(path, table, entries):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:z.writestr(f'{table}.str',make_str(table,entries))

class GameLocalizationTests(unittest.TestCase):
    def test_parse_str_bytes_links_keys_values_by_hash(self):
        doc=parse_str_bytes(make_str('Main',[(11,'poi_castle','Hirosaki Castle'),(22,'poi_fuji','Mount Fuji')]))
        self.assertEqual(doc['table'],'Main')
        self.assertEqual(doc['entries'][0],{'hash':11,'key':'poi_castle','value':'Hirosaki Castle'})

    def test_build_place_name_map_matches_same_table_and_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            make_zip(root/'EN.zip','Main',[(11,'castle','Hirosaki Castle'),(22,'fuji','Mount Fuji')])
            make_zip(root/'RU.zip','Main',[(11,'castle','Замок Хиросаки'),(22,'fuji','Гора Фудзи')])
            make_zip(root/'CHS.zip','Main',[(11,'castle','弘前城'),(22,'fuji','富士山')])
            make_zip(root/'MX.zip','Main',[(11,'castle','Castillo de Hirosaki'),(22,'fuji','Monte Fuji')])
            out=build_place_name_map([{'id':'game.hirosaki','name':'Hirosaki Castle','source':'game'}],root)
            self.assertEqual(out['game.hirosaki'],{'en-US':'Hirosaki Castle','zh-CN':'弘前城','ru-RU':'Замок Хиросаки','es-419':'Castillo de Hirosaki'})

    def test_ambiguous_english_name_is_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            make_zip(root/'EN.zip','Main',[(11,'a','Same'),(22,'b','Same')])
            make_zip(root/'RU.zip','Main',[(11,'a','Один'),(22,'b','Два')])
            self.assertEqual(build_place_name_map([{'id':'x','name':'Same','source':'game'}],root),{})


    def test_find_stringtables_dir_discovers_nondefault_steam_library_from_libraryfolders(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); steam=root/'Steam'; alt=root/'GamesSSD'
            (steam/'steamapps').mkdir(parents=True)
            tables=alt/'steamapps'/'common'/'Forza Horizon 6'/'media'/'Stripped'/'StringTables'
            tables.mkdir(parents=True); (tables/'EN.zip').write_bytes(b'zip')
            (steam/'steamapps'/'libraryfolders.vdf').write_text(f'"libraryfolders"\n{{\n "1" {{ "path" "{str(alt).replace(chr(92), chr(92)*2)}" }}\n}}', encoding='utf-8')
            found=find_stringtables_dir(steam_roots=[steam], xbox_roots=[])
            self.assertEqual(found,tables)

    def test_find_stringtables_dir_discovers_xbox_content_layout(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            tables=root/'XboxGames'/'Forza Horizon 6'/'Content'/'media'/'Stripped'/'StringTables'
            tables.mkdir(parents=True); (tables/'EN.zip').write_bytes(b'zip')
            found=find_stringtables_dir(steam_roots=[], xbox_roots=[root/'XboxGames'])
            self.assertEqual(found,tables)

    def test_localization_coverage_reports_each_locale_against_game_total(self):
        names={
            'game.a':{'en-US':'A','ru-RU':'А','zh-CN':'甲'},
            'game.b':{'en-US':'B','ru-RU':'Б'},
        }
        coverage=localization_coverage(names,total_game_places=3)
        self.assertEqual(coverage['en-US'],{'matched':2,'total':3})
        self.assertEqual(coverage['ru-RU'],{'matched':2,'total':3})
        self.assertEqual(coverage['zh-CN'],{'matched':1,'total':3})
        self.assertEqual(coverage['es-419'],{'matched':0,'total':3})

    def test_localization_coverage_excludes_curated_rows_from_game_poi_count(self):
        names={'game.a':{'en-US':'A','ru-RU':'А'},'curated.a':{'en-US':'C','ru-RU':'К'}}
        coverage=localization_coverage(names,total_game_places=1)
        self.assertEqual(coverage['ru-RU'],{'matched':1,'total':1})

    def test_refresh_merges_builtin_and_curated_but_not_community(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); make_zip(root/'EN.zip','Main',[(11,'castle','Hirosaki Castle')]);make_zip(root/'RU.zip','Main',[(11,'castle','Замок Хиросаки')])
            static=root/'static';(static/'data').mkdir(parents=True)
            (static/'data'/'builtin_places.json').write_text(json.dumps([{'id':'game.h','name':'Hirosaki Castle','source':'game'}]))
            (static/'data'/'scenic_catalog.json').write_text(json.dumps({'places':[{'id':'curated.h','name':'Hirosaki Castle','source':'curated'},{'id':'community.h','name':'Hirosaki Castle','source':'community'}]}))
            out=refresh_place_names(static,root,static/'data'/'place_names.json')
            self.assertEqual(out['game.h']['ru-RU'],'Замок Хиросаки')
            self.assertEqual(out['curated.h']['ru-RU'],'Замок Хиросаки')
            self.assertNotIn('community.h',out)
