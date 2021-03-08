import re
from .notes_processor import NotesProcessor
from regexes import tag_core
from collections import defaultdict
import logging
log = logging.getLogger(__name__)

class Appender(NotesProcessor):
	#To match this action in the Bearutils note
	action_matchers = (
		re.compile('^\*[\t ]+(?P<do>append|prepend)[\t ]+to[\t ]+(?P<to>titles|notes)[\t ]+in[\t ]+`?' + tag_core + '`?[\t ]*:(?P<what>.+)$', flags=re.I|re.M),
		re.compile('^\*[\t ]+(?P<do>remove)[\t ]+from[\t ]+(?P<to>titles|notes)[\t ]+in[\t ]+`?' + tag_core + '`?[\t ]*:(?P<what>.+)$', flags=re.I|re.M),
	)
	
	
	def __init__(self, **options):
		"""Append or prepend to notes tagged with a given tag. Currently only works with titles. Provide keyword arguments:
			do: 'append' or 'prepend'
			to: 'titles'
			tag: the desired tag to work on
			what: text to add
		"""
		self.options = {
		}
		self.options.update(options)
		self.note_actions = defaultdict(list)
		
		
	def process(self, notes):
		for note in notes.values():
			do, to, tag, what = [self.options.get(k) for k in ('do', 'to', 'tag', 'what')]
			do = do.lower()
			to = to.lower()
			
			if tag.strip('#') not in note.tags:
				continue
			if to == 'titles':
				if do == 'append' and not note.title.strip().endswith(what):
					log.info(f"append to {note.title}")
					self.note_actions[note].append(lambda c:
						re.subn('\n', what+'\n', c, count=1)[0])
				elif do == 'prepend' and not note.title.startswith(what):
					self.note_actions[note].append(lambda c:
						re.sub('^', what, c))
				elif do == 'remove' and re.match(rf'^(?:{what}|[^\n]+{what}\n)', note.title):
					self.note_actions[note].append(lambda c:
						re.sub(rf'^(?:{what}|([^\n]+){what}(?=\n))', r'\1', c))
								
		return self.note_actions
		
		
	def render(self, note):
		c = note.contents
		for func in self.note_actions[note]:
			c = func(c)
		return c
