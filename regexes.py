#Match Bear tags
tag_core = r'(?P<tag>#[^\s#][^#\n]*(?<!\s)#|#[^#\s]+)'
tag_re = r'(?:(?:^|(?<=\s))' + tag_core + r'(?=$|\s))'

#Match a header; format using re.escape
header_re = r'^{header}(?:[\t ]*\n)'

#Match a note title, even if without hashes
title_re = r'^(?:#+[\t ]+)?(?P<title>[^\n]+)[\t ]*(?:\n|$)'

#Match links
link_re = r'\[\[(?P<link>[^\s\]][^\]]*)(?<!\s)]]'

#Match tags at the end of a note
eoftags_re = r'\n[\t ]*(' + tag_re + r'[\t ]*)+$'

#Match list entries
list_re = r'(?<=\n)(?P<tabs>\t*)(?P<bullet>[*\-]|\d+\.)[\t ]+'
