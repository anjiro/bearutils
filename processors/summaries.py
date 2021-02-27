"""IN PROGRESS, NOT CURRENTLY WORKING

Adds summaries defined in individual notes to links in other notes. A summary is a single paragraph starting with *Summary:*, as in this example:
	
	 # Here is a note
	 
	 *Summary:* here is a summary. This note is good.
	 
	 Here is some other text.
	  
Summaries will be added when a request to generate summaries is encountered. See options; the default is to summarize a single link followed by an arrow:
	
	[[Here is a note]] ->

will be transformed:
	
	[[Here is a note]] -> here is a summary. This note is good.
	
and to summarize all links in a section with "!s" after the section heading:
	
	## Here is a section
	!s
	
	[[Here is a note]]
	
which will be similarly transformed:
	
	## Here is a section
	!s
	
	[[Here is a note]] -> here is a summary. This note is good.
	
To avoid over-writing existing text, the script will only add summaries when the link is at the end of a line. This means that summaries will not be updated if they have changed.
"""
import re
from .notes_processor import NotesProcessor
from utils import link_re
from collections import defaultdict

summary_re: r'^[\t ]*\*Summary:\*[\t ]+(?P<summary>.+)\n\n'

class Summarizer(NotesProcessor):
	def __init__(self, **options):
		self.options = {
			'summarize_link_request': ' -> ', #after a link to add summary
			'summarize_sect_request': '!s', #at start of section to summarize all links in section following
			'summary_style': ' -> {summary}'
			'bullet_summary_style': '\n\t* {summary}'
		}
		self.options.update(options)
		self.changed = {}
		self.summaries = {}
		
		
	def find_links_to_summarize(self, note):
		r = []
		for match in re.finditer(link_re + re.escape(self.options['summarize_link_request']) + r'[\t ]*$', note.contents, flags=re.MULTILINE):
			if notes[match.group('link')].summary:
				r.append((match.group('link'), match.span()))
		for match in re.finditer(rf'^(?P<header>#+[\t ]*.+\n[\t ]*{self.options["summarize_sect_request"]}[\t ]*\n', note.contents, flags=re.MULTILINE):
		

		
	def process(self, notes):
		for note in notes.values():
			match = re.search(summary_re, note.contents, flags=re.MULTILINE|re.DOTALL)
			if match:
				self.summaries[note.title] = match.group('summary')
			
			
			
					
			for link in note.links:
				if notes[link].summary:
					self.summaries[note][]
		
		
	def render(self, note):
