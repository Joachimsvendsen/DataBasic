import unittest, logging, time, codecs, os
import databasic.logic.filehandler as filehandler

class FileHandlerTest(unittest.TestCase):

    def setUp(self):
        self._fixtures_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),"fixtures")

    def test_write_to_temp_file(self):
        timestr = time.strftime("%Y%m%d-%H%M%S")
        data_to_write = "this is some data on %s" % timestr
        file_path = filehandler.write_to_temp_file(data_to_write)
        logging.info("Wrote to %s" % file_path)
        with codecs.open(file_path, 'r', filehandler.ENCODING_UTF_8) as f:
            data_as_written = f.read()
            self.assertEqual(data_as_written, data_to_write)

    def test_convert_to_txt_utf8(self):
        fixture_path = os.path.join(self._fixtures_dir,'utf-8.txt')
        text = filehandler.convert_to_txt(fixture_path) 
        self.assertEqual(len(text),7159)

    def test_convert_to_txt_latin1(self):
        fixture_path = os.path.join(self._fixtures_dir,'latin-1.txt')
        text = filehandler.convert_to_txt(fixture_path) 
        self.assertEqual(len(text),860)
