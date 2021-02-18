from bear import NotesProcessor
from utils import *
from collections import defaultdict


class NoteActions(NotesProcessor):
	def __init__(self, **options):
		self.options = {
			'action_note': 'Bearutils actions',
			'action_section': '## Actions',
			'collect_section_title': '## Collected notes',
		}
		self.options.update(options)
		self.note_actions = defaultdict(list)
		
		#Compiled regex will be used with .search()
		self.actions = {
			re.compile('^\*\s+(?P<do>append|prepend)\s+to\s+(?P<to>titles|notes)\s+in\s+`?' + tag_re + '`?\s*:(?P<what>.+)', flags=re.I): self.append_prepend,
			
			re.compile('^\*\s+(?P<do>remove)\s+from\s+(?P<to>titles|notes)\s+in\s+`?' + tag_re + '`?\s*:(?P<what>.+)', flags=re.I): self.append_prepend,
			
			re.compile('^\*\s+collect\s+`?' + tag_re + '`?\s+in\s+\[\[(?P<dest>.+?)]]', flags=re.I): self.collect,
			
			re.compile('^\*\s+(?P<strike>-?)::(?<!\s)(?P<term>.+)(?!=\s)::(?P=strike)\s+in\s+(?P<where>everywhere|`?(?<!#)#[^\s#](?:[^#\n]*(?<!\s)#|[^#\s]+)`?|\[\[.+?]])', flags=re.I): self.search,
		}
		
		
	def process(self, notes):
		print(f'process {len(notes)} notes')
		an = notes.get(self.options['action_note'])
		if not an:
			return
			
		print("ok")

		for action in get_section(an.contents, self.options['action_section']).splitlines():
			print(action)
			for matcher, func in self.actions.items():
				match = matcher.search(action)
				if match:
					func(notes, **match.groupdict())
				
		# Don't make changes to the action file
		return {note: True for note in self.note_actions if note.title != self.options['action_section']}
		
		
	def render(self, note):
		c = note.contents
		for func in self.note_actions[note]:
			c = func(c)
		return c
		
		
	def collect(self, notes, tag, dest):
		#Here we might make a new note with no id and add it to note actions
		existing_links = notes[dest].links if dest in notes else []
		new_links = []
		
		for note in notes.values():
			if tag.strip('#') not in note.tags: continue
			if note.title == dest: continue
			if note.title in existing_links: continue
			new_links.append(note.title)
			
		links_body = '\n'.join([self.options['collect_section_title']] + [f'* [[{link}]]' for link in new_links])
		
		if dest in notes:
			note = notes[dest]
			self.note_actions[note].append(lambda c:
				replace_section(c, self.options['collect_section_title'], links_body, before="## Backlinks")[0])
		else:
			note = Note(contents=f"# {dest}\n{text}")
			self.note_actions[note].append(lambda c: c)
			

	def append_prepend(self, notes, do, to, tag, what):
		do = do.lower()
		to = to.lower()
		
		for note in notes.values():
			if tag.strip('#') not in note.tags:
				continue
			if to == 'titles':
				if do == 'append':
					print(f"append to {note.title}")
					self.note_actions[note].append(lambda c:
						re.subn('\n', what+'\n', c, count=1)[0])
				elif do == 'prepend':
					self.note_actions[note].append(lambda c:
						re.sub('^', what, c))
				elif do == 'remove' and re.match(rf'^(?:{what}|[^\n]+{what}\n)', note.title):
					self.note_actions[note].append(lambda c:
						re.sub(rf'^(?:{what}|([^\n]+){what}(?=\n))', r'\1', c))
						
						
	def search(self, notes, strike, term, where):
		for note in notes.values():
			if note.title == self.options['action_note']:
				 continue
			if (where == 'everywhere' or where.startswith('#') and where.strip('#') in note.tags or where.startswith('[[') and where == f"[[{note.title}]]") and term in note.contents:
				if strike:
					#Remove highlights
					self.note_actions[note].append(lambda c:
						re.sub(rf"::{term}::", term, c))
				else:
					#Use a lambda in sub to avoid highlighting already-highlighted terms or inside links
					self.note_actions[note].append(lambda c:
						re.sub(rf"::.+?::|\[\[[^\]]+]]|\b({term})\b", lambda m:f"::{m.group(1)}::" if m.group(1) else m.group(0), c))
