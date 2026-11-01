import io
import unittest
from unittest.mock import patch
from dotenv import dotenv_values, DotEnvError
from dotenv.main import DotEnv

class SourceQA(unittest.TestCase):
    def test_path_precedence_encoding_and_ownership(self):
        primary=io.StringIO('NAME=caf\u00e9\n')
        fallback=io.StringIO('NAME=wrong\n')
        with patch('dotenv.main._is_file_or_fifo',return_value=True), patch('builtins.open',return_value=primary) as op:
            result=dotenv_values('chosen.env',fallback,False,True,'latin-1',True)
        self.assertEqual(result,{'NAME':'caf\u00e9'})
        op.assert_called_once_with('chosen.env',encoding='latin-1')
        self.assertTrue(primary.closed);self.assertFalse(fallback.closed);self.assertEqual(fallback.tell(),0)
    def test_missing_path_stream_fallback_and_empty_cache(self):
        fallback=io.StringIO('A=ok\n')
        with patch('dotenv.main._is_file_or_fifo',return_value=False):
            self.assertEqual(dotenv_values('missing.env',stream=fallback,strict=True),{'A':'ok'})
            d=DotEnv('missing.env',strict=True)
            first=d.dict();self.assertEqual(first,{})
            with patch.object(d,'_get_stream',side_effect=AssertionError('successful empty result should cache')):
                self.assertIs(d.dict(),first)
        self.assertFalse(fallback.closed)
    def test_direct_parser_duplicate_allowed(self):
        from dotenv.parser import parse_stream
        bindings=list(parse_stream(io.StringIO('A=1\nA=2\n'),strict=True))
        self.assertEqual([x.key for x in bindings],['A','A'])
    def test_positional_public_compatibility(self):
        self.assertEqual(dotenv_values(None,io.StringIO('A=${MISSING}\n'),False,True,'utf-8'),{'A':''})
        self.assertEqual(DotEnv(None,io.StringIO('A=${MISSING}\n'),False,None,True,True).dict(),{'A':''})
        with self.assertRaises(DotEnvError):
            dotenv_values(None,io.StringIO('A=${__QA_UNLIKELY_MISSING__}\n'),False,True,'utf-8',True)

if __name__=='__main__':unittest.main(verbosity=2)
