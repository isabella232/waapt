from __future__ import division
import urllib, os.path, collections, cPickle, math, itertools
from time import sleep
from lxml import etree

debug = {}

originalNames = {}

Post = collections.namedtuple("Post", ["name", "date", "troper", "text", "youtube"])
ThreadInfo = collections.namedtuple("ThreadInfo", ["url","id"])

info_WAAPT = ThreadInfo('http://tvtropes.org/pmwiki/posts.php?discussion=12971269370A74820100&page=', 'WAAPT')
info_Discussion = ThreadInfo('http://tvtropes.org/pmwiki/posts.php?discussion=13029586310A25120100&page=', 'Discussion')
info_PEFE = ThreadInfo('http://tvtropes.org/pmwiki/posts.php?discussion=rmvjixctp256gfq3p86y66ma&page=', 'PEFE')
info_Signups = ThreadInfo('http://tvtropes.org/pmwiki/posts.php?discussion=13555917160A75440100&page=', 'Signups')

#Dead threads to archive
info_BigCity = ThreadInfo('http://tvtropes.org/pmwiki/posts.php?discussion=12986677560A13620100&page=', 'BigCity')
info_BCDiscussion = ThreadInfo('http://tvtropes.org/pmwiki/posts.php?discussion=12986677640A07660100&page=', 'BCDiscussion')
info_BCSignups = ThreadInfo('http://tvtropes.org/pmwiki/posts.php?discussion=12985820890A41646300&page=', 'BCSignups')
info_PTRP = ThreadInfo('http://tvtropes.org/pmwiki/posts.php?discussion=13485251810A33860100&page=', 'PTRP')
info_PTRPDiscussion = ThreadInfo('http://tvtropes.org/pmwiki/posts.php?discussion=13485012860A22580400&page=', 'PTRPDiscussion')
info_PTRPSignups = ThreadInfo('http://tvtropes.org/pmwiki/posts.php?discussion=13477335210A92760100&page=', 'PTRPSignups')

def storePickle(obj, name):
    with open(os.path.join('Pickle', name), 'wb') as f:
        cPickle.dump(obj, f), -1

def getPickle(name):
    try:
        # with open(os.path.join('Pickle_old', name), 'rb') as f:
        with open(os.path.join('Pickle', name), 'rb') as f:
            return cPickle.load(f)
    except IOError:
        return None

def downloadSite(url, filename):
    sleep(1) #prevent accidently sending too much traffic to the poor server
    webf = urllib.urlopen(url)
    with open(filename, 'wb') as f:
        f.write(webf.read())

def downloadPage(num, info):
    assert(num >= 1)
    filename = os.path.join('DownloadedPages' + info.id, str(num) + '.html')
    if not os.path.isfile(filename):
        downloadSite(info.url + str(num), filename)
    return filename

def downloadRange(start, stop, info=info_WAAPT):
    for count in range(start, stop + 1):
        downloadPage(count, info)

def cannonizeName(name):
    return name.replace(' ','').lower()

def redlinkText(child):
    text = child.text
    link = child.attrib['href']
    i = link.find('/Main/')
    ltext = link[i+6:]
    if i >= 0 and ltext.lower() == text.lower().replace(' ',''):
        return ltext
    return text

def hasClass(node, cls):
    return cls in node.attrib.get('class', '').split()

def getPostBodyText(text, element):
    if element.tag == 'div':
        if element.attrib.get('class','').strip() in ('forumimageholder', 'forumtitle', 'forumsigline'):
            if element.tail:
                text.append(element.tail)
            return
    # for sub in element.findall('div'):
    #     if hasClass(sub, 'forumtext'):
    #         return getPostBodyText(text, sub)

    editedLine = element.attrib.get('style') == "font-size:x-small;font-style:italic;"
    editedLine = editedLine and element.tag == 'p' and 'edited ' in element.text
    if editedLine:
        raise StopIteration

    if not hasClass(element, 'quoteblock'):
        if element.text:
            text.append(element.text)
        for child in element:
            getPostBodyText(text, child)

    if element.tag == 'p':
        text.append('\n')
    if element.tail:
        text.append(element.tail)

# def old_getPostBodyText(text, element):
#     editedLine = element.attrib.get('style') == "font-size:x-small;font-style:italic;"
#     editedLine = editedLine and element.tag == 'p' and 'edited ' in element.text
#     if editedLine:
#         raise StopIteration

#     if element.tag != 'div' or hasClass(element, 'forumreplybody'):
#         for child in element:
#             getPostBodyText(text, child)
#     if element.tag == 'p' and not element.text:
#         text.append('\n')
#     if element.tag != 'div' and element.text:
#     #special check for accidental redlinks
#         if element.tag == 'a' and hasClass(element, 'createlink'):
#             text.append(redlinkText(element))
#         elif element.text:
#             text.append(element.text)
#     if element.tail:
#         text.append(element.tail)

def getPostData(head, body):
    if head[0].tag == 'div': #an extra div was added to headers partway through
        head = head[0]
    name = head[0].attrib['name']

    #Skip Herald icon
    offset = head.index([x for x in head.findall('a') if x.text][1])
    orig_troper = head[offset].text
    #store it in lower case without spaces, since a name can be capitalized arbitrarily
    troper = cannonizeName(orig_troper)
    # if troper not in originalNames:
    #     originalNames[troper] = orig_troper

    dateTitle = head[offset + 1].attrib['title']
    date = dateTitle[(dateTitle.find('post on ') + len('post on ')):]

    text = []
    try:
        getPostBodyText(text, body)
    except StopIteration:
        pass
    alltext = ''.join(s.encode('utf8') for s in text)
    return Post(int(name), date, troper, alltext, tuple(getYoutubeLinks(body)))

def getYoutubeLinks(body):
    for ele in body.iter('iframe'):
        src = ele.attrib.get('src')
        if src and 'youtube' in src.lower():
            yield src

def parsePageSub(fname):
    tree = etree.parse(fname, etree.HTMLParser())
    # body = tree.getroot().find('body')
    # firstLvl = body[0] if 'class' in body[0].attrib else body[1] #skip SOPA banner
    # table = firstLvl.find('table') #skip stupid announcement banner

    # if table is not None:
    #     container = table[0].findall('td')[-1]
    # else: #pages 12172 - 12209
    #     container = firstLvl
    # divs = list(container.findall('div'))

    parent_map = {c:p for p in tree.iter() for c in p}
    head1 = [d for d in tree.iter('div') if hasClass(d, 'forumreplyheader')][0]
    container = parent_map[head1]
    divs = list(container.findall('div'))



    headers = [d for d in divs if hasClass(d, 'forumreplyheader')]
    bodies = [d for d in divs if hasClass(d, 'forumreplybody')]

    assert(len(headers) == len(bodies))
    return map(getPostData, headers, bodies)

def parsePage(num, thread):
    results = parsePageSub(downloadPage(num, thread))
    assert(len(results) == 25)
    return results


def testWalk(element, indent=''):
    print indent + str(element.tag), element.attrib, element.text
    for child in element:
        testWalk(child, indent+' ')

# link = lambda num: "{0}{1}#{2}".format(info_WA.url, (num-1)//25+1, num )
# bblink = lambda num: "[[{0}{1}#{2} {2}]]".format(info_WA.url, (num-1)//25+1, num )
def link(num, thread):
    return "http://tvtropes.org/pmwiki/posts.php?discussion={}&page={}#{}".format(thread, (num-1)//25+1, num)

def getStringFromPost(post):
    text = post.text.strip()
    charsToRemove = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
    charsToRemove += u'\u2014' + u'\u25ca' #emdash, lozenge
    text = "".join(c for c in text if c not in frozenset(charsToRemove))
    return text.lower()

getWordsFromPost = lambda post: getStringFromPost(post).split()

def getPostIterSub(pageS, pageE=None, thread=info_WAAPT):
    #allow them to specify only an end page to start from page 1
    if not pageE:
        pageS, pageE = 1, pageS

    CHUNKSIZE = 200
    for pg in range((pageS-1)//CHUNKSIZE, (pageE-2)//CHUNKSIZE+1):
        sOff = max((pageS-1-pg*CHUNKSIZE,0))
        eOff = min((pageE-1-pg*CHUNKSIZE,CHUNKSIZE))
        sectionS, sectionE = sOff+1+pg*CHUNKSIZE, eOff+1+pg*CHUNKSIZE
        fname = 'postlist{}_{}_{}'.format(thread.id, pg*CHUNKSIZE+1,(pg+1)*CHUNKSIZE)
        cached = getPickle(fname)
        if cached:
            yield cached[sOff*25:eOff*25]
            print '{0}-{1} retrieved from cache'.format(sectionS, sectionE-1)
        else:
            temp = []
            for i in range(sectionS, sectionE):
                temp.extend(parsePage(i, thread))
                print i,
            if sOff == 0 and eOff == CHUNKSIZE:
                storePickle(temp, fname)
                print '{0}-{1} cached'.format(sectionS, sectionE-1)
            yield temp

def getPostIter(*args, **kwargs):
    return itertools.chain.from_iterable(getPostIterSub(*args, **kwargs))

def getPostList(*args, **kwargs):
    p = []
    map(p.extend, getPostIterSub(*args, **kwargs))
    return p

def getPostList2(pageS, pageE=None, thread=info_WAAPT):
    if not pageE:
        pageS, pageE = 1, pageS
    return list(itertools.chain.from_iterable(parsePage(i, thread) for i in range(pageS, pageE)))

def search(posts, author=None, phrase=None):
    assert author or phrase
    if author is not None:
        author = author.lower()
        posts = [p for p in posts if p.troper == author]

    if phrase is not None:
        posts = [p for p in posts if phrase in p.text]
    return posts
