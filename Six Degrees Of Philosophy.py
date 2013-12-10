################################################################################
#
#   Six Degrees of Philosophy.py
#
#       A claim was made that every random article on Wikipedia could be traced
#       to philosophy via the first non-parenthetical link in the body of the
#       article.  I'm going to create some dictionaries to check that, and learn
#       a bit about Python as a webcrawler language in the process!!
#
################################################################################

import webbrowser as wb         #   The native python package of web browser tools
import urllib2                  #   Another python library, more natural for this task
import time                     #   To pause so that wikipedia doesn't shut us down
import pickle                   #   To serialize the three dictionaries, and to merge them later on
import gzip                     #   For some reason Wikipedia gzips some of the files it sends

#   The dictionaries to save things to (sorted by first letter)
f = open('dictionaries.pkl','rb')
(linksDic, distanceDic, hubDic) = pickle.load(f)
f.close()

#   A base url that all links are assumed to link to
baseURL = 'http://en.wikipedia.org'


def saveDictionaries():
    """
    use pickle to serialize the three dictionaries
    """
    f = open('dictionaries.pkl','wb')
    pickle.dump((linksDic, distanceDic, hubDic), f)
    f.close()
    

def manyPaths(numOfPaths):
    """
    run oneRandomPath numOfPaths times
    """
    for i in range(numOfPaths):
        print "Step " + str(i + 1) + " of " + str(numOfPaths)
        try:
            oneRandomPath()
        except RuntimeError:
            print "Closed loop!"
        except ValueError:
            print "Probably a broken page"
            #break
        

def oneRandomPath():
    """
    Start at a random wikipedia page, and follow it down to Philosophy.  Return
    a list of strings representing titles along the way
    """

    #   Open a random webpage first, then write it to a string
    thisTitle, nextURL = checkNextStep('http://en.wikipedia.org/wiki/Special:Random')
    print "\t" + str(thisTitle) + "\t\t" + str(nextURL)
    
    firstTitle = thisTitle
    
    while thisTitle != 'Philosophy':
        
        #   First, check if this title has been seen before -- if so, the chain
        #   is complete!
        if titleHasBeenSeen(thisTitle):
            break
        
        else:
            #   Pause for a second
            #time.sleep(1.05)
            
            #   A few common exceptions
            if thisTitle == 'Flowering plant':      # This page has a problem with parentheses
                oldTitle = thisTitle
                thisTitle, nextURL = 'Embryophyte', 'http://en.wikipedia.org/wiki/Plant'
            else:
                oldTitle = thisTitle
                thisTitle, nextURL = checkNextStep(nextURL)
            print "\t" + str(thisTitle) + "\t\t" + str(nextURL)
            
            addToLinksDic(oldTitle, thisTitle)
    
    #   Now that we've finished, update the distance and hub dictionaries
    updateDistanceDic(firstTitle)
    updateHubDic(firstTitle)
    
    #   Update the three saved dictionaries
    saveDictionaries()


def checkNextStep(url): 
    """
    Given a url (in string format), collect the text for that wikipedia page,
    find the title of that wikipedia page, and find the "first" link's url
    """
    
    #   A urllib2 instance to scan through wikipedia pages
    opener = urllib2.build_opener()

    #   it will need to be told this is not a webcrawler, though it probably is
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    
    #   Open it!
    #print "\t\tAsking..."
    infile = opener.open(url)
    #print "\t\tReading..."
    thisPageString = infile.read()
    #print "\t\tScanning..."
    
    #   If it is gzip'ed, write it to file and read it in here
    if thisPageString[:3] == '\x1f\x8b\x08':
        f = open('gzipTextHolder.txt','wb')
        f.write(thisPageString)
        f.close()
        
        f = gzip.open('gzipTextHolder.txt','rb')
        thisPageString = f.read()
    
    #   Splilt it into pre-title, title, and post-title
    (preTitle, postTitle) = thisPageString.split('<title>')
    preTitle, thisPageString = None, None
    splitTitle = postTitle.split(' - Wikipedia')
    title = splitTitle[0]
    postTitle = ''
    for i in range(1,len(splitTitle)):
        postTitle += splitTitle[i]
    
    #   Extract from the "posttitle" the next link.  Start by finding the
    #   begining of the article
    postTitle = postTitle.split('<!-- bodytext -->')[1]
    
    #   Find a good place to look for the first link.  We will look for the
    #   first a href after a <p> marker.
    startIndex = goodStartIndex(postTitle)
    firstLinkIndex = postTitle.find('<a href=', startIndex)
    
    #   First, make sure a link exists!
    if firstLinkIndex == -1:
        raise ValueError, str(url) + ": No Links brah!"
    else:
        endLinkIndex = postTitle.find('"', firstLinkIndex + 9)
        
    
    #   While we are inside a table or a parenthetical aside, keep searching. 
    #   Also, skip past all "disambiguation" links
    brokenLinks = 0
    while linkIsInvalid(postTitle, firstLinkIndex, postTitle.find('>', firstLinkIndex) ):
        firstLinkIndex = postTitle.find('<a href=', firstLinkIndex + 1)
        endLinkIndex = postTitle.find('"', firstLinkIndex + 9)
        brokenLinks += 1
        if brokenLinks == 100:
            raise ValueError, "Probably a broken page."
    #print "\t\t" + str(brokenLinks) + " broken links"
    
    #   Now we have the first non-parenthetical, non-tabular, non-disambiguation
    #   link location.  Let's take a gander at it!
    endLinkIndex = postTitle.find('"', firstLinkIndex + 9)
    nextURL = baseURL + postTitle[firstLinkIndex + 9 : endLinkIndex]
    
    return title, nextURL


def goodStartIndex(postTitle):
    """
    Given the text of the post-title, find the best possible starting index.
    This essentially boils down to finding the first '<p>' character outside of
    a table or other mess
    """
    startPIndex = postTitle.find('<p>')
    
    while indexIsInvalid(postTitle, startPIndex):
        startPIndex = postTitle.find('<p>', startPIndex + 4)
    
    return startPIndex


def indexIsInvalid(postTitle, startPIndex):
    """
    Return a true if the <p> found in postTitle is inside a table (or other
    similar problems)
    """
    tableCriterion = postTitle[:startPIndex].count('<table') != postTitle[:startPIndex].count('</table')
    if tableCriterion:
        return True
    
    return False


def linkIsInvalid(postTitle, firstLinkIndex, endLinkIndex):
    """
    Check the provided link.  Return true if ANY of the criterion listed below
    are true (that is, all of the above are possible ways to invalidate the
    link)
    """
    #   Are we inside of a parenthetical aside?
    parenCriterion = postTitle[:firstLinkIndex].count('(') != postTitle[:firstLinkIndex].count(')')
    if parenCriterion:
        return True
    
    #   Are we in a table?
    tableCriterion = postTitle[:firstLinkIndex].count('<table') != postTitle[:firstLinkIndex].count('</table')
    if tableCriterion:
        return True
    
    #   Are we in a "div" thinger :P?
    divCriterion = postTitle[:firstLinkIndex].count('<div') != postTitle[:firstLinkIndex].count('</div')
    if divCriterion:
        return True
    
    #   Are we in a "dd" thinger :P?
    #ddCriterion = postTitle[:firstLinkIndex].count('dd') != postTitle[:firstLinkIndex].count('</dd>')
    #if ddCriterion:
    #    return True
    
    #   Is this a disambiguation page?
    disambiguationCriterion = postTitle[firstLinkIndex + 9 : endLinkIndex].count('(disambiguation)') != 0
    if disambiguationCriterion:
        return True
    
    #   Is this not a standard "/wiki/" wikipedia link?
    wikiCriterion = postTitle[firstLinkIndex + 10 : firstLinkIndex + 14] != 'wiki'
    if wikiCriterion:
        return True
    
    #   Is it a Wikipedia rules wiki link?
    wikiLinkCriterion = postTitle[firstLinkIndex + 15 : firstLinkIndex + 24] == 'Wikipedia'
    if wikiLinkCriterion:
        return True
    
    #   Is it a file type?
    fileLinkCriterion = postTitle[firstLinkIndex + 15 : firstLinkIndex + 19] == 'File'
    if fileLinkCriterion:
        return True
    
    return False

def titleHasBeenSeen(title):
    """
    Check for this title in LinksDic
    """
    firstLetter = title[0]
    if firstLetter in linksDic:
        return (title in linksDic[firstLetter])
    else:
        return False


def addToLinksDic(title, linkTitle):
    """
    Add this pair to the linksDic
    """
    #   Add this to the sub-dictionary corresponding to the first letter of this 
    #   article
    firstLetter = title[0]

    if firstLetter not in linksDic:
        linksDic[firstLetter] = {}

    if not (titleHasBeenSeen(title)):
        linksDic[firstLetter][title] = linkTitle


def updateDistanceDic(title):
    """
    Recursively check to see whether the item this title links to has it's
    "distance" from 'Philosophy' listed.  Once this distance has been calculated
    update the dictionary object distanceDic
    """
    firstLetter = title[0]
    stepDown = linksDic[firstLetter][title]
    
    #   First see if it's a nearest neighbor of Philosophy
    if stepDown == 'Philosophy':
        if firstLetter not in distanceDic:
            distanceDic[firstLetter] = {}
        distanceDic[firstLetter][title] = 1
    else:
        #   If it is not, check and see if the item a step down is available.  If
        #   it isn't, calculate that one before updating.
        if (stepDown[0] in distanceDic) and (stepDown in distanceDic[stepDown[0]]):
            if firstLetter not in distanceDic:
                distanceDic[firstLetter] = {}
            distanceDic[firstLetter][title] = distanceDic[stepDown[0]][stepDown] + 1
        else:
            updateDistanceDic(stepDown)
            if firstLetter not in distanceDic:
                distanceDic[firstLetter] = {}
            distanceDic[firstLetter][title] = distanceDic[stepDown[0]][stepDown] + 1


def updateHubDic(title):
    """
    For every title between "title" and "Philosophy" add 1 to the hub dic entry
    """
    
    thisTitle = title
    
    while thisTitle != 'Philosophy':
        
        #   Add 1 to hubDic (we've been here)
        firstLetter = thisTitle[0]
        if firstLetter not in hubDic:
            hubDic[firstLetter] = {}
        if thisTitle not in hubDic[firstLetter]:
            hubDic[firstLetter][thisTitle] = 0
        hubDic[firstLetter][thisTitle] += 1
        
        #   Move to the next title
        thisTitle = linksDic[firstLetter][thisTitle]


def getFarthest():
    """
    Return the node which is farthest from philosophy.  Return a list of those
    which are of that distance
    """
    farthestList = []
    maxDistance = 0
    
    for firstLetter in distanceDic:
        ddfl = distanceDic[firstLetter]
        for title in ddfl:
            d = ddfl[title]
            if d > maxDistance:
                maxDistance = d
                farthestList = []
            if d >= maxDistance:
                farthestList.append(title)
    
    return maxDistance, farthestList

    
def getMostPopular():
    """
    Return the node which has the largest number of paths going through it to
    philosophy.  Return a list of those which have that Z value
    """
    popularList = []
    maxEdges = 0
    
    for firstLetter in hubDic:
        hdfl = hubDic[firstLetter]
        for title in hdfl:
            d = hdfl[title]
            if d > maxEdges:
                maxEdges = d
                popularList = []
            if d >= maxEdges:
                popularList.append(title)
    
    return maxEdges, popularList


def getNearestNeighbors():
    """
    Return a list of all titles which link directly to Philosophy
    """
    nnList = []
    
    for firstLetter in linksDic:
        ldfl = linksDic[firstLetter]
        for title in ldfl:
            if ldfl[title] == 'Philosophy':
                nnList.append(title)
    
    return nnList


def printPath(title):
    """
    Given a title, print the path to Philosophy
    """
    i = 0
    thisTitle = title
    nextTitle = linksDic[thisTitle[0]][thisTitle]
    print str(title)
    
    while nextTitle != 'Philosophy':
        print (i * "  ") + "> " + str(nextTitle)
        i += 1
        thisTitle = nextTitle
        nextTitle = linksDic[thisTitle[0]][thisTitle]


def writeMathematicaGraph():
    """
    Take our entire dictionary and write it to file in the form
    {"key1" -> "key2", ... }
    """
    letterList = linksDic.keys()
    letterList.sort()
    L = len(letterList)
    
    f = open('MathematicaGraph.txt','wb')
    f.write('{')
    
    for i in range(len(letterList)):
        
        letter = letterList[i]
        letterDic = linksDic[letter]
        letterDicKeys = letterDic.keys()
        letterDicKeys.sort()
        l = len(letterDicKeys)
        
        for j in range(l):
            
            title = letterDicKeys[j]
            
            if not title.startswith('List of religious leaders'):

                link = letterDic[title]
                
                f.write( '"' + str(title) + '"' + "->" + '"' + str(link) + '"' )
                
                if i != (L - 1) or j != (l - 1):
                    f.write(",")
    
    f.write('}')
    f.close()


def findLink(title):
    for letter in linksDic:
        for t in linksDic[letter]:
            if linksDic[letter][t] == title:
                return t


def removeChain(title):
    linkList = []
    x = findLink(title)

    while x != None:
        linkList.append(x)
        x = findLink(x)
    
    for el in linkList:
        linksDic[el[0]].pop(el)


def wikiSpeedTest(numSites):
    
    t1 = time.time()
    for i in range(numSites):
        #   A urllib2 instance to scan through wikipedia pages
        opener = urllib2.build_opener()

        #   it will need to be told this is not a webcrawler, though it probably is
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        
        #   Open it!
        infile = opener.open('http://en.wikipedia.org/wiki/Special:Random')
        thisPageString = infile.read()
    t2 = time.time()
    print "Total time = " + str(t2 - t1)
    print "Time per site = " + str( (t2 - t1) / 100. )



#   Register Google Chrome as a browser :P
#   wb.register() etc
