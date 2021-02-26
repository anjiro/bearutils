#Match Bear tags
tag_re = r'(?:(?:^|(?<=\s))(?P<tag>#[^\s#][^#\n]*(?<!\s)#|#[^#\s]+)(?=$|\s))'

#Match a header; format using re.escape
header_re = r'^{header}(?:[\t ]*\n)'

#Match a note title, even if without hashes
title_re = r'^(?:#+[\t ]+)?(?P<title>[^\n]+)[\t ]*(?:\n|$)'

#Match links
link_re = r'\[\[(?P<link>[^\s\]][^\]]*)(?<!\s)]]'

#Match tags at the end of a note
eoftags_re = r'\n[\t ]*(' + tag_re + r'[\t ]*)+$'
