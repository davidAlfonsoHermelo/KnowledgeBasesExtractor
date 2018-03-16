#!/usr/bin/python
#-*- coding:utf-8 -*-


#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-IMPORTATIONS-------------------
from __future__ import print_function

import utils, gs, webUtils, kb

import re, urllib, urllib2, urlparse, Levenshtein
import json, Queue, time, swagger_client
from bs4 import BeautifulSoup
from googleapiclient.errors import HttpError
from urllib2 import HTTPError
from swagger_client.rest import ApiException
from gensim.models import Word2Vec
from nltk.corpus import stopwords


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


def charAnnotDirty(string):
	'''
	Replaces the character placeholder with its original char
	'''
	#in case we get an empty element we return the same
	if string == None:
		return None

	string = string.replace(u'&gt;', u'>')
	string = string.replace(u'&lt;', u'<')
	return string


def gottifOieWrapperAllOie(sentence, reverbDict=None, ollieDict=None, clausieDict=None, stanfordDict=None, openie4Dict=None, propsDict=None):
	'''
	We use gottif@iro.umontreal.ca's platform to access the output from different
	OIEs and we return a dict for every OIE we need
	'''
	#we create a new dict if there is none in argument 
	#(if we predefine each dict in argument as {}, python will not create a new dict each time the function is called, it will only create it once, when the function is defined)
	if reverbDict == None: reverbDict = {}
	if ollieDict == None: ollieDict = {}
	if clausieDict == None: clausieDict = {}
	if stanfordDict == None: stanfordDict = {}
	if openie4Dict == None: openie4Dict = {}
	if propsDict == None: propsDict = {}

	#we replace troublesome characters with a special name, we will change it back later
	sentence = sentence.replace(u'>', u'&gt;')
	sentence = sentence.replace(u'<', u'&lt;')
	#we launch the api
	api_instance = swagger_client.DefaultApi()
	extractors = ['reverb', 'ollie', 'clausie', 'stanford', 'openie', 'props'] # list[str] | The extractors used to extract triples.

	try:
		apiResponse = api_instance.oie_extract_triples_get(sentence, extractors)
		for dictApi in apiResponse:
			#we replace troublesome characters with a variable (instead of colon --> the fullwidth colon '：', 0xEF 0xBC 0x9A (efbc9a)
			if dictApi.arg1 != None:
				arg1 = (dictApi.arg1).replace(u':', u'：')
			#if there is no arg1 (uniplet)
			else:
				arg1 = u'*None'
			rel = (dictApi.rel).replace(u':', u'：')
			if dictApi.arg2 != None:
				arg2 = (dictApi.arg2).replace(u':', u'：')
			#if there is no arg2 (duplet or uniplet)
			else:
				arg2 = u'*None'
			sentence = sentence.replace(u':', u'：')

			#we catch the reverb content 
			if dictApi.extractor == 'reverb':
				tripletRaw = [charAnnotClean(arg1), charAnnotClean(rel), charAnnotClean(arg2)]
				reverbDict[u'_'.join(tripletRaw)] = tripletRaw + [charAnnotClean(sentence)] + [dictApi.score]
			#we catch the ollie content 
			elif dictApi.extractor == 'ollie':
				tripletRaw = [charAnnotClean(arg1), charAnnotClean(rel), charAnnotClean(arg2)]
				ollieDict[u'_'.join(tripletRaw)] = tripletRaw + [charAnnotClean(sentence)] + [dictApi.score]
			#we catch the clausie content except if there was a timeout
			elif dictApi.extractor == 'clausie' and dictApi.rel != u'timeout':
				tripletRaw = [charAnnotClean(arg1), charAnnotClean(rel), charAnnotClean(arg2)]
				clausieDict[u'_'.join(tripletRaw)] = tripletRaw + [charAnnotClean(sentence)] + [dictApi.score]
			#we catch the stanford content
			elif dictApi.extractor == 'stanford':
				tripletRaw = [charAnnotClean(arg1), charAnnotClean(rel), charAnnotClean(arg2)]
				stanfordDict[u'_'.join(tripletRaw)] = tripletRaw + [charAnnotClean(sentence)] + [dictApi.score]
			#we catch the openie-4 content
			elif dictApi.extractor == 'openie':
				tripletRaw = [charAnnotClean(arg1), charAnnotClean(rel), charAnnotClean(arg2)]
				openie4Dict[u'_'.join(tripletRaw)] = tripletRaw + [charAnnotClean(sentence)] + [dictApi.score]
			#we catch the props content
			elif dictApi.extractor == 'props':
				tripletRaw = [charAnnotClean(arg1), charAnnotClean(rel), charAnnotClean(arg2)]
				propsDict[u'_'.join(tripletRaw)] = tripletRaw + [charAnnotClean(sentence)] + [dictApi.score]
	#if there is a problem with the server
	except ApiException as e:
		raise Exception("Exception when calling DefaultApi->oie_extract_triples_get: %s\n" % e)
	return reverbDict, ollieDict, clausieDict, stanfordDict, openie4Dict, propsDict


def gottifOieWrapper(sentence, ollieDict=None, clausieDict=None, openie4Dict=None):
	'''
	We use gottif@iro.umontreal.ca's platform to access the output from different
	OIEs and we return a dict for every OIE we need
	'''
	#we create a new dict if there is none in argument 
	#(if we predefine each dict in argument as {}, python will not create a new dict each time the function is called, it will only create it once, when the function is defined)
	if ollieDict == None: ollieDict = {}
	if clausieDict == None: clausieDict = {}
	if openie4Dict == None: openie4Dict = {}
	
	#we replace troublesome characters with a variable (instead of greater-than --> the full width greater-than '＞', 0xFF1E (ff1e), instead of less-than --> the full width less-than '＜', 	0xFF1C (ff1c))
	#we do not replace yet the colon character with the fullwidth colon because some OIE might detect it and use it for deducing the sens of a sentence
	sentence = sentence.replace(u'>', u'＞')
	sentence = sentence.replace(u'<', u'＜')
	#we launch the api
	api_instance = swagger_client.DefaultApi()
	src_text = sentence # str | The source text
	extractors = ['ollie', 'clausie', 'openie'] # list[str] | The extractors used to extract triples.

	try:
		apiResponse = api_instance.oie_extract_triples_get(src_text, extractors)
		for dictApi in apiResponse:
			#we replace troublesome characters with a variable (instead of colon --> the fullwidth colon '：', 0xEF 0xBC 0x9A (efbc9a)
			arg1 = (dictApi.arg1).replace(u':', u'：')
			rel = (dictApi.rel).replace(u':', u'：')
			if dictApi.arg2 != None:
				arg2 = (dictApi.arg2).replace(u':', u'：')
			sentence = sentence.replace(u':', u'：')

			#we catch the ollie content 
			if dictApi.extractor == 'ollie':
				tripletRaw = [arg1, rel, arg2]
				ollieDict[u'_'.join(tripletRaw)] = tripletRaw + [sentence] + [dictApi.score]
			#we catch the clausie content except if there was a timeout
			elif dictApi.extractor == 'clausie' and dictApi.rel != u'timeout':
				tripletRaw = [arg1, rel, arg2]
				clausieDict[u'_'.join(tripletRaw)] = tripletRaw + [sentence] + [dictApi.score]
			#we catch the openie-4 content
			elif dictApi.extractor == 'openie':
				tripletRaw = [arg1, rel, arg2]
				openie4Dict[u'_'.join(tripletRaw)] = tripletRaw + [sentence] + [dictApi.score]
	#if there is a problem with the server
	except ApiException as e:
		raise Exception("Exception when calling DefaultApi->oie_extract_triples_get: %s\n" % e)
	return ollieDict, clausieDict, openie4Dict


def gottifOieWrapperNet(sentence, ollieDict={}, clausieDict={}, openie4Dict={}):
	'''
	We use gottif@iro.umontreal.ca's platform to access the output from different
	OIEs and we return a dict for every OIE we need
	'''
	#we replace troublesome characters with a variable (instead of greater-than --> the full width greater-than '＞', 0xFF1E (ff1e), instead of less-than --> the full width less-than '＜', 	0xFF1C (ff1c))
	#we do not replace yet the colon character with the fullwidth colon because some OIE might detect it and use it for deducing the sens of a sentence
	sentence = sentence.replace(u'>', u'＞')
	sentence = sentence.replace(u'<', u'＜')

	#we encode the text into its html entities (so we can use it in the url)
	sentenceQuote = urllib2.quote(sentence.encode('utf8'))
	#request page
	urlRequestPageUdem ='''http://www-etud.iro.umontreal.ca/~gottif/cyber/prototypes/buddleia/extract_triples?src_text=%s&extractors=reverb,ollie,clausie,stanford,openie''' %(sentenceQuote)
	
	#prepare a beautiful soup
	oiePageRequest = urllib2.Request(urlRequestPageUdem, headers={u'User-Agent' : u"Magic Browser"})
	oiePageObject = None
	counter = 0
	#we try to catch possible server errors
	while oiePageObject is None:
		counter += 1
		try:
			oiePageObject = urllib2.urlopen(oiePageRequest)
			
		except urllib2.HTTPError as err:
			#exceeded capacity of the server (error 502)
			if err.code == 502:
				#we retry 20 times
				if counter >= 20:
					raise Exception('gottifOieWrapperNet has a recursive 502 http error')
				#if we exceed capacity of the server (error 502), we retry after 1 sec
				time.sleep(counter)
				oiePageObject = urllib2.urlopen(oiePageRequest)
			else:
				raise Exception('%s http error in the function gottifOieWrapperNet' %(err.code))
	
	oiePageSoup = BeautifulSoup(oiePageObject.read(), 'lxml', from_encoding=oiePageObject.info().getparam(u'charset'))
	#get the data
	oieResultsUnicode = (oiePageSoup.body).find(u'p')
	#transform it from unicode to json format
	oieResultsContent = oieResultsUnicode.renderContents()
	#if there is a auto-closed none tag at the end of the json data ('</none>')
	#added because there is a none tag inside the json data so it creates a closing none tag
	if (oieResultsContent[len(oieResultsContent)-14:len(oieResultsContent)]) == u'</none></none>':
		oieResultsJsonList = json.loads(oieResultsContent[:-14])
	elif (oieResultsContent[len(oieResultsContent)-7:len(oieResultsContent)]) == u'</none>':
		oieResultsJsonList = json.loads(oieResultsContent[:-7])
	else:
		try: 
			oieResultsJsonList = json.loads(oieResultsContent)
		except ValueError:
			print(u'There was a problem in the oie wrapper because of the sentence:\n   %s' %(sentence))
			oieResultsJsonList = None

	#we save the wanted data to it's corresponding dict
	if oieResultsJsonList != None:
		for indexExtractor in range(len(oieResultsJsonList)):
			#we replace troublesome characters with a variable (instead of colon --> the fullwidth colon '：', 0xEF 0xBC 0x9A (efbc9a)
			arg1 = (oieResultsJsonList[indexExtractor][u'arg1']).replace(u':', u'：')
			rel = (oieResultsJsonList[indexExtractor][u'rel']).replace(u':', u'：')
			arg2 = (oieResultsJsonList[indexExtractor][u'arg2']).replace(u':', u'：')
			sentence = sentence.replace(u':', u'：')
			
			#ollie
			if oieResultsJsonList[indexExtractor][u'extractor'] == u'ollie':
				#we add the triplets to the dict (using the whole triplet as key)
				tripletRaw = [arg1, rel, arg2]
				ollieDict[u'_'.join(tripletRaw)] = tripletRaw + [sentence] + [oieResultsJsonList[indexExtractor][u'score']]
			#clausie
			elif oieResultsJsonList[indexExtractor][u'extractor'] == u'clausie':
				#we add the triplets to the dict (using the whole triplet as key)
				#we replace the unescaped slash with a normal slash
				tripletRaw = [arg1.replace(u'\/', u'/'), rel.replace(u'\/', u'/'), arg2.replace(u'\/', u'/')]
				clausieDict[u'_'.join(tripletRaw)] = tripletRaw + [sentence] + [oieResultsJsonList[indexExtractor][u'score']]
			#openie-4
			if oieResultsJsonList[indexExtractor][u'extractor'] == u'openie':
				#we add the triplets to the dict (using the whole triplet as key)
				tripletRaw = [arg1, rel, arg2]
				openie4Dict[u'_'.join(tripletRaw)] = tripletRaw + [sentence] + [oieResultsJsonList[indexExtractor][u'score']]
	return ollieDict, clausieDict, openie4Dict


def findCommonOnesOverCosLimit(listBase, listRemover, sumOfCosLimit=0.5):
	'''
	Removing the elements of the base list if the similarity between the elements is below the limit
	'''
	commonTripletsList = []
	dejaVusList = []

	#analysing the triplets to find the ones in common
	for indexTripletBase, tripletBase in enumerate(listBase):

		#if the triplet is not empty and isn't already in the list
		if tripletBase != None:
			for tripletRemover in listRemover:
				#if the triplet is not empty and the base triplet isn't already in the common list
				if tripletRemover != None and indexTripletBase not in dejaVusList:
					#we calculate the levenshtein similarity of the relation and object
					cosSimilSubj = Levenshtein.ratio(tripletBase[0], tripletRemover[0])
					cosSimilRel = Levenshtein.ratio(tripletBase[1], tripletRemover[1])
					cosSimilObj = Levenshtein.ratio(tripletBase[2], tripletRemover[2])
					#if the similarity score sum is under the satisfying level 
					if ((cosSimilSubj+cosSimilRel+cosSimilObj)/3) > sumOfCosLimit:
						#we add it to the list of common triplets
						try:
							commonTripletsList.append(tripletBase)
							dejaVusList.append(indexTripletBase)
						#if the common triplets list is so big we're out of memory, we return it.
						except MemoryError:
							#print(44444444444444444444, 'WE HAVE A MEMORY ERROR IN findCommonOnesOverCosLimit')
							return commonTripletsList
	return commonTripletsList


def launchWord2VecModel(path2Model='../041word2vecModelEnWiki/en_1000_no_stem/en.model'):
	'''
	Loads the word2vec model and returns the model python object.
	'''
	model = Word2Vec.load(path2Model)
	return model


def findCommonOnesOverEmbeddingPathLimit(word2VecModel, entity, triplet, similLimit=0.75):
	'''
	We remove the words of the list if the similarity between the elements is below the limit
	'''
	subject = triplet.split(u': ')[0]
	try:
		if u'_' not in entity and u'_' not in subject:
			embeddSimilarity = model.similarity(entity, subject)
		elif u' ' not in entity and u' ' not in subject:
			embeddSimilarity = model.similarity(entity, subject)
		#if there are multiple words in the entity or the subject we run word2vec multiple times and calculate the mean of all the results
		else:
			#we split and clean the subject and entity
			entityList = [word for word in entity.split(u'_') if word not in stopwords.words('english')]
			subjectList = [word for word in subject.split(u'_') if word not in stopwords.words('english')]
			entitySubjectCombinationsList = [zip(x, subjectList) for x in itertools.permutations(entityList, len(subjectList))]
			totalDistanceSum = 0.0
			#we browse the lists of lists and we make the mean of distances as one distance
			if len(entitySubjectCombinationsList) > 0:
				for combinationList in entitySubjectCombinationsList:
					subListDistanceSum = 0.0
					if len(combinationList) > 0:
						for combination in combinationList:
							subListDistanceSum += model.similarity(combination[0], combination[1])
						totalDistanceSum += subListDistanceSum / len(combinationList)
				embeddSimilarity = totalDistanceSum / len(entitySubjectCombinationsList)
			else:
				embeddSimilarity = 0.0
	except KeyError:
		embeddSimilarity = 0.0
	#frontier score parameter
	if embeddSimilarity >= similLimit: 
		return triplet


def findTripletsInCommon(articleName, openie4OutputDict, ollieOutputDict, clausieOutputDict, aliasListWords, commonFilteredInfoList, sumOfCosLimit, word2VecModel, noFilter):
	'''
	Takes the Open Information Extractors produced triplet Dict, 
	finds the triplets in common and if they are above
	the given limit it's added to the list of confirmed triplets
	'''
	#if we have a openie4 dict (the main dict) and a clausie dict
	if openie4OutputDict != None and clausieOutputDict != None:
		#analysing the triplets to find the ones in common
		commonTripletsListClausieOpenie4 = findCommonOnesOverCosLimit(openie4OutputDict.values(), clausieOutputDict.values(), sumOfCosLimit)
	#if we have a openie4 dict
	elif openie4OutputDict != None and clausieOutputDict == None:
		#analysing the triplets to find the ones in common
		commonTripletsListClausieOpenie4 = openie4OutputDict.values()
	#if we have a clausie dict
	elif openie4OutputDict == None and clausieOutputDict != None:
		#analysing the triplets to find the ones in common
		commonTripletsListClausieOpenie4 = clausieOutputDict.values()
	else:
		commonTripletsListClausieOpenie4 = []

	#if we have a openie4 dict (the main dict) and an ollie dict
	if openie4OutputDict != None and ollieOutputDict != None:
		#analysing the triplets to find the ones in common
		commonTripletsListOpenie4Ollie = findCommonOnesOverCosLimit(openie4OutputDict.values(), ollieOutputDict.values(), sumOfCosLimit)
	#if we have a openie4 dict
	elif openie4OutputDict != None and ollieOutputDict == None:
		#analysing the triplets to find the ones in common
		commonTripletsListOpenie4Ollie = openie4OutputDict.values()
	#if we have an ollie dict
	elif openie4OutputDict == None and ollieOutputDict != None:
		#analysing the triplets to find the ones in common
		commonTripletsListOpenie4Ollie = ollieOutputDict.values()
	else:
		commonTripletsListOpenie4Ollie = []

	#intersection of the 2 lists
	commonTripletsList = findCommonOnesOverCosLimit(commonTripletsListClausieOpenie4, commonTripletsListOpenie4Ollie, sumOfCosLimit)
	
	#no filter
	###commonFilteredInfoList = commonTripletsList
	
	#naive heuristics filter on each oie output individually 
	##########################################


	#naive heuristics filter on all oie outputs put in common 
	commonFilteredInfoList = gs.tripletsFilterSubjectBased(commonTripletsList, articleName, commonFilteredInfoList, aliasListWords, word2VecModel, correspondences=[0, 1, 2, 3, 4, 5])
	
	#clean triplets with 'to be' as relation
	#at this level the triplets have 3 elements again
	###commonFilteredInfoList = verbCleaner(commonTripletsList, commonFilteredInfoList)
	###############################################################
	return commonFilteredInfoList


def getAliasList(namedEntity=None, articleName=None, wikidataUrl=None):
	'''
	Interrogates Wikidata and Freebase to optain a list of aliases for a given entity
	'''
	aliasListWords = []

	#making a list of named entity aliases, divided by individual words
	#wikidata
	if wikidataUrl != None:
		aliasListWikidata = kb.getInfoWkdataWithBtfulSoup(wikidataUrl, dictInfoWkdata={}, allInfo=u'alias', lang=u'en')
	#if the url is not given we go and look for it
	else:
		try:
			listParagraphsWiki, nameOfArticle, wikidataUrl = (webUtils.getWikipediaPage(namedEntity, False))
			#if the wikidata page still exists
			if wikidataUrl != None:
				aliasListWikidata = kb.getInfoWkdataWithBtfulSoup(wikidataUrl, dictInfoWkdata={}, allInfo=u'alias', lang=u'en')
			#if the page does not exist anymore
			else:
				aliasListWikidata = []

			if articleName == None:
				articleName = nameOfArticle
		#if we can't find a wikipedia article
		except TypeError:
			aliasListWikidata = []
		
	#freebase
	try:
		if namedEntity != None:
			aliasListFreebase = kb.getInfoFreebase(namedEntity, dictInfoWkdata={}, lang=u'en', includeTypeAndPeopleAndContainsInformation=False, allInfo=u'common.topic.alias')
		elif articleName != None:
			aliasListFreebase = kb.getInfoFreebase(articleName, dictInfoWkdata={}, lang=u'en', includeTypeAndPeopleAndContainsInformation=False, allInfo=u'common.topic.alias')
		else:
			aliasListFreebase = []
	except requests.exceptions.ConnectTimeout:
		aliasListFreebase = []

	#we join the both of them
	aliasListWords = filter(None, (aliasListWikidata + aliasListFreebase))
	#we add the individual words of the aliases
	for alias in list(aliasListWords):
		words = re.compile(ur'[\w]+', re.UNICODE)
		aliasWords = words.findall(alias)
		for word in aliasWords:
			aliasListWords.append(word)
	#we supress doubles from the list
	aliasListWords = list(set(aliasListWords))

	return aliasListWords


def sourceConfirmedTripletInformation(string, articleName, wikidataUrl, noFilterFindingTripletsInCommon, nameOfFolderWhereDidWeGetThoseStrings, originalNamedEntity, word2VecModel, overwrite):
	'''
	Compares the openie4 output dict and the ollie output dict and 
	returns a list of the information that appears in both of them
	'''
	commonFilteredInfoList = []
	
	#if there is no article name
	if articleName == None:
		articleName = ''

	#making a list of named entity aliases taken from wikidata and freebase, with their individual tokens added to the list
	aliasListWords = getAliasList(originalNamedEntity, articleName, wikidataUrl)

	#we clean the string of all wikipedia-like references
	string = utils.stringCleaner(string)

	#make the dicts of string triplets
	ollieOutputDict={}
	clausieOutputDict={}
	openie4OutputDict={}

	#sentence tokenizer 
	sentencesList = utils.sentenceSplitter(string)
	for sentence in sentencesList:
		try: 
			ollieOutputDict, clausieOutputDict, openie4OutputDict = gottifOieWrapper(sentence, ollieOutputDict, clausieOutputDict, openie4OutputDict)
			#if, for some reason, the dicts are all empty, we retry using the web query method of the gottifwrapper
			if len(ollieOutputDict)+len(clausieOutputDict)+len(openie4OutputDict) == 0:
				ollieOutputDict, clausieOutputDict, openie4OutputDict = gottifOieWrapperNet(sentence, ollieOutputDict, clausieOutputDict, openie4OutputDict)
		#if there is an error with the api, we try using the web query method of the gottifwrapper
		except Exception:
			ollieOutputDict, clausieOutputDict, openie4OutputDict = gottifOieWrapperNet(sentence, ollieOutputDict, clausieOutputDict, openie4OutputDict)

	#########################################################################################################
	#we save all given triplets in a dir before aplying the filters to have a comparison base
	###gs.allTripletsSaver(openie4OutputDict, ollieOutputDict, clausieOutputDict, articleName, nameOfFolderWhereDidWeGetThoseStrings, joinedOutputs=False, originalNamedEntity=originalNamedEntity, overwrite=overwrite)
	########################################################################################################

	#analysing the triplets to find the ones in common
	sumOfCosLimit = 0.70
	commonFilteredInfoList = findTripletsInCommon(articleName, openie4OutputDict, ollieOutputDict, clausieOutputDict, aliasListWords, commonFilteredInfoList, sumOfCosLimit, word2VecModel, noFilterFindingTripletsInCommon)

	'''###############################################################################
	#if the limit of cosinus sum is too high and we have no results we lower it until we have at least 6 results but never under 0.3
	for nb in range(8):
		if len(commonFilteredInfoList) < 6:
			sumOfCosLimit -= 0.05
			commonFilteredInfoList = findTripletsInCommon(articleName, openie4OutputDict, ollieOutputDict, clausieOutputDict, aliasListWords, commonFilteredInfoList, sumOfCosLimit, word2VecModel, noFilterFindingTripletsInCommon)
		else:
			break
	'''###############################################################################
	#we clean the list of lists of any list element that has the relation and object in double
	commonFilteredInfoList = utils.cleanListOfList(commonFilteredInfoList)
	return commonFilteredInfoList


def dictMakerFromString(stringOrListOfStrings, articleName=None, wikidataUrl=None, noFilterFindingTripletsInCommon=True, nameOfFolderWhereDidWeGetThoseStrings='unkwnown', originalNamedEntity=None, word2VecModel=None, overwrite=True):
	'''
	Using open information extractors (OIE)
	we transform a string or a list of strings into triplets for wich we
	asume one absolute common subject. So we save the triplet-relation 
	as a key and the triplet-object as a value.
	'''
	tripletsFromRawDict = {}
	elementType = type(stringOrListOfStrings)

	#if the argument is a string we run the OIEs only once for the whole string
	if elementType is str or elementType is unicode:
		#we try to clean the string from all wikipedia-like reference
		stringOrListOfStrings = re.sub(ur'\[[\d]+\]|\[.*needed\]|\[not verified.*\]|\[note.*\]|\(.*listen\)', u'', stringOrListOfStrings)
		#we capture the triplets appearing in both binary relation extractors as a list of lists
		tripletsList = sourceConfirmedTripletInformation(stringOrListOfStrings, articleName, wikidataUrl, noFilterFindingTripletsInCommon, nameOfFolderWhereDidWeGetThoseStrings, originalNamedEntity, word2VecModel, overwrite)
		#if the function found confirmed triplets
		if len(tripletsList) > 0:
			for indexTriplet, triplet in enumerate(tripletsList):
				if triplet != None:
					#we add the replacement triplets to the dict
					tripletsFromRawDict['%s.%s' %(str(indexTriplet).zfill(9), triplet[1])] = triplet[2]
	#if the argument is a list of strings we run the OIEs multiple times
	elif elementType is list:
		for indexString in range(len(stringOrListOfStrings)):
			string = stringOrListOfStrings[indexString]
			#we try to clean the string from all wikipedia-like reference
			string = re.sub(ur'\[[\d]+\]|\[.*needed\]|\[not verified.*\]|\[note.*\]|\(.*listen\)', u'', string)
			#we capture the triplets appearing in both binary relation extractors as a list of lists
			tripletsList = sourceConfirmedTripletInformation(string, articleName, wikidataUrl, noFilterFindingTripletsInCommon, nameOfFolderWhereDidWeGetThoseStrings, originalNamedEntity, word2VecModel, overwrite)

			#if the function found confirmed triplets
			if len(tripletsList) > 0:
				for indexTriplet, triplet in enumerate(tripletsList):
					#we add the replacement triplets to the dict
					tripletsFromRawDict['000%s%s.%s' %(str(indexString).zfill(3), str(indexTriplet).zfill(3), triplet[1])] = triplet[2]
					############################################################################
					#JUST TO SHOW THE WHOLE TRIPLET
					#########tripletsFromRawDict['000%s%s.%s:%s' %(str(indexString).zfill(3), str(indexTriplet).zfill(3), triplet[0], triplet[1])] = triplet[2]
					############################################################################
	#if the argument is nor string nor list
	else:
		raise TypeError(u'unexpected type of argument, please use a string or a list of strings exclusively')
	return tripletsFromRawDict
	

def getWikipediaIntroAsDict(namedEntity, queueIntro=None, noFilterFindingTripletsInCommon=True, originalNamedEntity=None, word2VecModel=None, overwrite=True):
	'''
	Scraps the wikipedia for the article's intoduction and returns
	a dict containing the resumed information (it's returned in a 
	queue so it can be threaded and processend simultaneously 
	to another function)
	'''
	try:
		listIntroWiki, articleName, wikidataUrl = (webUtils.getIntroWikipedia(namedEntity, False))
	#if we can't find a wikipedia intro, we return None and save None in queue
	except TypeError:
		if queueIntro != None:
			queueIntro.put(None) 
		return None
	#listIntroWiki = list(set(listIntroWiki))
	introDict = dictMakerFromString(listIntroWiki, articleName, wikidataUrl, noFilterFindingTripletsInCommon, 'wikipediaIntro', originalNamedEntity, word2VecModel, overwrite)

	#if the dict is empty we return None
	if len(introDict) == 0:
		if queueIntro != None:
			queueIntro.put(None)
		return None

	#saving in queue and returning the dict
	if queueIntro != None:
		queueIntro.put(introDict) 
	return introDict


def getWikipediaAsDict(namedEntity, queueWiki=None, noFilterFindingTripletsInCommon=True, originalNamedEntity=None, word2VecModel=None, overwrite=True):
	'''
	Scraps the wikipedia for the article's text and returns
	a dict containing the resumed information (it's returned in a 
	queue so it can be threaded and processend simultaneously 
	to another function)
	'''
	try:
		listParagraphsWiki, articleName, wikidataUrl = (webUtils.getWikipediaPage(namedEntity, False))
	#if we can't find a wikipedia intro, we return None and save None in queue
	except TypeError:
		if queueWiki != None:
			queueWiki.put(None) 
		return None
	wikiDict = dictMakerFromString(listParagraphsWiki, articleName, wikidataUrl, noFilterFindingTripletsInCommon, 'wikipedia', originalNamedEntity, word2VecModel, overwrite)

	#if the dict is empty we return None
	if len(wikiDict) == 0:
		if queueWiki != None:
			queueWiki.put(None)
		return None

	#saving in queue and returning the dict
	if queueWiki != None:
		queueWiki.put(wikiDict) 
	return wikiDict


def getGoogleFirstPagesAsDict(namedEntity, queueGoogleFirstPagesText=None, nbOfPages=10, noFilterFindingTripletsInCommon=True, includeWikipedia=True, originalNamedEntity=None, word2VecModel=None, overwrite=True):
	'''
	Scraps the content of the google search first pages and returns 
	a dict containing the triplets
	'''

	#we try to find the possible aliases by searching for the wikipedia article name,
	#the wikidata code by looking in the wikidata name
	articleName = namedEntity
	#########################
	articleName = webUtils.getTheRightSearchQuery(namedEntity, wikiOrGoogleOriented='w')
	if articleName != None:
		articleNameNoSpace = articleName.replace(u' ', u'_')
		#we try to transform the article name to an uri readeable string if it has an iri code in it
		articleNameNoSpace = utils.iriToUri(articleNameNoSpace)

		#get the article url
		articleUrl = u'https://en.wikipedia.org/wiki/%s' %(articleNameNoSpace)
		#prepare a beautiful soup
		try:
			articleObject = urllib2.urlopen(articleUrl.encode('utf8'))
			articleSoup = BeautifulSoup(articleObject.read(), 'lxml', from_encoding=articleObject.info().getparam(u'charset'))
			#we scrap the wikidata url from wikipedia
			wikidataRow = articleSoup.body.find(u'a', {u'title' : u'Link to connected data repository item [g]'})
			wikidataUrl = wikidataRow.attrs[u'href']
			
		#if we can't find the page the wikidata url probably won't exist either and the wikidataUrl is None
		except HTTPError:
			wikidataUrl = None
	else:
		wikidataUrl = None
	#we get the google first pages text
	textGoogleFirstPages  = '. '.join(webUtils.getGoogleFirstPages(namedEntity, nbOfPages, includeWikipedia))
	#we get the dict of triplets
	googleFirstPagesDict = dictMakerFromString(textGoogleFirstPages, articleName, wikidataUrl, noFilterFindingTripletsInCommon, 'googleFirstPages', originalNamedEntity, word2VecModel, overwrite)

	#if the dict is empty we return None
	if len(googleFirstPagesDict) == 0:
		if queueGoogleFirstPagesText != None:
			queueGoogleFirstPagesText.put(None)
		return None

	#saving in queue and returning the dict
	if queueGoogleFirstPagesText != None:
		queueGoogleFirstPagesText.put(googleFirstPagesDict)
	return googleFirstPagesDict


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