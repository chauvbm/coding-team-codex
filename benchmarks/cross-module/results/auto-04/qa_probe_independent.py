import io
import inspect
import itertools
import unittest
from unittest.mock import patch
import dotenv
from dotenv.main import DotEnv
from dotenv.parser import parse_stream, DotEnvError
from dotenv.variables import parse_variables, UndefinedVariableError

class Env(dict):
    def __init__(self, *args):
        super().__init__(*args); self.writes=[]
    def __setitem__(self,k,v):
        self.writes.append((k,v)); super().__setitem__(k,v)

class QA(unittest.TestCase):
    def values(self,s,**kw):
        return dotenv.dotenv_values(stream=io.StringIO(s),strict=True,**kw)
    def test_interfaces(self):
        self.assertIs(dotenv.DotEnvError, DotEnvError)
        self.assertIn('DotEnvError',dotenv.__all__)
        for f in (DotEnv.__init__,dotenv.dotenv_values,dotenv.load_dotenv,parse_stream,parse_variables):
            p=list(inspect.signature(f).parameters.values())[-1]
            self.assertEqual(p.name,'strict'); self.assertIs(p.default,False)
        self.assertTrue(issubclass(UndefinedVariableError,ValueError))
    def test_binding_location_and_precedence_matrix(self):
        # Derive expected binding locations from upstream-compatible permissive parsing.
        samples=[('parse','\n \n BAD=\"broken\nNEXT=x'),('duplicate','\nA=one\n\nA=${M}\n'),('duplicate','A\nA\n'),('undefined','\nA=\"first\n${M}\"\n'),('undefined','A=${M}\nBAD=\"broken'),('duplicate','A=x\nA=${M}\nBAD=\"broken')]
        for kind,s in samples:
            with self.subTest(kind=kind,s=s),patch('dotenv.main.os.environ',{}):
                bindings=list(parse_stream(io.StringIO(s)))
                if kind=='parse': b=next(b for b in bindings if b.error)
                elif kind=='duplicate':
                    seen=set()
                    for b in bindings:
                        if b.key in seen: break
                        if b.key is not None: seen.add(b.key)
                else: b=next(b for b in bindings if b.value and '${M}' in b.value)
                with self.assertRaises(DotEnvError) as cm: self.values(s)
                e=cm.exception
                self.assertEqual((e.kind,e.line,e.original),(kind,b.original.line,b.original.string))
                self.assertIn(kind,str(e)); self.assertIn(str(e.line),str(e))
        s='A=x\nA=\"x\" extra\n'
        with self.assertRaises(DotEnvError) as cm: self.values(s)
        self.assertEqual(cm.exception.kind,'parse')
    def test_low_level_parser_and_variables(self):
        it=parse_stream(io.StringIO('A=1\nA=2\nBROKEN=\"x'),strict=True)
        self.assertEqual(next(it).value,'1'); self.assertEqual(next(it).value,'2')
        with self.assertRaises(DotEnvError): next(it)
        for name in ('M','','with spaces'):
            atom=list(parse_variables('${'+name+'}',strict=True))[0]
            with self.assertRaises(UndefinedVariableError) as cm: atom.resolve({})
            self.assertEqual(cm.exception.name,name)
            for value in ('ok','',None): self.assertEqual(atom.resolve({name:value}),value or '')
            with self.assertRaises(UndefinedVariableError): atom.resolve({})
        for value in (None,'','present'):
            atoms=list(parse_variables('a${M:-${N}}b',strict=True))
            self.assertEqual(''.join(a.resolve({'M':value}) for a in atoms),'a'+(value or '')+'}b')
        self.assertEqual(''.join(a.resolve({}) for a in parse_variables('$M ${M:+x}',True)),'$M ${M:+x}')
    def test_snapshot_merge_and_self_reference(self):
        for override,expected in ((True,'file||old'),(False,'os||old')):
            env=Env({'A':'os','SELF':'old'})
            class Mutating(io.StringIO):
                def read(self,*a):
                    dict.__setitem__(env,'A','changed'); dict.__setitem__(env,'NEW','late')
                    return super().read(*a)
            s=Mutating('A=file\nN\nSELF=${A}|${N}|${SELF}\nL=${NEW:-absent}\n')
            with patch('dotenv.main.os.environ',env):
                out=DotEnv(None,s,override=override,strict=True).dict()
            self.assertEqual(out['SELF'],expected); self.assertEqual(out['L'],'absent')
            self.assertEqual(list(out),['A','N','SELF','L']); self.assertIsNone(out['N'])
        with patch('dotenv.main.os.environ',{}):
            for s in ('A=${A}\n','A=${B}\nB=x\n'):
                with self.assertRaises(DotEnvError): self.values(s)
    def test_zero_writes_for_all_failures_and_skips(self):
        for override,s in itertools.product((True,False),('GOOD=1\nBAD=\"oops','GOOD=1\nA\nA=x\n','GOOD=1\nEXISTS=${MISSING}\n')):
            env=Env({'EXISTS':'os'})
            with patch('dotenv.main.os.environ',env):
                with self.assertRaises(DotEnvError): dotenv.load_dotenv(stream=io.StringIO(s),strict=True,override=override)
            self.assertEqual(env.writes,[])
    def test_commit_literals_and_cache(self):
        for override in (True,False):
            env=Env({'A':'old'})
            with patch('dotenv.main.os.environ',env):
                self.assertTrue(dotenv.load_dotenv(stream=io.StringIO('A=new\nB\nC=${M}\n'),strict=True,override=override,interpolate=False))
            self.assertEqual(env.writes,([('A','new')] if override else [])+[('C','${M}')])
        stream=io.StringIO('A=${M}')
        obj=DotEnv(None,stream=stream,strict=True)
        with patch('dotenv.main.os.environ',{}):
            with self.assertRaises(DotEnvError): obj.dict()
        self.assertIsNone(obj._dict); stream.seek(0)
        with patch('dotenv.main.os.environ',{'M':'yes'}): self.assertEqual(obj.dict(),{'A':'yes'})
        stream.close()
        with patch('dotenv.main.os.environ',{}): self.assertEqual(obj.dict(),{'A':'yes'})
    def test_empty_comments_disabled_and_permissive(self):
        with patch('dotenv.main.os.environ',Env()):
            self.assertFalse(dotenv.load_dotenv(stream=io.StringIO('# comment\n\n'),strict=True))
            self.assertTrue(dotenv.load_dotenv(stream=io.StringIO('A\n'),strict=True))
            self.assertEqual(dotenv.dotenv_values(stream=io.StringIO('A=one\nA=${M}\nBAD=\"oops\nB=ok')),{'A':'','B':'ok'})
        with patch('dotenv.main.os.environ',{'PYTHON_DOTENV_DISABLED':'yes'}):
            self.assertFalse(dotenv.load_dotenv(stream=io.StringIO('BAD=\"oops'),strict=True))
        for interpolate in (True,False):
            with self.assertRaises(DotEnvError): self.values('A\nA\n',interpolate=interpolate)
        self.assertEqual(self.values('A=$M\nB=${M}\n',interpolate=False),{'A':'$M','B':'${M}'})

if __name__=='__main__': unittest.main(verbosity=2)


