#!/usr/bin/python
#-*- coding:utf-8 -*-


#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-IMPORTATIONS-------------------
import utils, webUtils

import subprocess, shlex, requests, pywikibot, re, json
import urllib, urllib2, urlparse, pickle, Queue, time, os
from bs4 import BeautifulSoup
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





#--------------END-FONCTIONS-------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------



#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-DECLARATIONS-------------------


def startFreebaseRunning():
	'''
	Launches the freebase upstream (ahead)
	'''
	#command to launch the local Freebase platform
	commandArgsLaunch = shlex.split('sh fuseki-server -loc=/data/rali6/Tmp/Freebase/Index/ -port=27017 /Freebase')
	process = subprocess.Popen(commandArgsLaunch, cwd='/u/alfonsda/workspace/test/lib/apache-jena-fuseki-2.4.1/')
	#option to wait for the process to end:
	#(subprocess.Popen(commandArgsLaunch, cwd='/u/alfonsda/workspace/test/lib/apache-jena-fuseki-2.4.1/')).wait()
	time.sleep(15)
	return None


def deleteTheFreebaseLockFile(pathToLockFile=u'/data/rali6/Tmp/Freebase/Index/'):
	'''
	'''
	#we delete the freebase lock once all the processes have finished
	try:
		os.remove(u'%stdb.lock' %(pathToLockFile))
	except OSError:
		pass
	return None


def getFreebaseEntityId(searchQuery, dictInfoWkdata):
	'''
	If the is one, analyses and retrieves the freebase id from a dictionary of 
	correspondance between wiki article titles and freebase code ids, 
	if there's nothing, we search for it in the dictionnary 
	of wikidata information, otherwise it returns None
	'''
	if dictInfoWkdata == None:
		dictInfoWkdata = {}
	
	#if the article's name is in the dictionary of corresponding wikipedia articles - freebase code id
	articleName = searchQuery.replace(u' ', u'_')
	#path to the dict
	dictWikipedia2Freebase = pickle.load(open("./dictWikipedia2Freebase.p", "rb"))
	
	if articleName in dictWikipedia2Freebase and dictWikipedia2Freebase[articleName] != None:
		print('0000000000000000', dictWikipedia2Freebase[articleName])
		return dictWikipedia2Freebase[articleName]

	#if it's not in the wikidata dict we browse the dictWikipedia2Freebase to search for it
	elif len(dictInfoWkdata) != 0:
		for key in dictInfoWkdata:
			value = dictInfoWkdata[key]
			if u'Freebase ID' in key and u' ' not in value:
				#treatment of the value to make it compatible with the freebase syntax
				if u'/m/' in value:
					print('0000000000000000', value.replace(u'/m/', u'm.'))
					return value.replace(u'/m/', u'm.')
				return value
	return None


def queryFreebaseFromUrl(query="SELECT * {?subj ?prop ?obj} LIMIT 25"):
	'''
	Asks for the query in the local network using requests and returns the result 
	'''
	try:
		result = requests.post('http://localhost:27017/Freebase/query',
			data={'query': query})
	#iof there is a connexion error we restart the local freebase platform
	except requests.exceptions.ConnectionError:
		startFreebaseRunning()
		result = requests.post('http://localhost:27017/Freebase/query',
			data={'query': query})
	return result.json()


def getEntityName(objectValue, lang, originalFreebaseId):
	'''
	returns the first name of a given entity
	'''
	#SELECT * WHERE {<http://rdf.freebase.com/ns/m.01w5ts6> ?p ?o. } LIMIT 300
	subQueryOutput = queryFreebaseFromUrl(query=("SELECT * WHERE {<%s> ?p ?o. } LIMIT 100" %(objectValue)))
	subQueryResultList = subQueryOutput[u'results'][u'bindings']
	#preparing the variables in case the value is scattered
	firstValue = u''
	secondValue = u''
	#browsing
	for subQueryResult in subQueryResultList:
		#if the query result is a literal
		if subQueryResult[u'o'][u'type'] == u'literal':

			#if there are multiple languages posibilities we
			#only capture the language we're interested in
			if u'xml:lang' in subQueryResult[u'o']:
				if subQueryResult[u'o'][u'xml:lang'] == lang:
					return subQueryResult[u'o'][u'value']
			#otherwise we just capture the plain information
			else:
				#this value will be joined with the secondValue, 
				#in case the values are divided in two and scattered
				firstValue = subQueryResult[u'o'][u'value']

		else:
			#we search for a second value contained in another freebase value (i.e. the unit for a number)
			urlEndind = (subQueryResult[u'o'][u'value']).split(u'/')[-1]
			if u'm.' in urlEndind and urlEndind != originalFreebaseId:
				#we query once more, but just the name of the entity
				infraQueryResultList = queryFreebaseFromUrl(query=("SELECT * WHERE {<%s> ?p ?o. } LIMIT 100" %(subQueryResult[u'o'][u'value'])))[u'results'][u'bindings']
				for infraQueryResult in infraQueryResultList:
					#if the query result is a name (otherwise we do nothing)
					if infraQueryResult[u'o'][u'type'] == u'literal' and u'object.name' in infraQueryResult[u'p'][u'value']:
						#if there are multiple languages posibilities we
						#only capture the language we're interested in
						if u'xml:lang' in infraQueryResult[u'o']:
							if infraQueryResult[u'o'][u'xml:lang'] == lang:
								secondValue = infraQueryResult[u'o'][u'value']
						#otherwise we just capture the plain information
						else:
							#this value will be joined with the secondValue, 
							#in case the values are divided in two and scattered
							secondValue = infraQueryResult[u'o'][u'value']
	if firstValue != u'' and secondValue != u'':
		return (u'%s; %s' %(firstValue, secondValue))
	

def getInfoFreebase(searchQuery, dictInfoWkdata={}, lang=u'en', includeTypeAndPeopleAndContainsInformation=False, allInfo=True):
	'''
	Interrogates Freebase and returns a dict with the most relevant
	information
	'''
	dictFreebaseInfo = {}
	listOfIsolatedInfo = []
	#we try to get the freebase Id either by searching for it in a local 
	#dict or by selecting it from the wikidata info dict
	freebaseId =  getFreebaseEntityId(searchQuery, dictInfoWkdata)

	#we try to find the freebase content
	try:
		queryOutput = queryFreebaseFromUrl(query="PREFIX fb: <http://rdf.freebase.com/ns/> SELECT * WHERE {fb:%s ?p ?o. } LIMIT 30000" %(freebaseId))
		queryResultList = queryOutput[u'results'][u'bindings']

	#if there is no freebase content(no json file but a <Response [503]>) we return None
	except ValueError:
		return None

	#if we don't want to capture all the information but only some of it as a list (ex: aliases)
	if allInfo != True:
		for queryResultIndex, queryResult in enumerate(queryResultList):
			predicateValue = queryResult[u'p'][u'value']
			predicateName = predicateValue.split(u'/')[-1]

			objectType = queryResult[u'o'][u'type']
			objectValue = queryResult[u'o'][u'value']
			
			#if the predicate name corresponds exactly to the requested section of info (limited to the lang specified)
			if predicateName == allInfo and objectType == u'literal' and u'xml:lang' in queryResult[u'o'] and queryResult[u'o'][u'xml:lang'] == lang:
				listOfIsolatedInfo.append(objectValue)
		return listOfIsolatedInfo

	#if we want to capture all the info
	for queryResultIndex, queryResult in enumerate(queryResultList):
		predicateValue = queryResult[u'p'][u'value']
		predicateName = predicateValue.split(u'/')[-1]

		objectType = queryResult[u'o'][u'type']
		objectValue = queryResult[u'o'][u'value']

		#we start by capturing all the literal information 
		#on the first layer of the freebase database
		if objectType == u'literal':
			#if there is a language divided information we
			#only capture the information corresponding to
			#the language we're searching for
			if u'xml:lang' in queryResult[u'o']:
				#avoiding the 'rdf-schema#label' and '22-rdf-syntax-ns#type' predicate
				if queryResult[u'o'][u'xml:lang'] == lang and u'#' not in predicateName:
					dictFreebaseInfo[u'005%s.%s' %(str(queryResultIndex).zfill(6), predicateName)] = objectValue
			#if we find the wikipedia url in the corresponding language
			elif (u'/wikipedia/%s_title/' %(lang)) in objectValue:
				dictFreebaseInfo[u'005%s.%s' %(str(queryResultIndex).zfill(6), u'corresponding_wikipage')] = u'https://%s.wikipedia.org/wiki/%s' %(lang, objectValue.split(u'/')[-1])
			#we discard the wikipedia and freebase metadata and save the rest
			elif u'wikipedia' not in predicateName and u'wikipedia' not in objectValue and u'freebase' not in predicateName and u'object.key' not in predicateName:
				dictFreebaseInfo[u'005%s.%s' %(str(queryResultIndex).zfill(6), predicateName)] = objectValue
		
		#if the object type is not a literal but an uri we have to go
		#one layer deeper using a query to retrieve a literal
		elif objectType == u'uri':
			#avoiding the '22-rdf-syntax-ns#type' predicate
			#and avoiding images, freebase and wikipedia metadata
			if u'#' not in predicateName and u'image' not in predicateName:
				entityName = getEntityName(objectValue, lang, freebaseId)

				if entityName != None:
					#if we don't want to include the type, people(born here) and contains predicates
					if includeTypeAndPeopleAndContainsInformation == False:
						if u'people' not in predicateName and u'type' not in predicateName and u'contains' not in predicateName:
							dictFreebaseInfo[u'005%s.%s' %(str(queryResultIndex).zfill(6), predicateName)] = entityName
					#if we want to include the type, people(born here) and contains predicates
					#wich will add a lot of information slowing the whole process
					else:
						dictFreebaseInfo[u'005%s.%s' %(str(queryResultIndex).zfill(6), predicateName)] = entityName
			
		#if the type is neither a literal nor an uri we raise an error
		else:
			raise TypeError(u'unexpected type of query object :', objectType)
	#if the dict is empty we return None
	if len(dictFreebaseInfo) == 0:
		return None
	else:
		return dictFreebaseInfo


def getInfoWkdataWithBtfulSoup(itemUrl, dictInfoWkdata={}, allInfo=True, lang=u'en'):
	'''
	Scraps a wikidata site info using beautiful soup and returns a dict
	IF we do not scrap all the info, then we obtain the requested info, not a dict
	If we want to scrap some specific information instead 
	#of all the page information, we need to specify it
	by replacing the allInfo argument with the type of 
	information we're looking for:
	'l'	 'label'	 :: the string label of the article
	'd'	 'description'	   :: the string description of the article
	'a'	 'aliases'	   :: the list of aliases of the article
	'c'	 'claims'		:: the list of claims of the article
	'''
	#we try to transform the url to an uri readeable string if it has an iri code in it
	itemUrl = utils.iriToUri(itemUrl)

	articleObject = urllib2.urlopen(itemUrl)
	articleSoup = BeautifulSoup(articleObject.read(), 'lxml', from_encoding=articleObject.info().getparam(u'charset'))

	#information contained in tables
	articleTable = articleSoup.body.findAll('table')
	for tableContent in articleTable:
		#LABEL
		articleLabel = (tableContent.find(u'span', {u'class' : u'wikibase-labelview-text'})).string
		dictInfoWkdata[u'000000000.Label'] = articleLabel
		#specific info return
		if allInfo != True:
			if allInfo.lower() in [u'label', u'lab', u'l']:
				return articleLabel

		#DESCRIPTION
		articleDescription = (tableContent.find(u'span', {u'class' : u'wikibase-descriptionview-text'})).string
		dictInfoWkdata[u'001000000.Description'] = articleDescription
		#specific info return
		if allInfo != True:
			if allInfo.lower() in [u'description', u'descrip', u'd']:
				return articleDescription

		#ALIAS
		articleAliasesList = tableContent.findAll(u'li', {u'class' : u'wikibase-aliasesview-list-item'})
		aliasesList = []

		#saving each alias	  
		for indexL in range(len(articleAliasesList)):
			articleAlias = (articleAliasesList[indexL]).string
			dictInfoWkdata[u'002%s000.Aliases' %(str(indexL).zfill(3))] = articleAlias

			aliasesList.append(articleAlias)
		
		#specific info return
		if allInfo != True:
			if allInfo.lower() in [u'aliases', u'alias', u'a']:
				return aliasesList

	#information otherwise located
	#CLAIMS
	articleClaims = articleSoup.body.findAll(u'div', {u'class' : u'wikibase-statementgrouplistview'})
	claimList = []
	oldKeyName = u''

	for indexXl, claimSection in enumerate(articleClaims):
		claimTypeList = claimSection.findAll(u'div', {u'class' : u'wikibase-statementgroupview'})
		#information divided by type
		for indexL, claimType in enumerate(claimTypeList):
			#capturing the label
			claimLabel = claimType.find(u'div', {u'class' : u'wikibase-statementgroupview-property-label'})
			for labelContainer in claimLabel:
				keyName = (labelContainer.string)
			#capturing the informations
			claimContent = claimType.findAll(u'div', {u'class' : u'wikibase-snakview-value-container'})

			langKeyNameList = []
			keyNameList = []

			for indexM, contentContainer in enumerate(claimContent):
				contentValues = contentContainer.findAll(u'div', {u'class' : u'wikibase-snakview-value wikibase-snakview-variation-valuesnak'})
				#capturing each row of information for each type of information
				for contentRow in contentValues:
					#if the row contains information divided by language, we only select the info corresponding to the concerning language
					if (contentRow.find(u'span', {u'lang' : lang})) != None:
						contentStringsList = contentRow.strings
						langKeyNameList.append(keyName)
					#if the language we want isn't in the right language, we pass
					elif (contentRow.find(u'span', {u'lang': re.compile(ur'[a-z]*')})) != None:
						contentStringsList = None
						langKeyNameList.append(keyName)
					#if the info is a appendice of a language-separated info
					elif keyName in langKeyNameList:
						pass
					#if the info is new and non language-divided
					else:
						contentStringsList = contentRow.strings

					#if we have an info to add to the dict, we add it 
					if contentStringsList != None:
						value = u''
						for cntntString in contentStringsList:
							value += unicode(cntntString)
						#save in dict
						keyInfo = u'%s%s%s.%s' %(str(indexXl+900).zfill(3), str(indexL).zfill(3), str(indexM).zfill(3), keyName)
						#if the key does not exist yet
						if keyInfo not in dictInfoWkdata:
							#if the value is not empty and the key + value is not already in the dict
							if value != u'' and keyName not in keyNameList and value not in dictInfoWkdata.values():
								wordsRe = re.compile(ur'[\w]+', re.UNICODE)
								valueList = wordsRe.findall(value.lower())
								#avoiding wikipedia references and images
								if u'wikipedia' not in valueList and u'jpg' not in valueList and u'gif' not in valueList:
									dictInfoWkdata[keyInfo] = value
									claimList.append(value)
									keyNameList.append(keyName)
								else:
									pass
	#specific info return
	if allInfo != True:
		if allInfo.lower() in [u'claims', u'claim', u'c']:
			return claimList

	return dictInfoWkdata


def getInfoWikidataFromNet(namedEntity, queueWikiData, lang, pywikibotObjList, noDisambiguationSolving):
	'''
	Scraps all wikidata	data in an easy human readeable way
	otherwise: None.
	'''
	dictInfoWkdata = {}

	if len(pywikibotObjList) == 1:
		itemUrl = pywikibotObjList[0]
		#add the information to the dictionnary
		dictInfoWkdata = getInfoWkdataWithBtfulSoup(itemUrl, dictInfoWkdata={}, allInfo=True, lang=lang)

	else:
		#pywikibot objects
		repository = pywikibotObjList[0]
		item = pywikibotObjList[1]
		articleSoup = pywikibotObjList[2]

		try:
			descriptions = item.descriptions
			langDescription = descriptions[lang]
			#if its a disambiguation page we take the pywikibot objects of the first suggestion
			if langDescription in [u'Wikipedia disambiguation page', u'Wikimedia disambiguation page', u'Wikidata disambiguation page', u'Wikipedia disambiguation page\\', u'Wikimedia disambiguation page\\', u'Wikidata disambiguation page\\'] or u'disambiguation page' in langDescription:
				#if we only want to catch the information if there is no ambiguity whatsoever and it's a disambiguation page we return an empty dict
				if noDisambiguationSolving == True:
					return {}
				#if we try to solve naively the disambiguation by taking the first wikidata proposition in the disambiguation page
				else:
					langDescription, item = webUtils.firstElementOfDisambiguationPage(articleSoup, repository, lang)
		except KeyError:
			langDescription = None

		#we get the entry points of the item
		#of the labels
		labels = item.labels
		try:
			dictInfoWkdata[u'001000000.label'] = labels[lang]
		except KeyError:
			pass

		#of the descriptions
		#we already defined the objects when we verified it was not a disambiguation page
		if langDescription != None:
			dictInfoWkdata[u'002000000.description'] = langDescription
		else:
			pass

		#of the aliases
		aliases = item.aliases
		try:
			langAliasList = aliases[lang]
			#we browse the list of aliases
			for indexAlias in range(len(langAliasList)):
				keyAlias = u'003%s000.alias' %(str(indexAlias).zfill(3))
				dictInfoWkdata[keyAlias] = langAliasList[indexAlias]
		except KeyError:
			pass

		#of the claims
		dictClaims = item.claims
		#we browse the dictionnary containing all different kind of claims
		for indexKeyClaim in range(len(dictClaims.keys())):
			keyClaim = dictClaims.keys()[indexKeyClaim]

			#we try to find the text corresponding to this keyClaim code using beautifulsoup
			#so we can try to put the identifiers Ids at the end of the dictionnary
			claimCodeLine = articleSoup.find(u'a', title=(u'Property:'+keyClaim))
			claimCodeName = claimCodeLine.string
			claimCodeParent = claimCodeLine.findPrevious("span", string=u'Identifiers')
			try :
				previousString = claimCodeParent.string
				if previousString == u'Identifiers':
					indexKeyClaim += 900
			except AttributeError:
				pass
			#if the code has no named string or, perhaps, it's not inside an 'a' tag line
			#the we use the original code as a key for the wikidata information dictionnary
			if claimCodeName == None or len(claimCodeName) == 0:
				claimCodeName = keyClaim
			
			#we access the list corresponding to the information of each particular keyclaim
			claimList = dictClaims[keyClaim]
			for indexClaimList in range(len(claimList)):
				keyClaimList = u'004%s%s.%s' % (str(indexKeyClaim).zfill(3), str(indexClaimList).zfill(3), claimCodeName)
				claim = claimList[indexClaimList].getTarget()
				
				#if we encounter a linked wikidata link we try to extract it's label
				#to be used as the value of the wikidata information dictionnary
				try:
					#if it's a linked wikidata link
					content = claim.text
					if type(content) is dict:
						try:
							claimName = claim.labels[lang]
						#if the page of the link exists but has no labels, it must mean 
						#it is incomplete and we must pass
						except KeyError:
							claimName = None
							pass
						
						#if claimname is none, it's probably because the link is a 
						#disambiguation or uncomplete-page, so we pass
						if claimName == None:
							pass

						#if the claimname is a dictionnary, we add each content of the 
						#dictionnary as a new information line, but we keep the same ordering number 
						elif type(claimName) is dict:
							for keyclaimName in claimName:
								dictInfoWkdata[u'%s.%s' %(keyClaimList, keyclaimName)] = claimName[keyclaimName]
						else:
							dictInfoWkdata[keyClaimList] = claimName

					#if it's an image we discard it
					else:
						contentLowercase = content.lower()
						if u'.jpg' in contentLowercase or u'photo' in contentLowercase or u'pronunciation' in contentLowercase or u'image' in contentLowercase or u'file' in contentLowercase:
							pass
				#if we cannot acces the '.text' function
				except KeyError:
					try:
						claimName = claim.labels[lang]
					except KeyError:
						claimName = claim.getID()
					dictInfoWkdata[keyClaimList] = claimName 

				#if it's not a linked wikidata object but information we save the content as is 
				except AttributeError:
					typeClaim = type(claim)
					#if the claim variable is a dictionnary, we add each content of the 
					#dictionnary as a new information line, but we keep the same ordering number 
					if typeClaim is dict:
						for keyclaimName in claim:
							dictInfoWkdata[u'%s.%s'%(keyClaimList, keyclaimName)] = claim[keyclaimName]

					elif typeClaim is unicode:
						dictInfoWkdata[keyClaimList] = claim
						
					#if it's a wiki object (coordinate, quantity, etc)
					else:
						dictWkObjects = webUtils.wikiObjectTreatment(claim, typeClaim, keyClaimList, repository, lang)
						if dictWkObjects != None:
							for wkObjectKey in dictWkObjects:
								dictInfoWkdata[wkObjectKey] = dictWkObjects[wkObjectKey]
	#saving in queue and returning the dict
	if queueWikiData != None:
		queueWikiData.put(dictInfoWkdata) 
	return dictInfoWkdata


def getInfoWikidata(namedEntity, queueWikiData=None, lang='en', noDisambiguationSolving=True):
	'''
	Returns a dictionary containing all the wikidata
	data in an easy human readeable way
	otherwise: None.
	'''
	#get the right search query name by disambiguating
	searchQuery = namedEntity
	######################################
	###searchQuery = getTheRightSearchQuery(namedEntity, wikiOrGoogleOriented='w')
	try:
		print(searchQuery)
	except UnicodeEncodeError:
		pass
	#prepare the pywikibot objects
	site = pywikibot.Site(lang, 'wikipedia')
	repository = site.data_repository()
	page = pywikibot.Page(site, searchQuery)

	try:
		item = pywikibot.ItemPage.fromPage(page)
		#we need to call the item (by using '.get()') to access the data
		item.get()

		#get the url
		wikidataUrl = item.full_url()
		#we try to transform the url to an uri readeable string if it has an iri code in it
		wikidataUrl = utils.iriToUri(wikidataUrl)
		
		#prepare a beautiful soup
		articleObject = urllib2.urlopen(wikidataUrl)
		articleSoup = BeautifulSoup(articleObject.read(), 'lxml', from_encoding=articleObject.info().getparam(u'charset'))
		#we save the pywikibot ojects in a list
		pywikibotObjList = [repository, item, articleSoup]

	#if we encounter a KeyError: u'upperBound' due to the ± character
	except KeyError:
		#defining beautiful soup objects
		pageUrl = page.full_url()
		#we try to transform the url to an uri readeable string if it has an iri code in it
		pageUrl = utils.iriToUri(pageUrl)

		articleObject = urllib2.urlopen(pageUrl)
		articleSoup = BeautifulSoup(articleObject.read(), 'lxml', from_encoding=articleObject.info().getparam(u'charset'))
		#catching the page url
		itemUrl = articleSoup.find(u'a', {u'title' : u'Link to connected data repository item [g]'})[u'href']
		#we save the pywikibot oject (item url) in a list
		pywikibotObjList = [itemUrl]
	#if no page corresponds to the search
	except pywikibot.NoPage:
		print('ERROR no page', namedEntity)
		#saving in queue and returning the dict
		if queueWikiData != None:
			queueWikiData.put(None) 
		#we return an empty dict
		return None
	#if it takes too much time for the API or the API breaks we return an empty dict
	except APIError:
		print('API ERROR maxlag', namedEntity)
		#saving in queue and returning the dict
		if queueWikiData != None:
			queueWikiData.put(None) 
		#we return an empty dict
		return None
	#we get the information in dict form
	dictInfoWkdata = getInfoWikidataFromNet(namedEntity, queueWikiData, lang, pywikibotObjList, noDisambiguationSolving)

	#if the dict is empty we return None
	if len(dictInfoWkdata) == 0:
		if queueWikiData != None:
			queueWikiData.put(None)
		return None

	return dictInfoWkdata


def completeGoogleKnowledgeGraph(dictGoogleKnowGraph, query):
	'''
	We try to extract more information from the google search page
	to try and complete the knowledge graph dict
	'''
	searchPage = utils.iriToUri(u'https://www.google.ca/search?q=%s&lr=lang_en' %(query.replace(u' ', u'+')))

	#first we reformat all the dates already in the dict except for the ones in the description
	for keyKG in dictGoogleKnowGraph:
		#if it's not the entity description
		if u'articleBody' not in keyKG:
			dictGoogleKnowGraph[keyKG] = utils.reformatDates(dictGoogleKnowGraph[keyKG])
	
	#prepare a beautiful soup
	searchPageRequest = urllib2.Request(searchPage, headers={u'User-Agent' : u"Magic Browser"})
	searchPageObject = urllib2.urlopen(searchPageRequest)
	searchPageSoup = BeautifulSoup(searchPageObject.read(), 'lxml', from_encoding=searchPageObject.info().getparam(u'charset'))

	#get the pages urls of the search
	searchKnowGraphInfobox = (searchPageSoup.body).findAll(u'div', {u'class' : u'_o0d'})
	#for each type of fact
	for indexDiv, div in enumerate(searchKnowGraphInfobox):
		divText = div.text
		#catching the name and type
		if indexDiv == 0:
			divChildren = div.findChildren()[1:]
			#we fill the dict if the name and/or type info is missing
			if len(divChildren) == 1 and divChildren[0].text not in dictGoogleKnowGraph.values():
				dictGoogleKnowGraph[u'%s000000.%s' %(str(indexDiv).zfill(3), u'name')] = divChildren[0].text
			elif len(divChildren) == 2:
				if divChildren[0].text not in dictGoogleKnowGraph.values():
					dictGoogleKnowGraph[u'000000000.%s' %(u'name')] = divChildren[0].text
				if divChildren[1].text not in dictGoogleKnowGraph.values():
					dictGoogleKnowGraph[u'000000001.%s' %(u'type')] = divChildren[1].text
			else:
				pass
		#catching other infos
		else:
			knowGraphDateFormat = re.compile(ur'((.+): (January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) [\d]?[\d], [\d]*)|((Born:|Died:) [\d]+)')
			#catching the description
			if divText[-10:len(divText)] == u' Wikipedia':
				descriptionText = divText[:-10]
				if descriptionText not in dictGoogleKnowGraph.values():
					dictGoogleKnowGraph[u'%s000000.%s' %(str(indexDiv).zfill(3), u'detailedDescription.articleBody')] = descriptionText
			#catching and modifying the format of dates (except in the description)
			elif knowGraphDateFormat.match(divText) != None:
				divText = utils.reformatDates(divText)
				#we catch the first column so we can separate the relation of the fact
				firstColumn = divText.index(u':')
				relFact = divText[:firstColumn]
				#we save to the dict
				#if there is a coma after the date, we separate the 2 informations
				if u', ' in divText:
					firstComa = divText.index(u',')
					if divText[(firstColumn+2):] not in dictGoogleKnowGraph.values():
						if divText[(firstColumn+2):firstComa] not in dictGoogleKnowGraph.values():
							#date
							dictGoogleKnowGraph[u'%s000000.%s' %(str(indexDiv).zfill(3), relFact)] = divText[(firstColumn+2):firstComa]
						if divText[(firstComa+2):] not in dictGoogleKnowGraph.values():
							#place
							dictGoogleKnowGraph[u'%s000001.%s' %(str(indexDiv).zfill(3), relFact)] = divText[(firstComa+2):]
				else:
					if divText[(firstColumn+2):] not in dictGoogleKnowGraph.values():
						#date
						dictGoogleKnowGraph[u'%s000000.%s' %(str(indexDiv).zfill(3), relFact)] = divText[(firstColumn+2):]
			#catching the tables
			elif len(div.findAll(u'table')) != 0:
				tableName = div.find(u'div', {u'class' : re.compile(ur'.*')}).text
				#we catch the info in the table row by row, cell by cell
				tableData = []
				tableBody = div.find('tbody')
				rows = tableBody.findAll('tr')
				for row in rows:
					cols = row.findAll('td')
					cols = [ele.text.strip() for ele in cols]
					tableData.append([ele for ele in cols if ele]) # Get rid of empty values
				#we save to the dict
				for indexData, data in enumerate(tableData):
					#if it's a simple table (one column), otherwise it's too complex to add to the dict
					if len(data) == 1:
						dictGoogleKnowGraph[u'%s%s000.%s' %(str(indexDiv).zfill(3), str(indexData).zfill(3), tableName)] = data[0]
			#catching any other info
			elif len(divText) > 0 and u': ' in divText:
				divText = utils.reformatDates(divText)
				firstColumn = divText.index(u':')
				relFact = divText[:firstColumn]
				dictGoogleKnowGraph[u'%s000000.%s' %(str(indexDiv).zfill(3), relFact)] = divText[(firstColumn+2):]
			#empty data
			else:
				#print(div)
				pass
	return dictGoogleKnowGraph


def getGoogleKnowledgeGraph(query, queueKnowGraph=None):
	"""
	Returns a dictionary containing the google
	knowledge graph information.
	#https://developers.google.com/apis-explorer/#p/kgsearch/v1/
	"""
	dictGoogleKnowGraph = {}
	api_key = open('apiKeyKnowledgeGraphAndCustomSearch.api_key').read()
	service_url = 'https://kgsearch.googleapis.com/v1/entities:search'

	#we try to make the query readeable for the adress bar
	query = utils.toUtf8(query)
	
	#tramsform all iri code in the query to uri readeable
	query = utils.iriToUri(query)

	params = {
		'query': query,
		'limit': 10,
		'indent': True,
		'key': api_key,
	}
	
	parameters = (urllib.urlencode(params))
	url = service_url + '?' + parameters
	response = json.loads(urllib.urlopen(url).read())
	
	try:
		#if we find an empty knowledge graph we pass, the dict will be empty and we will return None
		if len(response[u'itemListElement']) == 0:
			pass
		else:
			#possible entities in order of probability score
			bestResultElement = response[u'itemListElement'][0]
			elementContentDict = bestResultElement[u'result']
			#content of the most probable entity
			for elementContentIndex in range(len(elementContentDict)):
				elementContentKey = elementContentDict.keys()[elementContentIndex]
				elementContent = elementContentDict[elementContentKey]
				
				#we discard all keys with the word image in them
				if u'image' not in elementContentKey:
					#we treat the information differently depending on
					#the type of content information
					elementContentType = type(elementContent)

					#if it's unicode we add directly to the dict 
					if elementContentType is unicode:
						dictGoogleKnowGraph[u'%s000000.%s' %(str(elementContentIndex).zfill(3), elementContentKey.replace(u'@', u''))] = elementContent
					#if it's a list every sub-element will be saved under the same key name 
					#(thought the number differs)
					elif elementContentType is list:
						for subElementIndex, subElement in enumerate(elementContent):
													
							dictGoogleKnowGraph[u'%s%s000.%s' %(str(elementContentIndex).zfill(3), str(subElementIndex).zfill(3), elementContentKey.replace(u'@', u''))] = subElement
					#if it's a dict we save the sub-element corresponding to unicode or a list
					elif elementContentType is dict:
						for subElementIndex in range(len(elementContent)):
							subElementKey = elementContent.keys()[subElementIndex]
							subElement = elementContent[subElementKey]
							
							subElementType = type(subElement)
							if subElementType is unicode:			
								dictGoogleKnowGraph[u'%s000%s.%s.%s' %(str(elementContentIndex).zfill(3), str(subElementIndex).zfill(3), elementContentKey.replace(u'@', u''), subElementKey.replace(u'@', u''))] = subElement
							else:
								raise TypeError('unexpected type of value', subElementType)
					else:
						raise TypeError('unexpected type of value', elementContentType)
		#complete the know graph dict the old fashion way: scraping
		dictGoogleKnowGraph = completeGoogleKnowledgeGraph(dictGoogleKnowGraph, query)
	
	#if the page we found is not a knowledge graph page we pass, the dict will be empty and we will return None
	except KeyError:
		pass

	#if we reach the 100/day limit of the google search api, we scrap the google search page using beautifulsoup
	except HttpError:
		#we try to fill the know graph dict the old fashion way: scraping
		dictGoogleKnowGraph = completeGoogleKnowledgeGraph(dictGoogleKnowGraph, query)

	#if the dict is empty we return None
	if len(dictGoogleKnowGraph) == 0:
		if queueKnowGraph != None:
			queueKnowGraph.put(None)
		return None

	#saving in queue and returning the dict
	if queueKnowGraph != None:
		queueKnowGraph.put(dictGoogleKnowGraph)
	return dictGoogleKnowGraph


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