"""Read a single local download link using the CommonMark parser used by the test recipient."""
from urllib.parse import unquote, urlsplit
from markdown_it import MarkdownIt

PARSER = MarkdownIt('commonmark')


def destination(message):
    blocks = PARSER.parse(message.decode('utf-8'))
    if [token.type for token in blocks] != ['paragraph_open','inline','paragraph_close']:
        return None
    items = blocks[1].children
    if len(items)<3 or items[0].type!='link_open' or items[-1].type!='link_close':
        return None
    if sum(item.type=='link_open' for item in items)!=1:
        return None
    url = urlsplit(items[0].attrGet('href'))
    if url.scheme or url.netloc or url.fragment or url.query:
        return ''
    return unquote(url.path)
