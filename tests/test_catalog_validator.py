import unittest


def graph():
    return {'format':'fh6-navgraph-v1','capabilities':{'directed_segments':True,'turn_transitions':True},
      'points':[[1,0,0,0],[2,100,0,0],[3,200,0,0]],
      'segments':[[10,0,1,2,100,1,'asphalt'],[11,0,2,3,100,1,'asphalt']],
      'transitions':[[10,11]]}

def place(pid='builtin.a',anchor=1,x=0):
    return {'id':pid,'source':'game','kind':'point','name':'A','aliases':[],'category':'landmarks','subcategory':'','tags':[],
      'position':{'x':x,'y':0,'z':0},'navigation':{'anchor_point_id':anchor,'snap_distance_m':1},'surface':'asphalt','access':'easy','scenic_score':1,'default_visible':True,'featured':False,'quality':'verified',
      'sources':[{'provider':'p','source_id':pid}]}

class CatalogValidatorTests(unittest.TestCase):
    def test_valid_catalog_reports_counts(self):
        from catalog_validator import validate_catalogs
        b={'places':[place()]}; c={'places':[],'blocks':[{'id':'curated.road.x','type':'road','name':'R','reversible':False,'forward_anchor_point_ids':[1,2,3]}],'collections':[]}
        r=validate_catalogs(b,c,graph()); self.assertTrue(r['valid']); self.assertEqual(r['places'],1); self.assertEqual(r['blocks'],1)

    def test_duplicate_ids_bad_coordinates_and_broken_anchor_fail(self):
        from catalog_validator import CatalogValidationError, validate_catalogs
        with self.assertRaisesRegex(CatalogValidationError,'duplicate'): validate_catalogs({'places':[place(),place()]},{'places':[],'blocks':[],'collections':[]},graph())
        bad=place(); bad['position']['x']=float('nan')
        with self.assertRaisesRegex(CatalogValidationError,'coordinate'): validate_catalogs({'places':[bad]},{'places':[],'blocks':[],'collections':[]},graph())
        with self.assertRaisesRegex(CatalogValidationError,'anchor'): validate_catalogs({'places':[place(anchor=999)]},{'places':[],'blocks':[],'collections':[]},graph())

    def test_duplicate_source_mapping_and_broken_scenic_path_fail(self):
        from catalog_validator import CatalogValidationError, validate_catalogs
        a=place('a'); b=place('b'); b['sources']=[{'provider':'p','source_id':'a'}]
        with self.assertRaisesRegex(CatalogValidationError,'source mapping'): validate_catalogs({'places':[a,b]},{'places':[],'blocks':[],'collections':[]},graph())
        block={'id':'r','type':'road','name':'R','reversible':False,'forward_anchor_point_ids':[1,3]}
        with self.assertRaisesRegex(CatalogValidationError,'scenic'): validate_catalogs({'places':[place()]},{'places':[],'blocks':[block],'collections':[]},graph())

    def test_reversible_block_requires_valid_reverse_path(self):
        from catalog_validator import CatalogValidationError, validate_catalogs
        block={'id':'r','type':'road','name':'R','reversible':True,'forward_anchor_point_ids':[1,2,3],'reverse_anchor_point_ids':[3,2,1]}
        with self.assertRaisesRegex(CatalogValidationError,'reverse'): validate_catalogs({'places':[place()]},{'places':[],'blocks':[block],'collections':[]},graph())

if __name__=='__main__': unittest.main()
