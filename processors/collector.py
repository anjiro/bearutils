import re
from .notes_processor import NotesProcessor
from utils import tag_re, replace_section
from collections import defaultdict

class Collector(NotesProcessor):
	#To match this action in the Bearutils note
	action_matchers = [re.compile('^\*[\t ]+collect[\t ]+`?' + tag_re + '`?[\t ]+in[\t ]+\[\[(?P<dest>.+?)]][\t ]*$', flags=re.I|re.M)]
	
	def __init__(self, **options):
		"""Collect links to notes with a given tag in a specified note, in a given section. Don't add links that already exist anywhere in the note. Provide keyword arguments:
		tag: the tag to collect
		dest: the title of the note in which to collect the links
		"""
		self.options = {
		}
		self.options.update(options)
		self.note_actions = defaultdict(list)
		
		
	def process(self, notes):
		tag = self.options['tag'].strip('#')
		dest = self.options['dest']
		existing_links = notes[dest].links if dest in notes else []
		new_links = []
		
		for note in notes.values():
			if tag not in note.tags: continue
			if note.title == dest: continue
			if note.title in existing_links: continue
			new_links.append(note.title)
			
		links_body = '\n'.join([self.options['collect_section_title']] + [f'* [[{link}]]' for link in new_links])
		
		if dest in notes:
			note = notes[dest]
			self.note_actions[note].append(lambda c:
				replace_section(c, self.options['collect_section_title'], links_body, before="## Backlinks")[0])
		else:
			note = Note(contents=f"# {dest}\n\n{links_body}")
			self.note_actions[note].append(lambda c: c)
			
		return self.note_actions
			
			
	def render(self, note):
		c = note.contents
		for func in self.note_actions[note]:
			c = func(c)
		return c
