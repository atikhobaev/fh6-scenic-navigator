import json,tempfile,unittest
from pathlib import Path


def graph_doc():
    # 0->1->2->3 legal; reverse exists only 2->1, but transitions block it from the forward chain.
    return {
      'format':'fh6-navgraph-v1','source':{'sha256':'x'},'capabilities':{'directed_segments':True,'turn_transitions':True,'route_validated':True},
      'stats':{},
      'points':[[0,0,0,0],[1,10,0,0],[2,20,0,0],[3,30,0,0],[4,20,0,10]],
      'segments':[
        [0,0,0,1,10,1,'asphalt'],[1,0,1,2,10,1,'asphalt'],[2,0,2,3,10,1,'asphalt'],
        [3,1,2,1,10,0,'asphalt'],[4,2,2,4,12,0,'dirt']
      ],
      'transitions':[[0,1],[1,2],[1,4],[3,0],[4,4]]
    }

class DirectedPreviewTests(unittest.TestCase):
    def test_route_uses_only_legal_directed_transitions_and_reverse_fails(self):
        from route_preview import DirectedGraph
        g=DirectedGraph.from_payload(graph_doc())
        r=g.route_between(0,3)
        self.assertEqual(r['segment_ids'],[0,1,2]); self.assertEqual(r['distance_m'],30)
        self.assertIsNone(g.route_between(3,0))

    def test_preview_marks_unresolved_leg_instead_of_fallback(self):
        from route_preview import DirectedGraph, RoutePreviewService
        g=DirectedGraph.from_payload(graph_doc()); svc=RoutePreviewService(g,places=None)
        route={'id':'r','revision':7,'items':[{'id':'a','type':'temporary','nav_anchor_point_id':0},{'id':'b','type':'temporary','nav_anchor_point_id':3},{'id':'c','type':'temporary','nav_anchor_point_id':0}]}
        p=svc.preview(route)
        self.assertFalse(p['resolved']); self.assertEqual(p['revision'],7); self.assertTrue(p['legs'][0]['resolved']); self.assertFalse(p['legs'][1]['resolved'])
        self.assertEqual(p['legs'][1]['reason'],'NO_LEGAL_DIRECTED_PATH')

    def test_real_graph_smoke_routes_between_known_adjacent_points(self):
        from route_preview import DirectedGraph
        g=DirectedGraph.from_gzip_path(Path('static/data/fh6_navgraph_v1.json.gz'))
        r=g.route_between(0,1); self.assertIsNotNone(r); self.assertEqual(r['point_ids'][0],0); self.assertEqual(r['point_ids'][-1],1)
