import re
from urllib.parse import quote
from utils import replace_section
from bear import NotesProcessor


class TOC(NotesProcessor):
	def __init__(self, **options):
		self.options = {
			'toc_heading': '## Table of contents',
			'toc_placeholder': '## TOC',   # Shorthand to indicate a place for a new TOC
			'exclude_headers': [],
			'min_level': 2,  #Don't add headers with < n #s; set to <= 0 for all
			'max_level': 0,  # Same but don't add for more
		}
		self.options.update(options)
		self.changed = {}
		self.rendered_tocs = {}
		

	def process(self, notes):
		for note in notes.values():
			self.changed[note] = self.render_toc(note)
		return self.changed
	
	
	def render_toc(self, note):
		"""Render the table of contents for the given note. Return False if no TOC was requested or if the generated TOC is identical to the existing one; otherwise return True."""
		#Should we generate a TOC? Look for an existing TOC or the placeholder header.
		if not (self.options['toc_placeholder'] in note.headers or
						self.options['toc_heading'] in note.headers):
			return False
			
		excludes = [h.strip() for h in self.options['exclude_headers']]
		excludes.extend((self.options['toc_heading'], self.options['toc_placeholder']))
			
		r = [self.options['toc_heading']]
		for h in note.headers.values():
			#Skip the TOC headers and any others requested
			if h.header in excludes or (0 < self.options['min_level'] > h.level) or (0 < self.options['max_level'] < h.level):
				continue
				
			r.append("\t"*(h.level-2) + f'* [{h.title}](bear://x-callback-url/open-note?id={note.id}&header={quote(h.title)})')

		if len(r) <= 1:
			print('no items')
			return False
			
		self.rendered_tocs[note] = '\n'.join(r)
		
		#If there's a placeholder, we'll be adding a TOC
		if self.options['toc_placeholder'] in note.headers:
			return True
		
		#Use replace_section to extract the old TOC and compare; not actually making any changes to the note.
		if replace_section(note.contents, self.options['toc_heading'], self.rendered_tocs[note])[1] == self.rendered_tocs[note]:
			return False
			
		return True
		
		
	def render(self, note):
		if self.options['toc_placeholder'] in note.headers:
			return replace_section(note.contents, self.options['toc_placeholder'], self.rendered_tocs[note], -1)[0]
		elif self.options['toc_heading'] in note.headers:
			return replace_section(note.contents, self.options['toc_heading'], self.rendered_tocs[note])[0]
