import io, inspect, unittest
from unittest.mock import patch, mock_open
import dotenv
from dotenv import main, parser, variables

class Env(dict):
    def __init__(self,*a,**kw): super().__init__(*a,**kw); self.writes=[]
    def __setitem__(self,k,v): self.writes.append((k,v)); super().__setitem__(k,v)

class QA(unittest.TestCase):
    def values(self,text,**kw): return dotenv.dotenv_values(stream=io.StringIO(text),strict=True,**kw)
    def failure(self,text,kind,index=0,**kw):
        bindings=list(parser.parse_stream(io.StringIO(text)))
        b=bindings[index]
        with self.assertRaises(dotenv.DotEnvError) as got: self.values(text,**kw)
        e=got.exception
        self.assertEqual((e.kind,e.line,e.original),(kind,b.original.line,b.original.string))
        self.assertIn(kind,str(e)); self.assertIn(str(e.line),str(e))
    def test_interfaces(self):
        for f in [main.DotEnv.__init__,dotenv.dotenv_values,dotenv.load_dotenv,parser.parse_stream,variables.parse_variables]:
            p=list(inspect.signature(f).parameters.values())[-1]
            self.assertEqual(p.name,'strict'); self.assertIs(p.default,False)
        self.assertIs(dotenv.DotEnvError,parser.DotEnvError)
        self.assertIn('DotEnvError',dotenv.__all__)
        self.assertTrue(issubclass(dotenv.DotEnvError,ValueError))
        self.assertTrue(issubclass(variables.UndefinedVariableError,ValueError))
    def test_parser_boundaries(self):
        for text in ['\n\n X="unterminated\nY=1\n','A=1\r\n\r\n X="bad" remainder\r\nZ=2\r\n',"\nA='multi\nline'\nBAD='x' junk\nC=ok\n"]:
            ordinary=list(parser.parse_stream(io.StringIO(text)))
            strict=parser.parse_stream(io.StringIO(text),True)
            for b in ordinary:
                if b.error:
                    with self.assertRaises(dotenv.DotEnvError) as got: next(strict)
                    self.assertEqual((got.exception.kind,got.exception.line,got.exception.original),('parse',b.original.line,b.original.string)); break
                self.assertEqual(next(strict),b)
        self.assertEqual([b.key for b in parser.parse_stream(io.StringIO('A=1\nA=2'),True)],['A','A'])
    def test_order_and_precedence(self):
        cases=[('A=${QA_MISSING}\nA=2\n','undefined',0),('A=1\nA=${QA_MISSING}\n','duplicate',1),('A=1\nA="x" junk\n','parse',1),('A\n\nexport A=2\n','duplicate',1),('A=1\nB=${QA_MISSING}\nA=2\n','undefined',1),('A=1\nA=2\nB="bad','duplicate',1)]
        with patch.object(main.os,'environ',{}):
            for text,kind,index in cases:
                with self.subTest(text=text): self.failure(text,kind,index)
        self.assertEqual(self.values('#c\n\nA\n#c\nB=\n'),{'A':None,'B':''})
    def test_atoms(self):
        for name in ['MISSING','', 'x-y','a b']:
            atom=list(variables.parse_variables('${'+name+'}',True))[0]
            for mapping,expected in [({name:None},''),({name:''},''),({name:'ok'},'ok')]: self.assertEqual(atom.resolve(mapping),expected)
            with self.assertRaises(variables.UndefinedVariableError) as got: atom.resolve({})
            self.assertEqual(got.exception.name,name)
            self.assertEqual(atom.resolve({name:'again'}),'again')
            default=list(variables.parse_variables('${'+name+':-fallback}',True))[0]
            self.assertEqual(default.resolve({}),'fallback'); self.assertEqual(default.resolve({name:None}),''); self.assertEqual(default.resolve({name:''}),'')
        for literal in ['$NAME','${NAME','${NAME:bad}','${NAME:=x}']:
            self.assertEqual(''.join(a.resolve({}) for a in variables.parse_variables(literal,True)),literal)
        self.assertEqual(''.join(a.resolve({}) for a in variables.parse_variables('${X:-${Y}}',True)),'${Y}')
        self.assertEqual(''.join(a.resolve({}) for a in variables.parse_variables('${X}')),'')
    def test_snapshot_and_precedence(self):
        for override,expected in [(True,'file'),(False,'before')]:
            env=Env(X='before')
            class Mutating(io.StringIO):
                def read(self,*a): env['X']='after'; return super().read(*a)
            stream=Mutating('X=file\nA=${X}\nN\nB=${N:-default}\nSELF=${SELF:-seed}\n')
            with patch.object(main.os,'environ',env):
                d=main.DotEnv(None,stream,override=override,strict=True).dict()
            self.assertEqual(d,{'X':'file','A':expected,'N':None,'B':'','SELF':'seed'})
            self.assertFalse(stream.closed)
        with patch.object(main.os,'environ',{}):
            self.failure('X=${X}\n','undefined')
            self.failure('X=${Y}\nY=later\n','undefined')
        with patch.object(main.os,'environ',{'Y':'snapshot'}): self.assertEqual(self.values('X=${Y}\nY=later\n')['X'],'snapshot')
    def test_zero_writes(self):
        for source in ['OK=yes\nBAD="x" tail\n','OK=yes\nD=1\nD=2\n','OK=yes\nSKIP=${MISSING}\n','OK=yes\nV\nV\n']:
            for override in [False,True]:
                for entry in ['load','method']:
                    env=Env(SKIP='existing')
                    with patch.object(main.os,'environ',env):
                        with self.assertRaises(dotenv.DotEnvError):
                            if entry=='load': dotenv.load_dotenv(stream=io.StringIO(source),strict=True,override=override)
                            else: main.DotEnv(None,io.StringIO(source),strict=True,override=override).set_as_environment_variables()
                    self.assertEqual(env.writes,[])
    def test_interpolation_off(self):
        self.assertEqual(self.values('X=${MISSING}\nV\n',interpolate=False),{'X':'${MISSING}','V':None})
        self.failure('X=1\nX=${MISSING}\n','duplicate',1,interpolate=False)
        self.failure('X="x" tail\n','parse',0,interpolate=False)
    def test_commit(self):
        for override in [False,True]:
            env=Env(X='old')
            with patch.object(main.os,'environ',env): self.assertTrue(dotenv.load_dotenv(stream=io.StringIO('X=new\nN\nY=${X}\n'),strict=True,override=override))
            self.assertEqual(env.writes,([('X','new'),('Y','new')] if override else [('Y','old')]))
        for source,expected in [('',False),('# comment\n',False),('N\n',True)]:
            env=Env()
            with patch.object(main.os,'environ',env): self.assertEqual(dotenv.load_dotenv(stream=io.StringIO(source),strict=True),expected)
            self.assertEqual(env.writes,[])
    def test_retry_and_cache(self):
        env=Env(); stream=io.StringIO('X=${MISSING}\n'); d=main.DotEnv(None,stream,strict=True)
        with patch.object(main.os,'environ',env):
            with self.assertRaises(dotenv.DotEnvError): d.dict()
            self.assertIsNone(d._dict); stream.seek(0); env['MISSING']='fixed'
            first=d.dict(); self.assertEqual(first,{'X':'fixed'})
            env['MISSING']='changed'; self.assertIs(d.dict(),first)
        empty=main.DotEnv(None,io.StringIO(''),strict=True); first=empty.dict(); self.assertIs(first,empty.dict())
    def test_source_and_disable(self):
        stream=io.StringIO('STREAM=1')
        with patch.object(main,'_is_file_or_fifo',return_value=True),patch('builtins.open',mock_open(read_data='PATH=2')) as op:
            self.assertEqual(main.DotEnv('some.env',stream,encoding='utf-16',strict=True).dict(),{'PATH':'2'})
            op.assert_called_once_with('some.env',encoding='utf-16')
        self.assertEqual(stream.tell(),0); self.assertFalse(stream.closed)
        with patch.object(main,'_is_file_or_fifo',return_value=False):
            self.assertEqual(main.DotEnv('missing.env',strict=True).dict(),{})
            self.assertEqual(main.DotEnv('missing.env',io.StringIO('A=1'),strict=True).dict(),{'A':'1'})
        stream=io.StringIO('BAD="unterminated')
        with patch.object(main.os,'environ',{'PYTHON_DOTENV_DISABLED':'true'}): self.assertFalse(dotenv.load_dotenv(stream=stream,strict=True))
        self.assertEqual(stream.tell(),0)
    def test_permissive(self):
        with patch.object(main.os,'environ',{}):
            with self.assertLogs(main.logger,level='WARNING'):
                self.assertEqual(dotenv.dotenv_values(stream=io.StringIO('A=1\nA=2\nBAD="x" junk\nB=${MISSING}\nV\n')),{'A':'2','B':'','V':None})

if __name__=='__main__': unittest.main(verbosity=2)
