"""Template class for adding new processors."""

class NotesProcessor:
	def process(self, notes):
		"""Process `notes`, which is a dict of {title: Note} representing all of the Notes loaded by BearNotes. Do not make any changes to the Note contents, because they might be overwritten if the contents need to be fetched from Bear. Instead, save the changes, and return a dict of {Note: changed (True/False)}, or None if no changes will be made."""
		raise NotImplementedError("Subclasses must implement process()")
		
		
	def render(self, note):
		"""This will be called once for each Note that process() indicates has changed. Return the new contents of the note."""
		raise NotImplementedError("Subclasses must implement render()")
		
		
	def __repr__(self):
		 return f"<{self.__class__.__name__}>"
