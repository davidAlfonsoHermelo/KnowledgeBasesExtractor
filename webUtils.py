#!/usr/bin/python
#-*- coding:utf-8 -*-


#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-IMPORTATIONS-------------------
import utils, kb

import wikipedia, pywikibot, re, urllib, urllib2
import urlparse, Levenshtein, time, langid
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urllib2 import HTTPError


#--------------END-IMPORTATIONS-------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-PARAMETRES-------------------



#--------------END-PARAMETRES-------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-FONCTIONS-------------------


def getWikiSearchQuery(namedEntity, lazySuggestedQuery=True):
	'''
	If the names entity doesn't correspond to any 
	existing article name, it returns a suggested
	one that does exist.

	if lazySuggestedQuery is True, the returned list 
	will only be a list of the first suggestion
	'''

	articleNameSuggested = wikipedia.suggest(namedEntity)

	#None suggestion means either that the article 
	#already has the right name or that it doesn't 
	#exist
	if articleNameSuggested == None:
		wikipediaSuggestedQueries = wikipedia.search(namedEntity)
		#if we're being lazy and we only want the first suggestion
		if lazySuggestedQuery == True:
			wikipediaSuggestedQueriesList = [wikipediaSuggestedQueries[0]]
		else:
			wikipediaSuggestedQueriesList = wikipediaSuggestedQueries
	else:
		wikipediaSuggestedQueriesList = wikipedia.search(articleNameSuggested)
	#if the list is empty, we return None
	if len(wikipediaSuggestedQueriesList) != 0:
		return wikipediaSuggestedQueriesList
	else:
		return None


def getGoogleSuggestedQueries(namedEntity):
	'''
	If we get no result for the search, it searchs 
	for google's suggestions containing the NE and
	returns a suggested query and a list with the
	other suggestions.
	If there's still nothing it returns None
	'''
	#we transform the named entity to utf8
	namedEntity = utils.toUtf8(namedEntity)

	#we try to transform the named entity to an uri readeable string if it has an iri code in it
	namedEntity = utils.iriToUri(namedEntity)

	#we try to make the adress bar
	regexWords = re.compile(ur'[\w]+', re.UNICODE)
	listOfNeWords = regexWords.findall(namedEntity)

	googleSuggestionsUrl = u'http://suggestqueries.google.com/complete/search?output=toolbar&q='

	#we make a string corresponding to 2nd half of the search bar
	for indexNeWord, neWord in enumerate(listOfNeWords):

		#we try to make the named entity word readeable for the adress bar
		neWord = utils.toUtf8(neWord)
		
		#if it's the first word of the query
		if indexNeWord == 0:
			googleSuggestionsUrl += neWord
		#if it's not the first word
		else:
			googleSuggestionsUrl += u'%20' + neWord

	suggestionsPage = urllib2.urlopen(googleSuggestionsUrl)
	suggestionSoup = BeautifulSoup(suggestionsPage.read(), 'lxml')
		
	#we scrap the data from the suggestion webpage
	tagList = suggestionSoup.findAll(u'suggestion')
	googleSuggestedQueriesList = []
	for tag in tagList:
		googleSuggestedQueriesList.append(tag[u'data'])

	if len(googleSuggestedQueriesList) != 0:
		return googleSuggestedQueriesList
	else:
		return None


def getTheRightSearchQuery(namedEntity, wikiOrGoogleOriented='w'):
	'''
	Searchs if the wikipedia page corresponding to the
	named entity exists. If there are multiple suggestions, 
	we do a simple, naive and 'rustic' weighted cross 
	between wikipedia and google suggestions to find 
	the most probable result.
	'''
	#we transform named entity into utf-8
	namedEntity = utils.toUtf8(namedEntity)
	
	#according to if we're looking for a wiki-like or
	#a google-like search query, we add weight to the
	#listA with the help of listB
	if wikiOrGoogleOriented.lower() in ['w', 'wiki', 'wikipedia', 'wikimedia', 'wikidata']:
		listA = getWikiSearchQuery(namedEntity)
		listB = getGoogleSuggestedQueries(namedEntity)
	elif wikiOrGoogleOriented.lower() in ['g', 'googl', 'google', 'alphabet']:
		listA = getGoogleSuggestedQueries(namedEntity)
		listB = getWikiSearchQuery(namedEntity)
	else:
		raise ValueError('the second argument (wikiOrGoogleOriented) has not a valid value, please choose between the string value "w" for a wikipedia-oriented query result or "g" for a google-oriented query result')
	
	#we transform the list elements to compare into unicode
	listFirstElement = utils.toUtf8(listA[0])

	#if one of the lists is None, then we return the first 
	#result of the other list
	if listA == None and listB == None:
		raise Exception('the search has produced no valid result, please verify the validity of the search arguments')
	elif len(listA) == 1:
		#if we can't find a suggestion similar enough, we return the same named entity we received
		if Levenshtein.ratio(namedEntity, listFirstElement) < 0.27:
			##########################################################################
			#################OR MAYBE WE SHOULD RETURN NONE ??????
			#########################################################################
			return namedEntity
		else:
			return listFirstElement
	elif listA == None:
		return listB[0]
	elif listB == None:
		return listFirstElement
	#otherwise
	else:
		similarityDict = {}
		intersectionDict = {}
		listB = [suggestB.lower() for suggestB in listB]
		
		#we save on a dict the most cosine similar element in the list A
		for indexSuggestA, suggestA in enumerate(listA):
			positionWeight = float(indexSuggestA)/100
			#we save the dict
			similarityDict[suggestA] = (Levenshtein.ratio(namedEntity.lower(), suggestA.lower())) - positionWeight
		#we look for the common elements in the 2 lists
		for suggestA in listA:
			if suggestA.lower in listB:
				intersectionDict[suggestA] = similarityDict[suggestA]

		#if there is an intersection between the 2 lists
		#we return the most similar common intersection
		if len(intersectionDict) != 0:
			return sorted(intersectionDict, key=intersectionDict.get, reverse=True)[0]
		#if there is no intersection between the 2 lists
		#we return the most similar suggestion from list A
		else:
			return sorted(similarityDict, key=similarityDict.get, reverse=True)[0]
	return None


def getAllPossibleQueries(namedEntityOrListOfNamedEntities):
	'''
	Searchs for all the wikipedia/google possible queries and returns
	a dict containing all suggestions as values and, as a key, the 
	original searched word.
	'''
	allPossibilitiesDict = {}

	if type(namedEntityOrListOfNamedEntities) is unicode or type(namedEntityOrListOfNamedEntities) is str :
		namedEntityOrListOfNamedEntities = [namedEntityOrListOfNamedEntities]
	elif type(namedEntityOrListOfNamedEntities) is not list:
		raise TypeError('list, string or unicode object needed, the type we received is: ', type(namedEntityOrListOfNamedEntities))

	#for each element of the list we search all possible queries
	for namedEntity in namedEntityOrListOfNamedEntities:
		allSuggestionsList = []
		wikiSearchQueries = getWikiSearchQuery(namedEntity, False)
		googlSearchQueries = getGoogleSuggestedQueries(namedEntity)

		#if we found at least one wikipedia suggestion we add it to the list of all posibilities
		if wikiSearchQueries != None:
			allSuggestionsList = allSuggestionsList + wikiSearchQueries
		#same thing for the google queries
		if googlSearchQueries != None:
			allSuggestionsList = allSuggestionsList + googlSearchQueries

		#if we didn't find anything from wikipedia or google we return the original named entity as a list list
		if len(allSuggestionsList) == 0:
			allPossibilitiesDict[namedEntity] = [namedEntity]
		else:
			#we save the results into the dict
			allPossibilitiesDict[namedEntity] = allSuggestionsList
	
	return allPossibilitiesDict


def wikiObjectTreatment(claim, typeClaim, keyClaimList, repository, lang):
	'''
	Returns a dictionnary of the object content
	'''
	dictWkObjects = {}
	#if it's a wiki quantity object
	if typeClaim is pywikibot.WbQuantity:
		unit = str(claim.unit)
		#if the unit is a website, we will try to get the label
		try:
			if u'http' in unit or u'www.' in unit:
				item = pywikibot.ItemPage(repository, (unit.split(u'/')[-1]))
				#we need to call the item (by using '.get()') to access the data
				item.get()
				unit = item.labels['en']
		#if we get a KeyError: u'upperBound' at the ItemPage- and the get()-  -level and 
		#can't open the page due to the ± character
		except KeyError:
			entityUrl = claim.unit
			entity = (entityUrl.split(u'/'))[-1]
			itemUrl = u'https://www.wikidata.org/wiki/%s' %(entity)
			
			unit = kb.getInfoWkdataWithBtfulSoup(itemUrl, dictInfoWkdata={}, allInfo=u'label', lang=lang)
		if unit != u'' or unit != None:
			dictWkObjects[keyClaimList] = '%s %s' %(str(claim.amount).encode('utf8'), unit)
	#if it's a wiki time object
	elif typeClaim is pywikibot.WbTime:
		'''
		#as we would find it in wikidata
		dictWkObjects[keyClaimList+u'.minute'] = str(claim.minute).encode('utf8')
		dictWkObjects[keyClaimList+u'.hour'] = str(claim.hour).encode('utf8')
		dictWkObjects[keyClaimList+u'.day'] = str(claim.day).encode('utf8')
		dictWkObjects[keyClaimList+u'.month'] = str(claim.month).encode('utf8')
		dictWkObjects[keyClaimList+u'.year'] = str(claim.year).encode('utf8')
		'''
		#adapted to be normalized with other KBs
		dictWkObjects[keyClaimList+u'.minute'] = str(claim.minute).encode('utf8')
		dictWkObjects[keyClaimList+u'.hour'] = str(claim.hour).encode('utf8')
		dictWkObjects[keyClaimList+u'.date'] = u'%s-%s-%s' %(str(claim.year).encode('utf8'), str(claim.month).encode('utf8'), str(claim.day).encode('utf8'))
	#if it's a wiki coordinate object
	elif typeClaim is pywikibot.Coordinate:
		dictWkObjects[keyClaimList+u'.altitude'] = str(claim.alt).encode('utf8')
		dictWkObjects[keyClaimList+u'.lattitude'] = str(claim.lat).encode('utf8')
		dictWkObjects[keyClaimList+u'.longitude'] = str(claim.lon).encode('utf8')
		dictWkObjects[keyClaimList+u'.globe'] = str(claim.globe).encode('utf8')
	#if it's none of the above
	#could be a TimeStamp or WbMonolingualText
	else:
		return None
	return dictWkObjects


def firstElementOfDisambiguationPage(articleSoup, repository, lang):
	'''
	When the article is a disambiguation page, we use a regex to 
	extract the default first description of the selected language
	'''
	descriptionSnakviews = articleSoup.body.findAll(u'div', {u'class' : u'wikibase-snakview-value wikibase-snakview-variation-valuesnak'})
	for snak in descriptionSnakviews:
		descriptionLink = snak.find(u'a')
		try: 
			descriptionLinkString = (descriptionLink.string).lower()
			#we try to find the first suggestion by deducing it's string won't have 
			#the words 'disambiguation' and 'wikipedia' in them
			if u'disambiguation' not in descriptionLinkString and u'wikipedia' not in descriptionLinkString:
				#we extract the code
				hrefAttribute = re.compile('href="/wiki/|title="|"', re.UNICODE)
				firstDisambiguationCode = hrefAttribute.split((descriptionLink).encode('utf8'))[1]
				
				#we prepare the new pywikibot objects
				item = pywikibot.ItemPage(repository, firstDisambiguationCode)
				#we need to call the item (by using '.get()') to access the data
				item.get()

				#get the url
				wikidataUrl = item.full_url()
				#we try to transform the url to an uri readeable string if it has an iri code in it
				wikidataUrl = utils.iriToUri(wikidataUrl)
				
				#prepare a beautiful soup
				articleObject = urllib2.urlopen(wikidataUrl)
				articleSoup = BeautifulSoup(articleObject.read(), 'lxml', from_encoding=articleObject.info().getparam(u'charset'))
				
				#we define the variable description again
				try:
					descriptions = item.descriptions
					langDescription = descriptions[lang]
				except KeyError:
					langDescription = None
				break
			else:
				langDescription = None
		#if we don't find the description link, then we pass
		except AttributeError:
			pass
	return langDescription, item


def getIntroWikipedia(namedEntity, returnAlist=True):
	'''
	Scraps Wikipedia's page and catches the intro of the article
	(so it can, later, be passed throught the Open Information Extractors).
	'''
	paragraphIntroList = []
	wikidataUrl = None

	#get the article name by disambiguating
	articleName = namedEntity
	#articleName = getTheRightSearchQuery(namedEntity, wikiOrGoogleOriented='w')

	if articleName != None:
		articleNameNoSpace = articleName.replace(u' ', u'_')
		#we try to transform the article name to an uri readeable string if it has an iri code in it
		articleNameNoSpace = utils.iriToUri(articleNameNoSpace)
	#if we don't find the right querry we return None
	else:
		return None

	#get the article url
	articleUrl = 'https://en.wikipedia.org/wiki/%s' %(articleNameNoSpace)
	
	try:
		#prepare a beautiful soup
		articleObject = urllib2.urlopen(articleUrl.encode('utf8'))
	#if there is an http error it means the page has an entry but doesn't exist so we return None
	except HTTPError:
		return None

	articleSoup = BeautifulSoup(articleObject.read(), 'lxml', from_encoding=articleObject.info().getparam(u'charset'))
	#get the first section-separated content
	articleContentDiv = articleSoup.body.find(u'div', {u'id' : u'toc'})

	#if there is no toc section (introduction), we search for the text appearing before the h2 tag (sub-title)
	if articleContentDiv == None:
		articleContentDiv = articleSoup.body.find(u'h2')

	#if it's an incomplete page we return None
	if articleContentDiv != None:
		#get the content of the previous paragraphs (aka the intro)
		articleIntroList = articleContentDiv.findAllPrevious(u'p')
		#cleaning the html intro list obtained
		wikiReference = re.compile(ur'\[[\d]*\]|\[.*needed\]|\[not verified.*\]|\[note.*\]|\(.*listen\)')
		for introParagraph in articleIntroList:
			introParagraphText = introParagraph.text
			#if its a disambiguation page, we return None
			if len(articleIntroList) <= 2 and u'refer to:' in introParagraphText:
				return None
			#if it's not a disambiguation page
			else:
				if len(introParagraphText) != 0:
					introReferenceList = re.findall(wikiReference, introParagraphText)
					#if there are references
					if len(introReferenceList) != 0:
						for reference in introReferenceList:
							introParagraphText = introParagraphText.replace(reference, u'')
						cleanedParagraphText = introParagraphText
					#if there are no references
					else:
						cleanedParagraphText = introParagraphText
					#add to the list
					paragraphIntroList.append(cleanedParagraphText)
		#we scrap the wikidata url from wikipedia
		wikidataRow = articleSoup.body.find(u'a', {u'title' : u'Link to connected data repository item [g]'})
		if wikidataRow != None:
			wikidataUrl = wikidataRow.attrs[u'href']
		
		#if the page doesn't exist we return None
		else:
			return None
	#if it's an incomplete page we return None
	else:
		return None

	#we put the list in the order it appears in wikipedia
	paragraphIntroList.reverse()
	#we return the intro, the article name and the wikidata url
	if returnAlist == True:
		return paragraphIntroList, articleNameNoSpace, wikidataUrl
	else:
		return u' '.join(paragraphIntroList), articleNameNoSpace, wikidataUrl


def getWikipediaPage(namedEntity, returnAlist=True):
	'''
	Scraps Wikipedia's page and catches the intro of the article
	(so it can, later, be passed throught the Open Information Extractors).
	'''
	paragraphTextList = []
	wikidataUrl = None

	#get the article name by disambiguating
	articleName = namedEntity
	#articleName = getTheRightSearchQuery(namedEntity, wikiOrGoogleOriented='w')

	if articleName != None:
		articleNameNoSpace = articleName.replace(u' ', u'_')
		#we try to transform the article name to an uri readeable string if it has an iri code in it
		articleNameNoSpace = utils.iriToUri(articleNameNoSpace)
	#if we don't find the right querry we return None
	else:
		return None

	#get the article url
	articleUrl = 'https://en.wikipedia.org/wiki/%s' %(articleNameNoSpace)
	
	try:
		#prepare a beautiful soup
		articleObject = urllib2.urlopen(articleUrl.encode('utf8'))
	#if there is an http error it means the page has an entry but doesn't exist so we return None
	except HTTPError:
		return None

	articleSoup = BeautifulSoup(articleObject.read(), 'lxml', from_encoding=articleObject.info().getparam(u'charset'))
	#get the text inside al paragraphs
	paragraphList = articleSoup.body.findAll(u'p')

	#we only take the text from the paragraphs, not the tags
	for paragraph in paragraphList:
		paragraphText = paragraph.text
		#we return None if we get to a desambiguation page
		if u'may refer to:' in paragraphText:
			return None
		#we clean the text form all wikipedia references
		cleanedParagraphText = re.sub(ur'\[[\d]+\]', u'', paragraphText)
		paragraphTextList.append(cleanedParagraphText)
	
	#we scrap the wikidata url from wikipedia
	wikidataRow = articleSoup.body.find(u'a', {u'title' : u'Link to connected data repository item [g]'})
	if wikidataRow != None:
		wikidataUrl = wikidataRow.attrs[u'href']
	

	#we return the intro, the article name and the wikidata url
	if returnAlist == True:
		return paragraphTextList, articleNameNoSpace, wikidataUrl
	else:
		return u' '.join(paragraphTextList), articleNameNoSpace, wikidataUrl


def getGoogleFirstPages(query, nbOfPages=10, includeWikipedia=True):
	"""
	Returns a list containing the text in the first google suggested 
	pages.
	Minimum number of pages: 1
	Maximum number of pages: 10

	Tuto: http://stackoverflow.com/questions/37754771/python-get-result-of-google-search

	IN ENGLISH ONLY
	For other languages the script must be changed at the lines:
		- result = service.cse().list(q=query, cx=my_cse_id, excludeTerms='wikipedia.org', lr='lang_en').execute()
		- searchPage = utils.iriToUri(u'https://www.google.ca/search?q=%s&lr=lang_en' %(query.replace(u' ', u'+')))
		- searchPage = utils.iriToUri(u'https://www.google.ca/search?q=%s+-site%3Awikipedia.org&lr=lang_en' %(query.replace(u' ', u'+')))
		- searchPage = utils.iriToUri(u'https://www.google.ca/search?q=%s&lr=lang_en' %(query.replace(u' ', u'+')))

	"""
	resultContentList = []

	#we try to transform the query to an uri readeable string if it has an iri code in it
	query = utils.iriToUri(query)

	#google api information
	my_cse_id = u'010977947046578922081:vl9apgc5fic'
	api_key = open('apiKeyKnowledgeGraphAndCustomSearch.api_key').read()
	service = build('customsearch', 'v1', developerKey=api_key)
	#google search result (dict)
	try:
		if includeWikipedia != True:
			result = service.cse().list(q=query, cx=my_cse_id, excludeTerms='wikipedia.org', lr='lang_en').execute()
		else:
			result = service.cse().list(q=query, cx=my_cse_id, lr='lang_en').execute()
	
	#if we reach the 100/day limit of the google search api, we scrap the google search page using beautifulsoup
	except HttpError:
		#do we include wikipedia pages or not
		if includeWikipedia != True:
			searchPage = utils.iriToUri(u'https://www.google.ca/search?q=%s+-site%3Awikipedia.org&lr=lang_en' %(query.replace(u' ', u'+')))
		else:
			searchPage = utils.iriToUri(u'https://www.google.ca/search?q=%s&lr=lang_en' %(query.replace(u' ', u'+')))

		#prepare a beautiful soup
		searchPageRequest = urllib2.Request(searchPage, headers={u'User-Agent' : u"Magic Browser"})
		searchPageObject = urllib2.urlopen(searchPageRequest)
		searchPageSoup = BeautifulSoup(searchPageObject.read(), 'lxml', from_encoding=searchPageObject.info().getparam(u'charset'))

		#get the pages urls of the search
		searchResultsWrapList = (searchPageSoup.body).findAll(u'h3', {u'class' : u'r'})
		#and we save them in a list
		result = []

		for h3Tag in searchResultsWrapList:
			googleLinkInfo = (h3Tag.find(u'a', {u'href':True})[u'href'])
			splittedLinkInfo = (re.compile(ur'=|&')).split(googleLinkInfo)
			if splittedLinkInfo[0] == u'/url?q':
				url = splittedLinkInfo[1]
				result.append(url)

	#getting the urls from the first google search results (using the google API)
	for indexResult in range(nbOfPages*2):
		try:
			#catching the url
			#if we used the google API
			if type(result) is not list:
				searchResult = result[u'items'][indexResult]
				googleSearchUrl = searchResult[u'link']
			#if we didn't use the API but beautifulsoup
			else:
				googleSearchUrl = result[indexResult]
			#we try to transform the url to an uri readeable string if it has an iri code in it
			googleSearchUrl = utils.iriToUri(googleSearchUrl)

			#scrapping each search result content
			#prepare a beautiful soup
			pageRequest = urllib2.Request(googleSearchUrl, headers={'User-Agent' : "Magic Browser"})
			pageObject = urllib2.urlopen(pageRequest)
			encoding = pageObject.info().getparam(u'charset')
			#if there is no encoding specified, we suppose it's probably utf-8
			if encoding in [None, u'None', 'None', 'none', '']:
				encoding = u'utf-8'
			pageSoup = BeautifulSoup(pageObject.read(), 'lxml', from_encoding=encoding)
			#getting the content out of the url pages
			pageText = pageSoup.body.text

			#we make sure the page is in english
			if langid.classify(pageText)[0] == u'en':

				#cleaning and filtering the text
				newPageText = ''				
				pageLinesList = pageText.split(u'\n')

				for indexLine in range(len(pageLinesList)):
					pageLine = pageLinesList[indexLine]
					lineChars = len(pageLine)
					#the input file has a limit of characters per line o 4096 char
					#so we don't take into account the lines that are bigger than 4090
					if lineChars > 4090:
						pass
					#ollie seems to have a data limit,
					#we have discarded nb of line limit, nb of char limit, time limit, data weight of input.txt limit, 
					#so we have limited the size of lines taken into account (we only take the bigger than 250char)
					elif lineChars < 250:
						pass
					elif u'{' in pageLine or u'}' in pageLine:
						pass
					elif pageLine in [u'', u' ']:
						pass
					else:
						newPageText = newPageText + pageLine.replace(u'\t', '') + u'\n'

				resultContentList.append(newPageText)

				#if we achieve the desired n umber of pages we break the loop
				if len(resultContentList) >= nbOfPages:
					break
		#in case the desired nb of pages exceeds the desired number or is less than 1
		except IndexError:
			pass
		#if we cannot open the page using urllib, we pass
		except HTTPError:
			pass
		#if the page content or its body content is None we pass
		except AttributeError:
			pass
		#error: [Errno 104] Connection reset by peer or <urlopen error [Errno 110] Connection timed out>
		except Exception:
			pass

	#returning the list of text
	return resultContentList


#--------------END-FONCTIONS-------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------



#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-DECLARATIONS-------------------








#--------------END-DECLARATIONS-------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-COMMANDES-------------------

	

#--------------END-COMMANDES-------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-ERRORS-------------------



#--------------END-ERRORS-------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-REFERENCES-------------------



#--------------END-REFERENCES-------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------