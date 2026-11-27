"""Fail-closed inventory contract for replacing explicitly declared, non-original copper."""

def validate_inventory(before, after, original, declarations, candidate):
    declared={item['uuid']:item for item in declarations}
    assert len(declared)==len(declarations), 'duplicate replacement declaration'
    assert set(before)-set(after)==set(declared), 'undeclared or missing removal'
    assert not set(declared)&set(original), 'attempt to remove original copper'
    for uid,item in declared.items():
        assert before[uid]['authored']==item['before_sexpr'], ('stale removal declaration',uid)
    for uid in set(before)&set(after):
        assert before[uid]==after[uid], ('changed retained checkpoint object',uid)
    for uid in set(original)&set(after):
        if original[uid]['kind']in ['segment','via']:
            assert original[uid]==after[uid], ('changed original copper',uid)
    assert set(candidate)==set(after), 'native candidate inventory differs'
    for uid in set(after)-set(before):
        assert candidate[uid]==after[uid], ('native added object differs from authored candidate',uid)
    return {'removed':sorted(declared),'added':sorted(set(after)-set(before))}
