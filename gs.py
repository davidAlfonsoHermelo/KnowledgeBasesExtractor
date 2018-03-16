#!/usr/bin/python
#-*- coding:utf-8 -*-


#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-IMPORTATIONS-------------------
import utils

import os, re, urlparse, random
import collections, Levenshtein, gensim
from nltk.corpus import stopwords
import numpy as np
from scipy import spatial


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


def getEmbeddingSimilarity(string1, string2, model):
	'''
	returns the embedding similarity score between 
	0 (not similar) and 1 (very similar)
	'''
	string1 = utils.cleanedArticleName(string1)
	string2 = utils.cleanedArticleName(string2)
	try:
		if u' ' not in string1 and u' ' not in string2:
			embeddSimilarity = model.similarity(string1, string2)
		#if there are multiple words in the string1 or the string2 we run word2vec multiple times and calculate the mean of all the results
		else:
			#we split and clean the string2 and string1
			string1List = [word for word in string1.split(u' ') if word not in stopwords.words('english')]
			string2List = [word for word in string2.split(u' ') if word not in stopwords.words('english')]
			#we add the vectors of all the tokens in the string1List
			string1VectorsTemp = np.zeros(len(model.wv[string1List[0]]))
			
			for string1Token in list(string1List):
				string1VectorsTemp = np.add(string1VectorsTemp, model.wv[string1Token])
			#we divide the vectors by the nb of entities so we obtain a mean vector
			string1VectorsTemp = np.divide(string1VectorsTemp, len(string1List))

			#we add the vectors of all the tokens in the string2list
			string2VectorsTemp = np.zeros(len(model.wv[string1List[0]]))
			for string2Token in string2List:
				string2VectorsTemp = np.add(string2VectorsTemp, model.wv[string2Token])
			#we divide the vectors by the nb of entities so we obtain a mean vector
			string2VectorsTemp = np.divide(string2VectorsTemp, len(string1List))

			#we use the cosinus distance between vectors to get a similarity score
			embeddSimilarity = 1 - spatial.distance.cosine(string1VectorsTemp, string2VectorsTemp)
			
	except KeyError:
		embeddSimilarity = 0.0
	return embeddSimilarity


def tripletsFilterSubjectBased(tripletsList, articleName, filteredInfoList=[], aliasListWords=[], word2VecModel=None, correspondences=[0, 1, 2, 3, 4, 5]):
	'''
	We try to filter the triplets according to the subject
	to try and keep most of the non noisy triplets

	We keep:
	- the exact correspondences between the subject and the article name
	- the partial correspondences between the subject and the article name
	- the alias correspondences between the subject and the article name
	- the Levenshtein similarity correspondences above 0.75 between the subject and the article name
	- the word2vec embeddings similarity correspondences  above 0.75 between the subject and the article name
	- the pronoun subjects
	'''
	pronounsList = [u'it', u'he', u'she', u'they', 'it', 'he', 'she', 'they']
	if word2VecModel == None:
		print('LOADING Word2Vec MODEL')
		word2VecModel = gensim.models.Word2Vec.load("../041word2vecModelEnWiki/en_1000_no_stem/en.model")
		print('MODEL LOADED')

	for triplet in tripletsList:

		subject = triplet[0]
		#exact correspondence
		if 0 in correspondences:
			if subject in [articleName, articleName.replace(u'_', u' '), utils.cleanedArticleName(articleName)]:
				filteredInfoList.append(triplet)
		#partial correspondence
		if 1 in correspondences and triplet not in filteredInfoList:
			if subject in (utils.noTroublesomeName(articleName)).split(u'_'):
				filteredInfoList.append(triplet)
		#alias correspondence
		if 2 in correspondences and triplet not in filteredInfoList:
			if subject in aliasListWords:
				filteredInfoList.append(triplet)
		#levenshtein similarity correspondence
		if 3 in correspondences and triplet not in filteredInfoList:
			cosineSimilarity = Levenshtein.ratio(utils.cleanedArticleName(articleName), subject)
			if cosineSimilarity >= 0.75:
				filteredInfoList.append(triplet)
		#word2vec embedding similarity correspondence
		if 4 in correspondences and triplet not in filteredInfoList and word2VecModel != None:
			embeddSimilarity = getEmbeddingSimilarity(articleName, subject, word2VecModel)
			if embeddSimilarity >= 0.75:
				filteredInfoList.append(triplet)
		#pronouns
		if 5 in correspondences and triplet not in filteredInfoList:
			if subject in pronounsList:
				filteredInfoList.append(triplet)
	return filteredInfoList


def verbCleaner(commonTripletsList, commonFilteredInfoList):
	'''
	If the relation is the verb 'to be' we replace the relation 
	with the subject so the subject becomes the new relation
	I.E. the dog - is - the man's best friend --> the dog : the man's best friend

	If the subject is a part of the named entity and the relation
	has an instance of the verb 'to be', we erase the verb, 
	add the rest of the relation to the object and the subject becomes
	the new relation
	I.E. his puppies - are usually - very cute --> his puppies : usually very cute
	'''
	for triplet in commonTripletsList:
		if triplet != None:
			#the subject becomes the new relation
			if triplet[1] in [u'is', u'are', 'is', 'are']:
				triplet[1] = triplet[0]

			else:
				words = re.compile(ur'[\w]+', re.UNICODE)
				#list variables (3 elements if it's from ollie, 4 if they're from the others Oepn Information Extractors)
				if len(triplet) == 3 or len(triplet) == 4:
					subjectList = words.findall(triplet[0].lower())
				#the fifth element in the triplet is the subject without the coreference replacement(so it might have pronouns)
				elif len(triplet) == 5:
					subjectList = words.findall(triplet[4].lower())
				else:
					raise Exception('the triples do not have an expected format, each triplet must be a list of 3 or 4 elements :', triplet)

				relationList = words.findall(triplet[1].lower())
				possesiveDeterminer = [u'his', u'her', u'its', u'their']		
				verbToBe = [u'are', u'is', u'being', u'was', u'were', u'been', u'be', u'being']
				#if the subject is a part of the named entity and the relation (presence of possesive determiner)
				subjectElementsInCommon = list(set(subjectList).intersection(possesiveDeterminer))
				if len(subjectElementsInCommon) != 0:
					#we look for the elements in common in the relation and the 'to be' verb conjugation
					relationElementsInCommon = list(set(relationList).intersection(verbToBe))
					#we erase the verb, add the rest of the relation to the object and the subject becomes the new relation
					if len(relationElementsInCommon) != 0:
						#we clean the relation list of the 'to be' verb
						for relationElement in relationElementsInCommon:
							relationList.remove(relationElement)
						#we clean the relation list of the auxiliary of the verb
						for auxiliary in [u'have', u'has', u'had', u'will', u'would']:
							if auxiliary in relationList:
								relationList.remove(auxiliary)
						relationRemainder = u' '.join(relationList)
						#add the rest of the relation to the object
						triplet[2] = u'%s %s' %(relationRemainder, triplet[2])
						#the subject becomes the new relation
						triplet[1] = triplet[0]
			
			commonFilteredInfoList.append(triplet)
	return commonFilteredInfoList


def rearrangementOfDicts(tripletDict):
	'''
	reanranges the dict to obtain a format similar to the final output 
	but without filtering nor ordering
	'''
	modifiedOpenie4OrOllieOrClausieSentenceDict = {}
	modifiedOpenie4OrOllieOrClausieTripletDict = {}
	modifiedOpenie4OrOllieOrClausieTupleDict = {}
	nb = 0

	for keyString in tripletDict:
		tripletList = tripletDict[keyString]
		if len(tripletList) == 3:
			modifiedOpenie4OrOllieOrClausieTripletDict[u'%s.%s' %(str(nb).zfill(9), tripletList[0])] = u' : '.join(tripletList[1:3])
		elif len(tripletList) >= 4 :
			#triplet
			modifiedOpenie4OrOllieOrClausieTripletDict[u'%s.%s' %(str(nb).zfill(9), tripletList[0])] = u' : '.join(tripletList[1:3])
			#sentence: we use the whole sentence as the key because there is no other information to show
			modifiedOpenie4OrOllieOrClausieSentenceDict[u'%s.%s' %(str(nb).zfill(9), tripletList[3])] = ''

		##################################################3
		#WE DO NOT CLEAN YET SEE COMMENT IN VERBCLEANER
		#same as the verb cleaner function
		###if tripletList[1] in [u'is', u'are', 'is', 'are']:
		###	tripletList[1] = tripletList[0]

		#tuple
		modifiedOpenie4OrOllieOrClausieTupleDict[u'%s.%s' %(str(nb).zfill(9), tripletList[1])] = tripletList[2]
		nb += 1
	return modifiedOpenie4OrOllieOrClausieSentenceDict, modifiedOpenie4OrOllieOrClausieTripletDict, modifiedOpenie4OrOllieOrClausieTupleDict


def listOfDictsAndcolumnNamesMaker(sentenceDict, tripletDict, dupleDict, nameOfBinaryExtractor=u'Unkknown',listOfDicts=[], columnNames=[]):
	'''
	Fills the variables listOfDicts and	columnNames of 2 or 3 columns according to the data available
	'''
	if len(sentenceDict) == 0:
		#we order the keys
		tripletDict = collections.OrderedDict(sorted(tripletDict.items()))
		dupleDict = collections.OrderedDict(sorted(dupleDict.items()))
		#we append to the valiable lists
		listOfDicts.append(tripletDict)
		listOfDicts.append(dupleDict)
		#names of columns (for pandas file)
		columnNames.append(u'%s TRIPLE' %(nameOfBinaryExtractor))
		columnNames.append(u'%s DUPLE' %(nameOfBinaryExtractor))
	else:
		#we order the keys
		sentenceDict = collections.OrderedDict(sorted(sentenceDict.items()))
		tripletDict = collections.OrderedDict(sorted(tripletDict.items()))
		dupleDict = collections.OrderedDict(sorted(dupleDict.items()))
		#we append to the valiable lists
		listOfDicts.append(sentenceDict)
		listOfDicts.append(tripletDict)
		listOfDicts.append(dupleDict)
		#names of columns (for pandas file)
		columnNames.append(u'%s SENTENCE' %(nameOfBinaryExtractor))
		columnNames.append(u'%s TRIPLE' %(nameOfBinaryExtractor))
		columnNames.append(u'%s DUPLE' %(nameOfBinaryExtractor))
	return listOfDicts, columnNames



def toolSeparatedDump(openie4OutputDict, ollieOutputDict, clausieOutputDict, articleName, directoryPath, originalNamedEntity, overwrite):
	'''
	We dump each article data in a 3 files dividing
	by subj-rel-obj tool (openie4, ollie, clausie)
	'''
	articleName = utils.toUtf8(articleName)
	###we rearrange the openie4 and ollie and clausie output dicts
	listOfDicts = []
	columnNames = []
	#name of the file
	if originalNamedEntity != None:
		nameOfFile = u'%s.%s' %(originalNamedEntity, articleName)
	else:
		nameOfFile = u'%s' %(articleName)

	#openie4
	if openie4OutputDict != None:
		modifiedOpenie4SentenceDict, modifiedOpenie4TripletDict, modifiedOpenie4DupleDict = rearrangementOfDicts(openie4OutputDict)
		#preparing variables for tsv file
		listOfDicts, columnNames = listOfDictsAndcolumnNamesMaker(modifiedOpenie4SentenceDict, modifiedOpenie4TripletDict, modifiedOpenie4DupleDict, u'Openie4', listOfDicts, columnNames)

		#if we don't want to overwrite the files, we look and see if the file already exists before launching
		if overwrite == False:
			fileExists = utils.theFileExists(directoryPath, nameOfFile, u'openie4')
		else:
			fileExists = False
		#if the file doesn't already exists or if we don't care if we overwrite it
		if fileExists == False:
			#DELETING THE FILES (if they already exist)
			utils.deleteTheFile(directoryPath, nameOfFile, u'openie4')
			utils.transformsDictsInTsv(list(listOfDicts), list(columnNames), nameOfFile, directoryPath, u'openie4')
		else:
			pass

	listOfDicts = []
	columnNames = []
	#ollie
	if ollieOutputDict != None:
		modifiedOllieSentenceDict, modifiedOllieTripletDict, modifiedOllieDupleDict = rearrangementOfDicts(ollieOutputDict)
		#preparing variables for tsv file
		listOfDicts, columnNames = listOfDictsAndcolumnNamesMaker(modifiedOllieSentenceDict, modifiedOllieTripletDict, modifiedOllieDupleDict, u'Ollie', listOfDicts, columnNames)


		#if we don't want to overwrite the files, we look and see if the file already exists before launching
		if overwrite == False:
			fileExists = utils.theFileExists(directoryPath, nameOfFile, u'ollie')
		else:
			fileExists = False
		#if the file doesn't already exists or if we don't care if we overwrite it
		if fileExists == False:
			#DELETING THE FILES (if they already exist)
			utils.deleteTheFile(directoryPath, nameOfFile, u'ollie')
			utils.transformsDictsInTsv(list(listOfDicts), list(columnNames), nameOfFile, directoryPath, u'ollie')
		
	listOfDicts = []
	columnNames = []
	#clausie
	if clausieOutputDict != None:
		modifiedClausieSentenceDict, modifiedClausieTripletDict, modifiedClausieDupleDict = rearrangementOfDicts(clausieOutputDict)
		#preparing variables for tsv file
		listOfDicts, columnNames = listOfDictsAndcolumnNamesMaker(modifiedClausieSentenceDict, modifiedClausieTripletDict, modifiedClausieDupleDict, u'Clausie', listOfDicts, columnNames)
	
		#if we don't want to overwrite the files, we look and see if the file already exists before launching
		if overwrite == False:
			fileExists = utils.theFileExists(directoryPath, nameOfFile, u'clausie')
		else:
			fileExists = False
		#if the file doesn't already exists or if we don't care if we overwrite it
		if fileExists == False:
			#DELETING THE FILES (if they already exist)
			utils.deleteTheFile(directoryPath, nameOfFile, u'clausie')
			utils.transformsDictsInTsv(list(listOfDicts), list(columnNames), nameOfFile, directoryPath, u'clausie')
	return None


def allTripletsSaver(openie4OutputDict, ollieOutputDict, clausieOutputDict, articleName, nameOfFolderWhereDidWeGetThoseStrings, joinedOutputs=True, originalNamedEntity=None, overwrite=True):
	'''
	We dump the information necessary to make a manual gold standard
	wich, as it will be made by few taggers (one) does not really 
	correspond to the ground truth. Wich is why we says 'pseudo'.

	joinedOutputs can be:
	True -> all data is dumped in a single file
	False -> the data is dumped in 3 files: openie4, ollie and clausie
	None -> the data is separated in openie4, ollie and clausie AND 
			separated by subject of the triple, then dumped in numerous files
	'''
	###we define the variables to use
	directoryPath = '../046OieOutputsRandomEntities/%s/' %(nameOfFolderWhereDidWeGetThoseStrings)
	
	###we save the openie4, ollie and clausie output dicts to be able compile the data
	if not os.path.exists(directoryPath):
		os.makedirs(directoryPath)

	#dumping the openie4, ollie and clausie output separated
	###if joinedOutputs == False:
	toolSeparatedDump(openie4OutputDict, ollieOutputDict, clausieOutputDict, articleName, directoryPath, originalNamedEntity, overwrite)

	################################################################################
	##IF we want to revive these functions go see 059
	#dumping the output separated by subject
	###elif joinedOutputs == None:
	###	subjectSeparatedDumpGoldStandard(openie4OutputDict, ollieOutputDict, clausieOutputDict, articleName, directoryPath, originalNamedEntity, overwrite)
	#dumping the openie4, ollie and clausie output joined
	###else:
	###	joinedDumpGoldStandard(openie4OutputDict, ollieOutputDict, clausieOutputDict, articleName, directoryPath, originalNamedEntity, overwrite)
	return None


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