#!/usr/bin/python
#-*- coding:utf-8 -*-


#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-IMPORTATIONS-------------------
import utils, kb, oie, webUtils

import os, Queue, gensim


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


def mrHolmesLaunched(searchQuery, lang=u'en', originalNamedEntity=None, word2VecModel=None, overwrite=True):
	'''
	Launches all the functions together to
	produce the 5 result dictionaries:

	dictInfoWkdata, 
	dictFreebase, 
	dictGoogleKnowGraph, 
	dictIntroWiki, 
	dictGoogleSearchResults

	in that order.
	'''
	#QUEUE INITIALIZING
	queueIntro = None
	queueWiki = None
	queueWikiData = None
	queueKnowGraph = None
	queueGoogleSearchResults = None

	#Knowledge Graphs
	#WIKIDATA #we do not solve naively the ambiguity, if its a disambiguation page we will get an empty dict
	dictInfoWkdata = None
	###dictInfoWkdata = kb.getInfoWikidata(searchQuery, queueWikiData, lang, noDisambiguationSolving=True)
	print('WIKIDATA', searchQuery)
	#GOOGLE KNOWLEDGE GRAPH
	dictGoogleKnowGraph = None
	###dictGoogleKnowGraph = kb.getGoogleKnowledgeGraph(searchQuery, queueKnowGraph)
	print('KNOWLEDGE GRAPH', searchQuery)
	#FREEBASE
	dictFreebase = None
	###dictFreebase = kb.getInfoFreebase(searchQuery, dictInfoWkdata, lang)
	print('FREEBASE', searchQuery)

	#Open Information Extractors
	#WIKIPEDIA INTRO
	#dictIntroWiki = None
	dictIntroWiki = oie.getWikipediaIntroAsDict(searchQuery, queueIntro, True, originalNamedEntity, word2VecModel, overwrite)
	print('WIKIPEDIA INTRO', searchQuery)
	#WIKIPEDIA PAGE
	#dictWikipedia = None
	dictWikipedia = oie.getWikipediaAsDict(searchQuery, queueWiki, True, originalNamedEntity, word2VecModel, overwrite)
	print('WIKIPEDIA', searchQuery)
	#WEBPAGE TEXT FROM GOOGLE FIRST SEARCH RESULTS
	#dictGoogleSearchResults = None
	dictGoogleSearchResults = oie.getGoogleFirstPagesAsDict(searchQuery, queueGoogleSearchResults, 10, True, True, originalNamedEntity, word2VecModel, overwrite)
	print('GOOGLE FIRST SEARCH RESULTS', searchQuery)

	return dictInfoWkdata, dictFreebase, dictGoogleKnowGraph, dictIntroWiki, dictWikipedia, dictGoogleSearchResults


#--------------END-FONCTIONS-------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------



#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-DECLARATIONS-------------------


lang = u'en'
searchQuery = u'batman'
#searchQuery = raw_input('input:')

path2Output = '../047filteredChillyOieOutput/'
###path2Output = '../043KbAndOieOutputsRandomEntities/'

if not os.path.exists(path2Output):
	os.makedirs(path2Output)


#name of the dicts (for the column names in the tsv file)
nameOfColumns = [
	u'From Wikidata', 
	u'From Freebase', 
	u'From Google Knowledge Graph', 
	u'From the Wikipedia Intro', 
	u'From Wikipedia', 
	u'From 10 webpages (Google Search)']

overwrite = True

#--------------END-DECLARATIONS-------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-COMMANDES-------------------


if __name__ == '__main__':
	
	
	#LAUNCH OF MRHOLMES
	#------------------#

	#FREEBASE STARTER
	#if it's not already on: starting Freebase to be able to interrogate it effortlessly
	#kb.startFreebaseRunning()

	#WORD2VEC MODEL STARTED
	print('LOADING Word2Vec MODEL')
	word2VecModel = gensim.models.Word2Vec.load("../041word2vecModelEnWiki/en_1000_no_stem/en.model")
	print('MODEL LOADED')


	#listOfNamedEntities = getRandomPseudoNamedEntities()
	#listOfNamedEntities = [u'Paramecus', u'Copelatus unguicularis', u'1927 World Snooker Championship', u'Moustached brush finch', u'Hans Jacob Horst', u'Easingwold', u'Hugh Borton', u'YIT', u'Battle of Whitestone Hill', u'Micropogonias', u'27056 Ginoloria', u'Spargaloma sexpunctata', u'Surinder Vasal', u'MILGEM project', u'Neadeloides', u'Temnora sardanus', u'Dobrogea Veche', u'Soltam M-71', u'Chilly Gonzales', u'Hellboy: Blood and Iron']
	listOfNamedEntities = [u'Chilly Gonzales']
	
	#we clean the dir we<re going to use
	utils.emptyTheFolder(path2Output, [u'tsv', u'wikidata', u'freebase', u'knowGraph', u'wikipediaIntro', u'wikipedia', u'googleSearch'])
	
	#ALL NAMED ENTITIES IN A LIST (NO MENTION OF AMBIGUITY OR SUGGESTIONS)
	entitiesListOrDict = listOfNamedEntities
	
	#ALL NAMED ENTITIES IN A DICT (ALL SUGGERSTIONS AN AMBIGUITIES PER EACH NAMED ENTITY)
	#we get not only the queries but all of google and wikipedia possible suggestions
	#entitiesListOrDict = getAllPossibleQueries(listOfNamedEntities)

	for namedEntityKey in entitiesListOrDict:
		namedEntityKey = utils.toUtf8(namedEntityKey)

		#if we just search for the query(ies) no suggestions nor ambiguities
		if type(entitiesListOrDict) is list:
			suggestionsListValue = [None]


		#if we searched for all possibilities of suggestions and ambiguities
		elif type(entitiesListOrDict) is dict:
			suggestionsListValue = entitiesListOrDict[namedEntityKey]

		print(11111111111111111, namedEntityKey)
		#we lauch the prog for each suggestion individually
		for suggestion in suggestionsListValue:
			if suggestion != None:
				suggestion = toUtf8(suggestion)
				#we name the file
				nameOfFile = (u'%s.%s' %(namedEntityKey, suggestion))
			else:
				suggestion = utils.toUtf8(namedEntityKey)
				#we name the file
				nameOfFile = namedEntityKey

			#if we don't want to overwrite the files, we look and see if the file already exists before launching
			if overwrite == False:
				fileExists = utils.theFileExists(path2Output, nameOfFile)
			else:
				fileExists = False
			#if the file doesn't already exists or if we don't care if we overwrite it
			if fileExists == False:
				#DELETING THE FILES (if they already exist)
				utils.deleteTheFile(path2Output, nameOfFile, u'wikidata')
				utils.deleteTheFile(path2Output, nameOfFile, u'freebase')
				utils.deleteTheFile(path2Output, nameOfFile, u'knowGraph')
				utils.deleteTheFile(path2Output, nameOfFile, u'wikipediaIntro')
				utils.deleteTheFile(path2Output, nameOfFile, u'wikipedia')
				utils.deleteTheFile(path2Output, nameOfFile, u'googleSearch')

				#LAUNCHING AND GETTING THE INFO
				#no suggestions or errors in queries
				listOfTheDicts = list(mrHolmesLaunched(suggestion, lang, originalNamedEntity=None, word2VecModel=word2VecModel, overwrite=overwrite))
				#possible suggestions or variants or errors in query
				###listOfTheDicts = list(mrHolmesLaunched(suggestion, lang, namedEntityKey, overwrite=overwrite))
				##########################################################################################################################
				#JUST to make the masters thesis calculation, we make sure before dumping that there is something in every simgle dict
				#if listOfTheDicts[0] != None and listOfTheDicts[1] != None and listOfTheDicts[2] != None :
				##########################################################################################################################

				#RESULTS DUMPED IN A FILE (one by one)
				#utils.transformsDictsInTsv([listOfTheDicts[0]], [nameOfColumns[0]], nameOfFile, path2Output, fileExtension=u'wikidata')
				#utils.transformsDictsInTsv([listOfTheDicts[1]], [nameOfColumns[1]], nameOfFile, path2Output, fileExtension=u'freebase')
				#utils.transformsDictsInTsv([listOfTheDicts[2]], [nameOfColumns[2]], nameOfFile, path2Output, fileExtension=u'knowGraph')
				utils.transformsDictsInTsv([listOfTheDicts[3]], [nameOfColumns[3]], nameOfFile, path2Output, fileExtension=u'wikipediaIntro')
				utils.transformsDictsInTsv([listOfTheDicts[4]], [nameOfColumns[4]], nameOfFile, path2Output, fileExtension=u'wikipedia')
				utils.transformsDictsInTsv([listOfTheDicts[5]], [nameOfColumns[5]], nameOfFile, path2Output, fileExtension=u'googleSearch')


	kb.deleteTheFreebaseLockFile(pathToLockFile=u'/data/rali6/Tmp/Freebase/Index/')
	

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