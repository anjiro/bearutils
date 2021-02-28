"""Move tags from the end of the file to the line after the note's title."""
import re
from .notes_processor import NotesProcessor
from regexes import tag_re, eoftags_re
import logging
log = logging.getLogger(__name__)

class TagMover(NotesProcessor):
	def __init__(self, **options):
		"""Move tags from the bottom of a note to the top.
		"""
		self.options = {}
		self.options.update(options)
		
		
	def process(self, notes):
		changed = {}
		for note in notes.values():
			try:
				changed[note] = False if note.contents.count('\n') < 2 else re.search(eoftags_re, note.contents)
			except:
				print(note)
				raise
		return changed
		
	
	def render(self, note):
		lines = note.contents.splitlines()
		contents = lines[:-1]
		tags = lines[-1].strip()
		
		#If the second line of the note has tags, move the tags to the end of that line
		if re.search(tag_re, contents[1]):
			contents[1] += ' ' + tags
		#Otherwise make a new tags line
		else:
			contents.insert(1, tags+'\n')
			
		return '\n'.join(contents).strip()
