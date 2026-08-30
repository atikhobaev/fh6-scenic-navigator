import unittest
from test_route_preview import graph_doc

class FakePlaces:
    def __init__(self,block): self.block=block
    def get_scenic_block(self,bid):
        if bid!=self.block['id']: raise KeyError(bid)
        return self.block

class ScenicBlockTests(unittest.TestCase):
    def test_scenic_block_forces_internal_path_and_reports_approach(self):
        from route_preview import DirectedGraph, RoutePreviewService
        g=DirectedGraph.from_payload(graph_doc())
        block={'id':'curated.road.test','type':'road','reversible':False,'forward_anchor_point_ids':[1,2,3]}
        svc=RoutePreviewService(g,FakePlaces(block))
        route={'id':'r','revision':1,'items':[{'id':'s','type':'scenic_road','scenic_block_id':block['id'],'direction':'forward'}]}
        p=svc.preview(route,start_anchor=0)
        self.assertTrue(p['resolved']); self.assertEqual(p['legs'][0]['segment_ids'],[0,1,2]); self.assertEqual(p['legs'][0]['scenic_distance_m'],20)

    def test_invalid_fixed_scenic_path_fails_closed(self):
        from route_preview import DirectedGraph, RoutePreviewService
        g=DirectedGraph.from_payload(graph_doc())
        block={'id':'curated.road.bad','type':'road','reversible':False,'forward_anchor_point_ids':[0,2,3]}
        svc=RoutePreviewService(g,FakePlaces(block))
        p=svc.preview({'id':'r','revision':1,'items':[{'id':'s','type':'scenic_road','scenic_block_id':block['id'],'direction':'forward'}]},start_anchor=0)
        self.assertFalse(p['resolved']); self.assertEqual(p['legs'][0]['reason'],'INVALID_SCENIC_BLOCK_PATH')

    def test_reversible_block_requires_reverse_path_definition(self):
        from route_preview import validate_scenic_block_definition
        block={'id':'x','type':'road','reversible':True,'forward_anchor_point_ids':[0,1]}
        with self.assertRaises(ValueError): validate_scenic_block_definition(block)
