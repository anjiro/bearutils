from bear import NotesProcessor
from utils import *
from collections import defaultdict


class NoteActions(NotesProcessor):
	def __init__(self, **options):
		self.options = {
			'action_note': 'Bearutils actions',
			'always_section': '## Always',
			'search_section': '## Searches',
			'clear_section': '### Uncheck to clear highlights',
		}
		self.options.update(options)
		self.note_actions = defaultdict(list)
		
		#Compiled regex will be used with .search()
		self.actions = {
			re.compile('^\*\s+(?P<do>append|prepend)\s+to\s+(?P<to>titles|notes)\s+in\s+`?' + tag_re + '`?\s*:(?P<what>.+)', flags=re.I): self.append_prepend,
			
			re.compile('^\*\s+collect\s+`?' + tag_re + '`?\s+in\s+\[\[(?P<dest>.+?)]]', flags=re.I): self.collect,
			
			re.compile('^\*\s+(?P<strike>-?)::(?<!\s)(?P<term>.+)(?!=\s)::(?P=strike)\s+in\s+(?P<where>everywhere|`?(?<!#)#[^\s#](?:[^#\n]*(?<!\s)#|[^#\s]+)`?|\[\[.+?]])', flags=re.I): self.search,
		}
		
		
	def process(self, notes):
		print(f'process {len(notes)} notes')
		an = notes.get(self.options['action_note'])
		if not an:
			return
			
		print("ok")

		for action in get_section(an.contents, self.options['always_section']).splitlines():
			print(action)
			for matcher, func in self.actions.items():
				match = matcher.search(action)
				if match:
					print(match, match.groupdict())
					func(match, notes)
				
		return {note: True for note in self.note_actions}
		
		
	def render(self, note):
		c = note.contents
		for func in self.note_actions[note]:
			print('action:')
			print(c)
			c = func(c)
		return c
		
		
	def collect(self, match, notes):
		#Here we might make a new note with no id and add it to note actions
		pass
		

	def append_prepend(self, match, notes):
		do, to, tag, what = match.group(*'do to tag what'.split())
		do = do.lower()
		to = to.lower()
		
		print(f"got {len(notes)}")
		
		for note in notes.values():
			if tag.strip('#') not in note.tags:
				continue
			if to == 'titles':
				if do == 'append':
					print(f"append to {note.title}")
					self.note_actions[note].append(lambda c:
						re.subn('\n', what+'\n', c, count=1))
				elif do == 'prepend':
					self.note_actions[note].append(lambda c:
						re.sub('^', what, c))
						
						
	def search(self, match, notes):
		strike, term, where = match.group(*'strike term where'.split())
		for note in notes.values():
			if note.title == self.options['action_note']:
				 continue
			if (where == 'everywhere' or where.startswith('#') and where.strip('#') in note.tags or where.startswith('[[') and match.group('link') == note.title) and term in note.contents:
				if strike:
					#Remove highlights
					self.note_actions[note].append(lambda c:
						re.sub(rf"\b::{term}::\b", term, c))
				else:
					#Use a lambda in sub to avoid highlighting already-highlighted terms or inside links
					self.note_actions[note].append(lambda c:
						re.sub(rf"::{term}::|\[\[[^\]]+]]|\b({term})\b", lambda m:"::\1::" if m.group(1) else m.group(0), c))
