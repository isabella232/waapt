#TV Tropes Thread Downloader/Archiver
#Original author: Storyyeller
#Branched from a late-2012 pastebin, archived at https://gist.github.com/Sixthhokage1/2d5f077b65b65e804b65/0512286e3180045107b3549abed4e5c41ae37988

from __future__ import division
import urllib, os.path, collections, cPickle, math, itertools
from time import sleep
from lxml import etree

#d = getTroperPostLists(5128)
debug = {}

originalNames = {}

Post = collections.namedtuple("Post", ["name", "date", "troper", "text"])
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
        with open(os.path.join('Pickle', name), 'rb') as f:
            return cPickle.load(f)
    except IOError:
        return None

def downloadSite(url, filename):
    sleep(1) #prevent accidently sending too much traffic to the poor server
    webf = urllib.urlopen(url)
    with open(filename, 'wb') as f:
        f.write(webf.read())

def downloadPage(num, info=info_WAAPT):
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

def getPostBodyText(text, element):
    editedLine = element.attrib.get('style') == "font-size:x-small;font-style:italic;"
    editedLine = editedLine and element.tag == 'p' and 'edited ' in element.text
    if editedLine:
        raise StopIteration
    
    if element.tag != 'div' or element.attrib.get('class') == 'forumreplybody':
        for child in element:
            getPostBodyText(text, child)
    if element.tag == 'p' and not element.text:
        text.append('\n')       
    if element.tag != 'div' and element.text:
    #special check for accidental redlinks
        if element.tag == 'a' and element.attrib.get('class') == 'createlink':
            text.append(redlinkText(element))
        elif element.text:    
            text.append(element.text)
    if element.tail:
        text.append(element.tail)

def getPostData(head, body):
    if head[0].tag == 'div': #an extra div was added to headers partway through
        head = head[0]
    name = head[0].attrib['name']
    
    #Skip Herald icon
    offset = head.index([x for x in head.findall('a') if x.text][1])
    orig_troper = head[offset].text
    #store it in lower case without spaces, since a name can be capitalized arbitrarily
    troper = cannonizeName(orig_troper)
    if troper not in originalNames:
        originalNames[troper] = orig_troper

    dateTitle = head[offset + 1].attrib['title']
    date = dateTitle[(dateTitle.find('post on ') + len('post on ')):]

    text = []
    try:
        getPostBodyText(text, body)
    except StopIteration:
        pass
    return Post(int(name), date, troper, ''.join(text))

def parsePage(num, thread=info_WAAPT):
    tree = etree.parse(downloadPage(num, thread), etree.HTMLParser())
    body = tree.getroot().find('body')
    firstLvl = body[0] if 'class' in body[0].attrib else body[1] #skip SOPA banner
    table = firstLvl.find('table') #skip stupid announcement banner
    divs = list(table[0].findall('td')[-1].findall('div'))

    headers = [d for d in divs if d.attrib.get('class') == 'forumreplyheader']
    bodies = [d for d in divs if d.attrib.get('class') == 'forumreplybody']
    assert(len(headers) == len(bodies) == 25)
    return map(getPostData, headers, bodies)

def testWalk(element, indent=''):
    print indent + str(element.tag), element.attrib, element.text
    for child in element:
        testWalk(child, indent+' ')

link = lambda num: "{0}{1}#{2}".format(info_WAAPT.url, (num-1)//25+1, num )
bblink = lambda num: "[[{0}{1}#{2} {2}]]".format(info_WAAPT.url, (num-1)//25+1, num )

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
    for pg in xrange((pageS-1)//CHUNKSIZE, (pageE-2)//CHUNKSIZE+1):
        sOff = max((pageS-1-pg*CHUNKSIZE,0))
        eOff = min((pageE-1-pg*CHUNKSIZE,CHUNKSIZE))
        sectionS,sectionE = sOff+1+pg*CHUNKSIZE,eOff+1+pg*CHUNKSIZE
        fname = 'postlist{}_{}_{}'.format(thread.id, pg*CHUNKSIZE+1,(pg+1)*CHUNKSIZE)
        cached = getPickle(fname)
        if cached:
            yield cached[sOff*25:eOff*25]
            print '{0}-{1} retrieved from cache'.format(sectionS,sectionE-1)
        else:
            temp = []
            for i in xrange(sectionS,sectionE):
                temp.extend(parsePage(i, thread))
                print i,
            if sOff == 0 and eOff == CHUNKSIZE:
                storePickle(temp, fname)
                print '{0}-{1} cached'.format(sectionS,sectionE-1)
            yield temp

def getPostIter(*args, **kwargs):
    return itertools.chain.from_iterable(getPostIterSub(*args, **kwargs))

def getPostList(*args, **kwargs):
    p = []
    map(p.extend, getPostIterSub(*args, **kwargs))
    return p

def getTroperPostLists(posts, mergeAlts=False):
    #for conveinence, allow passing in a page count instead
    if isinstance(posts, (int,long)): 
        posts = getPostIter(1,posts)
        
    d = collections.defaultdict(list)
    for p in posts:
        d[p.troper].append(p.name)
    if mergeAlts:
        for names in altNameLists:
            name = names[0]
            for alt in names[1:]:
                d[name] += d[alt]
                del d[alt]
            d[name] = sorted(d[name])
    return dict(d.iteritems())

altNameLists = [
                ]

def indicesToPosts(posts, indices):
    return [posts[x-1] for x in indices]

def getCountDict(posts):
    d = collections.defaultdict(int)
    for post in posts:
        for word in frozenset(getWordsFromPost(post)):
            d[word] += 1
    return d

def mergeCountDicts(dicts):
    total = collections.defaultdict(int)
    for d in dicts:
        for k in d:
            total[k] += d[k]
    return total

def getWordScores(weights, counts):
    score = lambda key: counts[key]/weights[key]
    tups = [(score(key), key) for key in counts if key in weights]
    return sorted(tups, reverse=True)

def getBestWords():
    unpackWords = lambda tuplist: [t[1] for t in tuplist]
    return map(unpackWords, getGroupScores())

def getMostUniqueWords(pageE, groupSize, wordcount=25):
    assert(0 < groupSize < pageE)
    
    dicts = []
    limits = []
    for s in xrange(1,pageE,groupSize):
        e = min((pageE, s+groupSize))
        d = getCountDict(getPostIter(s,e))
        dicts.append(d)
        limits.append((s,e))
    total = mergeCountDicts(dicts)
    weights = {k:v for (k,v) in total.items() if v>=25}
    gweights = [getWordScores(weights, g) for g in dicts]
    fitems = [(s,e, [t[1] for t in scores[:wordcount]]) for ((s,e),scores) in zip(limits, gweights)]
    formatstr = '*Pages {0} to {1}: {2}'
    return '\n'.join([formatstr.format(s,e-1,', '.join(map(str, items))) for (s,e,items) in fitems])

class partialStats(object):
    def __init__(self, groupSize, start=1):
        self.groupSize = groupSize
        self.limit = start
        self.posts = []
        self.totalCounts = {}
        self.groupCounts = []

    def add(self, pnum):
        S,E,G = self.limit, pnum, self.groupSize
        if pnum <= self.limit:
            return
        newposts = getPostList(self.limit, pnum)
        self.limit = pnum
        self.posts.extend(newposts)
        self.totalCounts = mergeCountDicts((self.totalCounts, getCountDict(newposts)))
        
        if self.groupCounts and (S%G != 1):
            (os, oe), last = self.groupCounts[-1]
            assert(S == oe)
            ne = min((E, os+G))
            newCounts = mergeCountDicts((last, getCountDict(getPostIter(os,ne))))
            self.groupCounts[-1] = (os,ne), newCounts
            assert(ne == int(math.ceil((S-1)/G)*G + 1))
        S2 = int(math.ceil((S-1)/G)*G + 1)
        print S, G, S2, E
        for s in xrange(S2, E, G):
            e = min((E, s+G))
            print s, e
            d = getCountDict(getPostIter(s,e))
            self.groupCounts.append(((s,e), d))

    def makePost(self):
        weights = {k:v for (k,v) in self.totalCounts.items() if v>=25}
        gweights = [('Pages {0} to {1}'.format(key[0],key[1]-1), getWordScores(weights, counts))
                    for (key,counts) in self.groupCounts]
        
        fitems = [(k,[t[1] for t in scores[:25]]) for (k,scores) in gweights]
        formatstr = '*{0}: {1}'
        return '\n'.join([formatstr.format(key,', '.join(map(str, items))) for (key,items) in fitems])

def filterPoster(names, it):
    if isinstance(names, (str,unicode)):
        names = (names,)
    names = map(cannonizeName, names)
    return itertools.ifilter((lambda p: p.troper in names), it)

def filterWord(word, it):
    return itertools.ifilter((lambda p: word in getWordsFromPost(p)), it)

def filterAnyWord(words, it):
    words = frozenset(words)
    return itertools.ifilter((lambda p: not words.isdisjoint(getWordsFromPost(p))), it)

def search(posts, tropers=None, words=None, anyWords=None):
    it = posts
    if tropers:
        it = filterPoster(tropers, it)
        
    if isinstance(words, (str,unicode)):
        words = (words,)
    if words:
        for word in words:
            it = filterWord(word, it)
    if anyWords:
        it = filterAnyWord(anyWords, it)
    return it

def findFirst(*args, **kwargs):
    return search(*args, **kwargs).next()

def findAll(*args, **kwargs):
    return list(search(*args, **kwargs))

def searchForString(pageS, pageE, string, maxcount=10):
    s = string
    results = []
    for post in getPostIter(pageS, pageE):
        text = getStringFromPost(post)
        if s in text:
            results.append(post.name)
            if maxcount and len(results) >= maxcount:
                break
    return results

def getRuns(posts):
    posts = iter(posts)
    runs = []

    last = posts.next()
    count = 1
    for post in posts:
        if post.troper != last.troper:
            runs.append((last.troper, last.name, count))
            last, count = post, 1
        else:
            count += 1
    return runs

dbg = []
def getTroperAltUniqueWords(pnum, wordcount=25):
    posts = getPostList(1,pnum)
    d = getTroperPostLists(posts, mergeAlts=True)
    dbg.append(d)
    def processKey(k):
        return k if isinstance(k, (str,unicode)) else k[0]
    
    d = {processKey(k):indicesToPosts(posts,v) for k,v in d.items() if len(v) > 1000 or v[-1] > (pnum*25 - 1000)}
    dbg.append(d)
    print 'counting'
    dicts = {k:getCountDict(v) for k,v in d.items()}
    dbg.append(dicts)
    gdict = getCountDict(posts)
    weights = {k:v for (k,v) in gdict.items() if v>=25}
    gweights = [(k,getWordScores(weights, v)) for k,v in dicts.items()]
    fitems = [(key, [t[1] for t in scores[:wordcount]]) for (key,scores) in gweights]
    formatstr = '*{0}: {1}'
    return '\n'.join([formatstr.format(key,', '.join(items)) for (key,items) in fitems])
