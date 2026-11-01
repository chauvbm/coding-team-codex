import io, os, inspect, unittest
from unittest.mock import patch
import dotenv
from dotenv import DotEnvError, dotenv_values, load_dotenv
from dotenv.main import DotEnv
from dotenv.parser import parse_stream
from dotenv.variables import parse_variables, UndefinedVariableError

class Env(dict):
    def __init__(self,*a,**kw): super().__init__(*a,**kw); self.writes=[]
    def __setitem__(self,k,v): self.writes.append((k,v)); super().__setitem__(k,v)

class QA(unittest.TestCase):
    def values(self,s,**kw): return dotenv_values(stream=io.StringIO(s),strict=True,**kw)
    def error(self,s,kind,**kw):
        bindings=list(parse_stream(io.StringIO(s)))
        with self.assertRaises(DotEnvError) as c: self.values(s,**kw)
        e=c.exception
        self.assertEqual(e.kind,kind)
        b=next(b for b in bindings if b.original.string==e.original and b.original.line==e.line)
        self.assertIn(kind,str(e)); self.assertIn(str(e.line),str(e)); self.assertIsInstance(e,ValueError)
        return e
    def test_interfaces(self):
        for f in [DotEnv.__init__,dotenv_values,load_dotenv,parse_stream,parse_variables]:
            p=list(inspect.signature(f).parameters.values())[-1]
            self.assertEqual(p.name,'strict'); self.assertIs(p.default,False)
        self.assertIn('DotEnvError',dotenv.__all__)
        self.assertIs(dotenv.DotEnvError, __import__('dotenv.parser',fromlist=['DotEnvError']).DotEnvError)
    def test_precedence(self):
        cases=[('A=1\nA=${M}\nBAD="\n','duplicate'),('A=${M}\nA=2\n','undefined'),('A=1\nA="x" junk\n','parse'),('BAD="x" junk\nA=${M}\n','parse'),('A\nA\n','duplicate'),('#x\n\nA=\n\nA=\n','duplicate')]
        for source,kind in cases:
            with self.subTest(source=source): self.error(source,kind)
    def test_metadata(self):
        for sep in ['\n','\r','\r\n']:
            for source,kind in [('A=1'+sep+sep+' A=${M}'+sep,'duplicate'),(sep+'  A="one'+sep+'${M}"'+sep,'undefined'),(sep+' A="x" tail'+sep,'parse')]:
                self.error(source,kind)
    def test_atoms_matrix(self):
        for syntax in ['${X}','prefix${X}tail','${X:-d}','${X:-}','${:-d}','${}','${X:-${Y}}','$X','${X-default}','${X:default}']:
            strict=list(parse_variables(syntax,True)); loose=list(parse_variables(syntax))
            for env in [{},{'X':None},{'X':''},{'X':'ok'},{'X':'${Y}'},{'':'empty'}]:
                try: expected=''.join(a.resolve(env) for a in loose)
                except Exception: self.fail('permissive resolver raised')
                missing=next((a.name for a in strict if hasattr(a,'name') and a.default is None and a.name not in env),None)
                if missing is not None:
                    with self.assertRaises(UndefinedVariableError) as c: ''.join(a.resolve(env) for a in strict)
                    self.assertEqual(c.exception.name,missing)
                else: self.assertEqual(''.join(a.resolve(env) for a in strict),expected)
    def test_repeated_atoms(self):
        atom=list(parse_variables('${Q}',True))[0]
        for d in [{'Q':'1'},{'Q':None},{'Q':''},{'Q':'2'}]: self.assertEqual(atom.resolve(d),d['Q'] or '')
        with self.assertRaises(UndefinedVariableError): atom.resolve({})
    def test_priorities_and_none(self):
        for override,exp in [(True,'file'),(False,'os')]:
            with patch('os.environ',Env({'A':'os'})):
                d=DotEnv(None,io.StringIO('A=file\nB=${A}\nC\nD=${C:-z}\nE=\nF=${E:-z}\n'),override=override,strict=True).dict()
                self.assertEqual(list(d),['A','B','C','D','E','F']); self.assertEqual(d['B'],exp)
                self.assertIsNone(d['C']); self.assertEqual(d['D'],''); self.assertEqual(d['F'],'')
        self.error('A=${A}\n','undefined'); self.error('A=${B}\nB=x\n','undefined')
    def test_snapshot(self):
        env=Env({'X':'old'})
        class Stream(io.StringIO):
            def read(self,*a): env['X']='new'; env['Z']='new'; return super().read(*a)
        with patch('os.environ',env):
            d=DotEnv(None,Stream('A=${X}\nB=${X}\n'),strict=True).dict()
            self.assertEqual(d,{'A':'old','B':'old'})
            env['X']='old'
            with self.assertRaises(DotEnvError): DotEnv(None,Stream('A=${Zmissing}\n'),strict=True).dict()
    def test_transaction(self):
        for override in [False,True]:
            for source,kind in [('NEW=ok\nEXISTS=${M}\n','undefined'),('NEW=ok\nEXISTS=a\nEXISTS=b\n','duplicate'),('NEW=ok\nBAD="\n','parse')]:
                env=Env({'EXISTS':'keep'})
                with patch('os.environ',env), self.assertRaises(DotEnvError) as c:
                    load_dotenv(stream=io.StringIO(source),override=override,strict=True)
                self.assertEqual(c.exception.kind,kind); self.assertEqual(env.writes,[]); self.assertEqual(env,{'EXISTS':'keep'})
    def test_success_returns(self):
        for source,result,writes in [('',False,[]),('#x\n',False,[]),('N\n',True,[]),('EXISTS=x\n',True,[]),('NEW=x\nN\n',True,[('NEW','x')])]:
            env=Env({'EXISTS':'keep'})
            with patch('os.environ',env): self.assertIs(load_dotenv(stream=io.StringIO(source),strict=True),result)
            self.assertEqual(env.writes,writes)
    def test_no_interpolate(self):
        self.assertEqual(self.values('A=${M}\n',interpolate=False),{'A':'${M}'})
        self.error('A=${M}\nA=x\n','duplicate',interpolate=False)
        self.error('A="x" tail\n','parse',interpolate=False)
    def test_cache_failure_retry(self):
        source=io.StringIO('A=x\nA=y\n'); d=DotEnv(None,source,strict=True)
        with self.assertRaises(DotEnvError): d.dict()
        self.assertIsNone(d._dict); self.assertFalse(source.closed)
        source.seek(0); source.truncate(); source.write('A=ok\n'); source.seek(0)
        result=d.dict(); self.assertEqual(result,{'A':'ok'})
        source.seek(0); source.truncate(); source.write('A=${M}\n'); source.seek(0)
        self.assertIs(d.dict(),result)
    def test_parser_recovery(self):
        s='A=x\nBAD="x" tail\nB=y\n'
        self.assertEqual([b.error for b in parse_stream(io.StringIO(s))],[False,True,False])
        it=parse_stream(io.StringIO(s),True); self.assertEqual(next(it).key,'A')
        with self.assertRaises(DotEnvError): next(it)
        self.assertEqual([b.key for b in parse_stream(io.StringIO('A=1\nA=2\n'),True)],['A','A'])
    def test_permissive(self):
        self.assertEqual(dotenv_values(stream=io.StringIO('A=${M}\nA=last\nBAD="x" tail\nB=${Z}\n')) ,{'A':'last','B':''})
    def test_disabled(self):
        env=Env({'PYTHON_DOTENV_DISABLED':'yes'})
        with patch('os.environ',env): self.assertFalse(load_dotenv(stream=io.StringIO('A=${M}\n'),strict=True))
        self.assertEqual(env.writes,[])

if __name__=='__main__':
    with patch.dict(os.environ,{},clear=True): unittest.main(verbosity=2)
