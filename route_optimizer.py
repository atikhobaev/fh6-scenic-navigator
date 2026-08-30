from __future__ import annotations
from copy import deepcopy
from itertools import permutations, product

class NoValidOptimizedRoute(RuntimeError): pass


def orientation_options(item,choose=True):
    typ=item.get('type')
    if not choose or item.get('direction_locked') or typ not in ('scenic_road','scenic_loop'):
        return [item.get('direction') or ('clockwise' if typ=='scenic_loop' else 'forward')]
    if typ=='scenic_loop': return ['clockwise','counterclockwise']
    return ['forward','reverse']


def _apply_orientations(seq,dirs):
    out=[]
    for item,d in zip(seq,dirs):
        q=deepcopy(item)
        if q.get('type') in ('scenic_road','scenic_loop'): q['direction']=d
        out.append(q)
    return out


def _evaluate(seq,preview,start_anchor,objective):
    if hasattr(preview,'validate_items'):
        return preview.validate_items(seq,start_anchor=start_anchor,objective=objective)
    return None


def optimize_items(items,preview,start_anchor=None,objective='fastest',keep_final=True,choose_orientation=True,max_exact=8):
    items=[deepcopy(x) for x in items]
    if not items:return []
    fixed={i for i,x in enumerate(items) if x.get('position_locked')}
    if keep_final: fixed.add(len(items)-1)
    free_slots=[i for i in range(len(items)) if i not in fixed]
    free_items=[items[i] for i in free_slots]
    best=None; best_cost=float('inf')

    def consider(seq):
        nonlocal best,best_cost
        opts=[orientation_options(x,choose_orientation) for x in seq]
        combos=product(*opts)
        for dirs in combos:
            oriented=_apply_orientations(seq,dirs)
            cost=_evaluate(oriented,preview,start_anchor,objective)
            if cost is not None and cost<best_cost:
                best_cost=float(cost); best=oriented

    if len(free_items)<=max_exact:
        for perm in permutations(free_items):
            seq=[None]*len(items)
            for i in fixed: seq[i]=deepcopy(items[i])
            for slot,item in zip(free_slots,perm): seq[slot]=deepcopy(item)
            consider(seq)
    else:
        # Deterministic greedy fallback while preserving exact locked positions.
        remaining=[deepcopy(x) for x in free_items]; seq=[None]*len(items); current=start_anchor
        for i in fixed: seq[i]=deepcopy(items[i])
        for pos in range(len(items)):
            if seq[pos] is not None:
                try: _,current,_=preview.item_anchor(seq[pos],seq[pos].get('direction'))
                except Exception: current=None
                continue
            choice=None
            for idx,item in enumerate(remaining):
                for d in orientation_options(item,choose_orientation):
                    try:
                        entry,exit_,internal=preview.item_anchor(item,d); travel=0 if current is None else preview.travel_cost(current,entry,objective)
                    except Exception: travel=None
                    if travel is None: continue
                    score=float(travel)+float(internal or 0)
                    key=(score,str(item.get('id','')),d)
                    if choice is None or key<choice[0]: choice=(key,idx,d,exit_)
            if choice is None: raise NoValidOptimizedRoute('no legal greedy candidate')
            _,idx,d,current=choice; item=remaining.pop(idx); item['direction']=d if item.get('type') in ('scenic_road','scenic_loop') else item.get('direction'); seq[pos]=item
        consider(seq)
    if best is None: raise NoValidOptimizedRoute('could not find a fully legal optimized route')
    return best
