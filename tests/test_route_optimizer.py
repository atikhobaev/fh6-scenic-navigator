import tempfile,unittest
from pathlib import Path


class MatrixPreview:
    def __init__(self,costs): self.costs=costs
    def item_anchor(self,item,direction=None):
        if item.get('type') in ('scenic_road','scenic_loop'):
            pair=item['anchors'][direction or item.get('direction','forward')]
            return pair[0],pair[1],item.get('internal_cost',5)
        a=item['nav_anchor_point_id']; return a,a,0
    def travel_cost(self,a,b,objective='fastest'):
        if a==b:return 0
        return self.costs.get((a,b))
    def validate_items(self,items,start_anchor=None,objective='fastest'):
        current=start_anchor; total=0
        for it in items:
            entry,exit_,internal=self.item_anchor(it,it.get('direction'))
            if current is not None:
                c=self.travel_cost(current,entry,objective)
                if c is None:return None
                total+=c
            total+=internal; current=exit_
        return total


class RouteOptimizerTests(unittest.TestCase):
    def test_optimizer_reorders_free_items_but_keeps_locked_position_and_final(self):
        from route_optimizer import optimize_items
        costs={(0,1):20,(0,2):5,(0,9):2,(1,9):2,(2,9):2,(9,1):4,(9,2):9,(1,2):3,(2,1):3,(1,3):4,(2,3):4,(9,3):20}
        p=MatrixPreview(costs)
        items=[
            {'id':'a','type':'temporary','nav_anchor_point_id':1},
            {'id':'lock','type':'temporary','nav_anchor_point_id':9,'position_locked':True},
            {'id':'b','type':'temporary','nav_anchor_point_id':2},
            {'id':'final','type':'temporary','nav_anchor_point_id':3},
        ]
        out=optimize_items(items,p,start_anchor=0,keep_final=True)
        self.assertEqual(out[1]['id'],'lock'); self.assertEqual(out[-1]['id'],'final')
        self.assertEqual({x['id'] for x in out},{'a','lock','b','final'})

    def test_optimizer_can_choose_reversible_block_direction_but_respects_direction_lock(self):
        from route_optimizer import optimize_items
        p=MatrixPreview({(0,10):20,(0,20):2,(11,30):3,(21,30):3})
        scenic={'id':'s','type':'scenic_road','direction':'forward','anchors':{'forward':(10,11),'reverse':(20,21)},'internal_cost':5}
        final={'id':'f','type':'temporary','nav_anchor_point_id':30}
        out=optimize_items([scenic,final],p,start_anchor=0,keep_final=True,choose_orientation=True)
        self.assertEqual(out[0]['direction'],'reverse')
        locked={**scenic,'direction_locked':True}
        out2=optimize_items([locked,final],p,start_anchor=0,keep_final=True,choose_orientation=True)
        self.assertEqual(out2[0]['direction'],'forward')

    def test_unresolvable_candidate_raises_without_partial_result(self):
        from route_optimizer import optimize_items, NoValidOptimizedRoute
        p=MatrixPreview({})
        with self.assertRaises(NoValidOptimizedRoute): optimize_items([{'id':'a','type':'temporary','nav_anchor_point_id':1},{'id':'b','type':'temporary','nav_anchor_point_id':2}],p,start_anchor=0)


class RouteServiceReverseTests(unittest.TestCase):
    def setUp(self):
        from planner_database import PlannerDatabase
        from route_service import RouteService
        self.tmp=tempfile.TemporaryDirectory(); db=PlannerDatabase(Path(self.tmp.name)/'db.sqlite'); db.initialize(); self.svc=RouteService(db)
        self.r=self.svc.get_active_route()
    def tearDown(self): self.tmp.cleanup()

    def test_reverse_flips_reversible_block_and_is_single_revision(self):
        self.svc.add_item(self.r['id'],{'type':'temporary','nav_anchor_point_id':1},0)
        a=self.svc.add_item(self.r['id'],{'type':'scenic_road','scenic_block_id':'x','direction':'forward'},1)
        b=self.svc.add_item(self.r['id'],{'type':'temporary','nav_anchor_point_id':2},2)
        out=self.svc.reverse_route(self.r['id'],3)
        self.assertEqual([x['type'] for x in out['items']],['temporary','scenic_road','temporary'])
        self.assertEqual(out['items'][1]['direction'],'reverse'); self.assertEqual(out['revision'],4)

    def test_reverse_direction_lock_conflict_requires_policy(self):
        from route_service import RouteReverseConflict
        self.svc.add_item(self.r['id'],{'type':'scenic_road','scenic_block_id':'x','direction':'forward','direction_locked':True},0)
        with self.assertRaises(RouteReverseConflict): self.svc.reverse_route(self.r['id'],1)
        out=self.svc.reverse_route(self.r['id'],1,policy='keep')
        self.assertEqual(out['items'][0]['direction'],'forward')
