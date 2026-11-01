import io,random
from unittest.mock import patch
from dotenv import main,DotEnvError
rng=random.Random(407)
checks=0
for trial in range(2500):
    env={k:rng.choice(['', 'os_'+k]) for k in 'ABC' if rng.choice([True,False])}
    override=rng.choice([True,False]); interpolate=rng.choice([True,False])
    prior={}; rows=[]; expected_error=None
    for index in range(rng.randint(1,8)):
        name=rng.choice('ABCD')
        kind=rng.choice(['literal','none','ref','default','two'])
        ref=rng.choice('ABCDE'); ref2=rng.choice('ABCDE')
        text={'literal':'literal','none':None,'ref':'${'+ref+'}','default':'${'+ref+':-fallback}','two':'${'+ref+'}:${'+ref2+'}'}[kind]
        rows.append(name+('='+text if text is not None else ''))
        if expected_error: continue
        if name in prior: expected_error=('duplicate',index+1,rows[-1]+'\n'); continue
        value=text
        if interpolate and text is not None:
            scope=({**env,**prior} if override else {**prior,**env})
            if kind=='default': value=scope.get(ref,'fallback') or ''
            elif kind in ('ref','two'):
                refs=[ref] if kind=='ref' else [ref,ref2]
                if any(r not in scope for r in refs): expected_error=('undefined',index+1,rows[-1]+'\n'); continue
                value=(':'.join(scope[r] or '' for r in refs))
        prior[name]=value
    source='\n'.join(rows)+'\n'
    with patch.object(main.os,'environ',env):
        try: result=main.DotEnv(None,io.StringIO(source),override=override,interpolate=interpolate,strict=True).dict()
        except DotEnvError as e:
            assert expected_error==(e.kind,e.line,e.original),(source,env,expected_error,e)
        else:
            assert expected_error is None,(source,expected_error,result)
            assert list(result.items())==list(prior.items()),(source,env,result,prior)
    checks+=1
print(f'PASS {checks} deterministic independently modeled integration cases')
