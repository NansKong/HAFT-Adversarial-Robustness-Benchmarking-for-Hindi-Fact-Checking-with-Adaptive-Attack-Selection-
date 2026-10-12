import re

with open('naacl/acl_latex.tex', encoding='utf-8') as f:
    text = f.read()

# Strip comments
lines = [re.sub(r'(?<!\\)%.*$', '', l) for l in text.splitlines()]
clean_text = '\n'.join(lines)

# Abstract
abstract_match = re.search(r'\\begin\{abstract\}([\s\S]*?)\\end\{abstract\}', clean_text)
if abstract_match:
    ab_clean = re.sub(r'\\[a-zA-Z]+', ' ', abstract_match.group(1))
    ab_words = len(re.findall(r'\b[A-Za-z0-9_-]+\b', ab_clean))
    print(f'Abstract: {ab_words} words')

# Sections
sections = re.split(r'\\section\*?\{([^}]+)\}', clean_text)
total_words = 0
main_body_words = 0

for i in range(1, len(sections), 2):
    title = sections[i]
    content = sections[i+1]
    
    clean_content = re.sub(r'\\[a-zA-Z]+(?:\[[^\]]*\])?(?:\{[^}]*\})*', ' ', content)
    words = len(re.findall(r'\b[A-Za-z0-9_-]+\b', clean_content))
    total_words += words
    
    is_main = title.lower() not in ['limitations', 'ethics statement', 'acknowledgments', 'references']
    if is_main:
        main_body_words += words
    print(f'Section "{title}": {words} words (Main body: {is_main})')

print('-' * 40)
print(f'Main body word count (Sections 1-6): {main_body_words} words')
print(f'Total body word count (including Limitations & Ethics): {total_words} words')
