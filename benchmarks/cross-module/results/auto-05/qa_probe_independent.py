import io
import inspect
import os
import unittest
from unittest.mock import patch
import dotenv
from dotenv import DotEnvError, dotenv_values, load_dotenv
from dotenv.main import DotEnv
from dotenv.parser import parse_stream
from dotenv.variables import parse_variables, UndefinedVariableError

class Tracking(dict):
    def __init__(self, *a):
        super().__init__(*a); self.writes=[]
    def __setitem__(self,k,v):
        self.writes.append((k,v)); super().__setitem__(k,v)

class QA(unittest.TestCase):
    def values(self, text, **kw):
        return dotenv_values(stream=io.StringIO(text), strict=True, **kw)
    def check_error(self, text, kind, index, **kw):
        b=list(parse_stream(io.StringIO(text)))[index]
        with self.assertRaises(DotEnvError) as cm: self.values(text, **kw)
        e=cm.exception
        self.assertEqual((e.kind,e.line,e.original),(kind,b.original.line,b.original.string))
        self.assertIn(kind,str(e)); self.assertIn(str(b.original.line),str(e))
    def test_interfaces(self):
        self.assertIs(dotenv.DotEnvError,DotEnvError)
        self.assertIn('DotEnvError',dotenv.__all__)
        self.assertTrue(issubclass(DotEnvError,ValueError))
        self.assertTrue(issubclass(UndefinedVariableError,ValueError))
        for f in [DotEnv.__init__, dotenv_values, load_dotenv, parse_stream, parse_variables]:
            p=list(inspect.signature(f).parameters.values())[-1]
            self.assertEqual((p.name,p.default),('strict',False))
    def test_exact_parser_context_and_recovery(self):
        for ending in ['\n','\r','\r\n']:
            for bad in ['invalid key=bad', 'A="unterminated', '=oops', "A='valid' garbage"]:
                text=ending+'GOOD="a'+ending+'b"'+ending+ending+' '+bad+ending+'LATER=x'+ending
                permissive=list(parse_stream(io.StringIO(text)))
                broken=next(x for x in permissive if x.error)
                it=parse_stream(io.StringIO(text),True)
                self.assertEqual(next(it),permissive[0])
                with self.assertRaises(DotEnvError) as cm:list(it)
                self.assertEqual((cm.exception.kind,cm.exception.line,cm.exception.original),('parse',broken.original.line,broken.original.string))
                self.assertEqual(permissive[-1].key,'LATER')
    def test_precedence_source_order(self):
        with patch.dict(os.environ,{},clear=True):
            cases=[('A=1\n\n export A=${MISSING}\n','duplicate',1),
                   ('A\nA\n','duplicate',1),
                   ("'A'=one\nA=two\n",'duplicate',1),
                   ('A=one\nA="ok" garbage\n','parse',1),
                   ('A=${MISSING}\nA=x\nBROKEN bad\n','undefined',0),
                   ('A=one\nA=two\nB=${MISSING}\n','duplicate',1),
                   ('BAD key\nA=${MISSING}\n','parse',0),
                   ('# c\n\nA="multi\n${MISSING}"\n','undefined',1)]
            for text,kind,index in cases:
                with self.subTest(text=text):self.check_error(text,kind,index)
    def test_strict_atoms(self):
        for name in ['K','','spaced name','A-B']:
            atom=list(parse_variables('${'+name+'}',True))[0]
            for mapping in [{}, {name:None}, {name:''}, {name:'value'}]:
                with self.subTest(name=name,mapping=mapping):
                    if name not in mapping:
                        with self.assertRaises(UndefinedVariableError) as cm:atom.resolve(mapping)
                        self.assertEqual(cm.exception.name,name)
                    else:self.assertEqual(atom.resolve(mapping),mapping[name] or '')
            self.assertEqual(atom.resolve({name:'again'}),'again')
            default=list(parse_variables('${'+name+':-literal}',True))[0]
            self.assertEqual(default.resolve({}),'literal')
            self.assertEqual(default.resolve({name:None}),'')
            self.assertEqual(default.resolve({name:''}),'')
        for value in ['$K','${K:bad}','${K','plain','${K:-${OTHER}}']:
            strict=list(parse_variables(value,True)); loose=list(parse_variables(value))
            self.assertEqual(''.join(a.resolve({}) for a in strict),''.join(a.resolve({}) for a in loose))
    def test_resolution_override_and_self_forward(self):
        for override in [False,True]:
            with patch.dict(os.environ,{'A':'os','SELF':'prior'},clear=True):
                d=DotEnv(None,io.StringIO('A=file\nB=${A}\nSELF=${SELF}\nN\nEMPTY=\nC=${N:-fallback}:${EMPTY:-fallback}\n'),override=override,strict=True).dict()
                self.assertEqual(list(d),['A','B','SELF','N','EMPTY','C'])
                self.assertEqual(d['B'],'file' if override else 'os')
                self.assertEqual(d['SELF'],'prior'); self.assertIsNone(d['N']);self.assertEqual(d['C'],':')
        with patch.dict(os.environ,{},clear=True):
            for text in ['A=${A}\n','A=${B}\nB=one\n']:
                self.check_error(text,'undefined',0)
    def test_environment_snapshot_before_read(self):
        for override in [True,False]:
            environment=Tracking({'A':'before'})
            class Mutating(io.StringIO):
                def read(self,*a):
                    environment['A']='after'; environment['NEW']='late'
                    return super().read(*a)
            with patch('dotenv.main.os.environ',environment):
                d=DotEnv(None,Mutating('B=${A}\nC=${NEW:-absent}\n'),override=override,strict=True).dict()
            self.assertEqual(d,{'B':'before','C':'absent'})
    def test_transaction_all_failures_and_skipped_keys(self):
        cases=[('FIRST=ok\nBAD key\n','parse'),('FIRST=ok\nSKIP=ok\nSKIP=again\n','duplicate'),('FIRST=ok\nSKIP=${MISSING}\n','undefined')]
        for override in [True,False]:
            for text,kind in cases:
                for direct in [True,False]:
                    env=Tracking({'SKIP':'existing'})
                    with patch('dotenv.main.os.environ',env):
                        with self.assertRaises(DotEnvError) as cm:
                            if direct:DotEnv(None,io.StringIO(text),override=override,strict=True).set_as_environment_variables()
                            else:load_dotenv(stream=io.StringIO(text),override=override,strict=True)
                    self.assertEqual(cm.exception.kind,kind);self.assertEqual(env.writes,[])
                    self.assertEqual(env,{'SKIP':'existing'})
    def test_noninterpolation_and_success_returns(self):
        for text,kind in [('A\nA=x\n','duplicate'),('BAD key\n','parse')]:self.check_error(text,kind,1 if kind=='duplicate' else 0,interpolate=False)
        self.assertEqual(self.values('A=${MISSING}\n',interpolate=False),{'A':'${MISSING}'})
        for text,expected in [('',False),('# comment\n',False),('N\n',True),('A=one\n',True)]:
            env=Tracking({})
            with patch('dotenv.main.os.environ',env): self.assertIs(load_dotenv(stream=io.StringIO(text),strict=True),expected)
            self.assertEqual(env.writes,[('A','one')] if text.startswith('A=') else [])
        for override in [False,True]:
            env=Tracking({'A':'os'})
            with patch('dotenv.main.os.environ',env):self.assertTrue(load_dotenv(stream=io.StringIO('A=file\nB=second\n'),strict=True,override=override))
            self.assertEqual(env,{'A':'file' if override else 'os','B':'second'})
    def test_cache_failure_and_success(self):
        stream=io.StringIO('A=${MISSING}\n')
        d=DotEnv(None,stream,strict=True)
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(DotEnvError): d.dict()
            self.assertIsNone(d._dict)
            stream.seek(0);stream.truncate();stream.write('A=good\n');stream.seek(0)
            result=d.dict()
            stream.seek(0);stream.truncate();stream.write('BROKEN key\n');stream.seek(0)
            self.assertIs(d.dict(),result)
            self.assertEqual(result,{'A':'good'})
            self.assertFalse(stream.closed)
    def test_permissive_and_disabled(self):
        with patch.dict(os.environ,{},clear=True):
            for strict in [False,None]:
                kw={} if strict is None else {'strict':False}
                result=dotenv_values(stream=io.StringIO('A=first\nBAD key\nA=${MISSING}\n'),**kw)
                self.assertEqual(result,{'A':''})
        with patch.dict(os.environ,{'PYTHON_DOTENV_DISABLED':'true'},clear=True):
            s=io.StringIO('BAD key\n')
            self.assertFalse(load_dotenv(stream=s,strict=True));self.assertEqual(s.tell(),0)

if __name__=='__main__':unittest.main(verbosity=2)
