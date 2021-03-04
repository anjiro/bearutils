import re
from collections import defaultdict
from regexes import list_re
from .notes_processor import NotesProcessor
import logging
log = logging.getLogger(__name__)

class Indenter(NotesProcessor):
	def __init__(self, **options):
		self.options = {
			'indent': '-->',
			'dedent': '<--',
		}
		self.options.update(options)
		
		i = self.options['indent']
		d = self.options['dedent']
		self.matcher = re.compile(list_re + rf'(?P<marker>{i}|{d}).*?(?P=marker)(?=\n|$)', flags=re.DOTALL)

		
	def process(self, notes):
		return {note: bool(self.matcher.search(note.contents)) for note in notes.values()}
		
			
			
	def render(self, note):
		return self.matcher.sub(
			lambda m:re.sub(m.group('marker'), '',
				re.sub('^', '\t', m.group(0), flags=re.M) if m.group('marker') == self.options['indent'] else
				re.sub('^\t', '', m.group(0), flags=re.M)),
			note.contents)
