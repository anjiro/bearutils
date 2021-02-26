import re
from bear import NotesProcessor
from utils import tag_re
from collections import defaultdict

class Highlighter(NotesProcessor):
	#To match this action in the Bearutils note
	action_matchers = [re.compile('^\*[\t ]+(?P<remove>-?)::(?<![\t ])(?P<term>.+)(?!=[\t ])::(?P=remove)[\t ]+in[\t ]+(?P<where>everywhere|`?(?<!#)#[^[\t ]#](?:[^#\n]*(?<![\t ])#|[^#[\t ]]+)`?|\[\[.+?]][\t ]*$)', flags=re.I|re.M)]
	
	def __init__(self,
		term:{'type': 'text', 'title': 'Search for: ', 'placeholder': 'search term'},
		remove:{'type': 'switch', 'title': 'Remove highlights?', 'value': False},
		where='everywhere',
		**options):
		"""Highlight or remove highlights matching a search term. Arguments:
			term: the search term
			where: a tag, note title, or "everywhere"
			remove: if True, remove highlights matching the search term
		"""
		self.options = {'term': term, 'remove': remove, 'where': where}
		self.options.update(options)
		self.note_actions = defaultdict(list)
		
		
	def process(self, notes):
		term = self.options['term']
		where = self.options['where']
		remove = self.options['remove']
		
		for note in notes.values():
			if note.title == self.options['all_options']['Actions']['actions_note']:
				 continue
			if (where == 'everywhere' or where.startswith('#') and where.strip('#') in note.tags or where == f"[[{note.title}]]" or where == note.title) and term in note.contents:
				if remove:
					#Remove highlights
					self.note_actions[note].append(lambda c:
						re.sub(rf"::{term}::", term, c))
				else:
					#Use a lambda in sub to avoid highlighting already-highlighted terms or inside links
					self.note_actions[note].append(lambda c:
						re.sub(rf"::.+?::|\[\[[^\]]+]]|\b({term})\b", lambda m:f"::{m.group(1)}::" if m.group(1) else m.group(0), c))
						
		return self.note_actions
						
						
	def render(self, note):
		c = note.contents
		for func in self.note_actions[note]:
			c = func(c)
		return c
