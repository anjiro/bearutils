import re
from urllib.parse import quote
from utils import replace_section


class TOC:
	def __init__(self, **options):
		self.options = {
			'toc_heading': '## Table of contents',
			'toc_placeholder': '## TOC',   # Shorthand to indicate a place for a new TOC
			'exclude_headers': [],
		}
		self.options.update(options)
		self.changed = {}
		self.rendered_tocs = {}

	def process(self, notes):
		for note in notes.values():
			self.changed[note] = self.render_toc(note)
		return self.changed
	
	
	def render_toc(self, note):
		"""Render the table of contents for the given note and return True.
		If no TOC was requested or generated, return False."""
		#Should we generate a TOC? Look for an existing TOC or the placeholder header.
		if not (self.options['toc_placeholder'] in note.headers or
						self.options['toc_heading'] in note.headers):
			return False
			
		excludes = [h.strip() for h in self.options['exclude_headers']]
		excludes.extend((self.options['toc_heading'], self.options['toc_placeholder']))
			
		r = [self.options['toc_heading']]
		for h in note.headers.values():
			#Skip the TOC headers and any others requested
			if h.header in excludes:
				continue
				
			r.append("\t"*(h.level-2) + f'* [{h.title}](bear://x-callback-url/open-note?id={note.id}&header={quote(h.title)})')

		if len(r) <= 1:
			print('no items')
			return False
			
		self.rendered_tocs[note] = '\n'.join(r) + '\n'
		return True
		
		
	def render(self, note):
		if self.options['toc_placeholder'] in note.headers:
			return replace_section(note.contents, self.options['toc_placeholder'], self.rendered_tocs[note], -1)[0]
		elif self.options['toc_heading'] in note.headers:
			return replace_section(note.contents, self.options['toc_heading'], self.rendered_tocs[note])[0]
