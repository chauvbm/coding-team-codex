import io
import unittest
from unittest.mock import patch
from dotenv import dotenv_values
from dotenv.main import DotEnv
from dotenv.parser import parse_stream

class QAIO(unittest.TestCase):
    def test_path_precedence_and_encoding(self):
        supplied=io.StringIO('A=stream')
        disk=io.StringIO('A=caf\u00e9')
        with patch('dotenv.main._is_file_or_fifo',return_value=True),patch('builtins.open',return_value=disk) as opened:
            self.assertEqual(dotenv_values('relative.env',supplied,encoding='latin-1',strict=True),{'A':'caf\u00e9'})
        opened.assert_called_once_with('relative.env',encoding='latin-1')
        self.assertTrue(disk.closed); self.assertFalse(supplied.closed); self.assertEqual(supplied.tell(),0)
    def test_missing_fallback_and_stream_ownership(self):
        for strict in (True,False):
            with patch('dotenv.main._is_file_or_fifo',return_value=False):
                stream=io.StringIO('A=x')
                self.assertEqual(dotenv_values('missing.env',stream,strict=strict),{'A':'x'})
                self.assertFalse(stream.closed)
                self.assertEqual(dotenv_values('missing.env',strict=strict),{})
                self.assertFalse(DotEnv('missing.env',strict=strict).set_as_environment_variables())
    def test_parser_recovery_and_false_default_match(self):
        s='A=x\nBAD=\"oops\nB=y\n'
        expected=list(parse_stream(io.StringIO(s)))
        self.assertEqual(expected,list(parse_stream(io.StringIO(s),False)))
        self.assertTrue(expected[1].error); self.assertEqual(expected[2].key,'B')

if __name__=='__main__': unittest.main(verbosity=2)
