#!/usr/bin/python
#-*- coding:utf-8 -*-


#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-IMPORTATIONS-------------------
import os, codecs, re, urlparse, random
import collections, pickle, Levenshtein, nltk
import pandas as pd


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


def urlEncodeNonAscii(b):
	'''
	Found in http://stackoverflow.com/questions/4389572/how-to-fetch-a-non-ascii-url-with-python-urlopen
	merit: bobince: bobince(at)gmail[dot]com
	'''
	return re.sub('[\x80-\xFF]', lambda c: '%%%02x' % ord(c.group(0)), b)


def iriToUri(iri):
	'''
	Found in http://stackoverflow.com/questions/4389572/how-to-fetch-a-non-ascii-url-with-python-urlopen
	merit: bobince: bobince(at)gmail[dot]com
	'''
	parts= urlparse.urlparse(iri)
	return urlparse.urlunparse(
		part.encode('idna') if parti==1 else urlEncodeNonAscii(part.encode('utf-8'))
		for parti, part in enumerate(parts)
		)


def toUtf8(stringOrUnicode):
	'''
	Returns the argument in utf-8 encoding
	Unescape html entities???????
	'''
	typeArg = type(stringOrUnicode)
	if typeArg is unicode:
		return stringOrUnicode.encode('utf8').decode('utf8')
	elif typeArg is str:
		return stringOrUnicode.decode('utf8')


def cleanedArticleName(articleName):
	'''
	Transforms an article name in a simple minimalistic
	by taking away all special characters and crazy spaces
	'''
	ponctuation = re.compile(ur"(\s| |_|-|'|\.|,|:|;|\(|\)|\[|\]|&|\?|!|\n|\t)")
	articleName = ponctuation.sub(u' ', articleName)

	while u'  ' in articleName:
		articleName = articleName.replace(u'  ', u' ')

	if articleName[0] == u' ':
		articleName = articleName[1:]
	if articleName[-1] == u' ':
		articleName = articleName[:-1]
	return toUtf8(articleName)


def sentenceSplitter(stringText):
	'''
	Takes a whole text as an argument and splits affirmative, interrogative 
	and exclamative sentences and includes the punctuation and the end of the 
	sentence. If there is a new line or a tab char, it's replaced by a dot.
	Does not take into account commas and semi-colums.
	'''
	sentencesList=[]
	#we clean the string from all non-breaking spaces (a0), replacing them with regular spaces
	stringText = stringText.replace(u' ', u' ')

	ponctuationAffirm = re.compile(ur"((?<![A-Z])(\.)[ \n\s\t\r])|[ \n\t\r]+")
	affirmativeList = ponctuationAffirm.split(stringText)

	#we split the affirmative sentences
	for affirmative in affirmativeList:
		if affirmative != None and affirmative not in [u'.', u'. ', u' .', u'.\n', u':', u' :', u': ', u':\n', u''] :
			if affirmative[-1] != u'.' and affirmative[-1] != u':':
				affirmative = u'%s.' %(affirmative)
			#we split the interrogative sentences
			interrogativeList = affirmative.split(u'?')
			for interrogative in interrogativeList:
				if len(interrogative) > 5 and interrogative[-1] != u'.':
					interrogative = u'%s?' %(interrogative)
				exclamativeList = interrogative.split(u'!')

				#we split the exclamative sentences
				for exclamative in exclamativeList:
					if len(exclamative) > 5 and exclamative[-1] != u'.' and exclamative[-1] != u'?':
						exclamative = u'%s!' %(exclamative)

					#we take away the space in the first index if there is one
					if len(exclamative) > 5 and exclamative[0] == u' ':
						exclamative = exclamative[1::]

					#we take away most common html code that migh have passed
					noTag = True
					for tag in [u'<img', u'</img', u'<a', u'</a', u'<p', u'</p', u'<div>', u'</div', u'<form', u'</form', u'<button', u'</button', u'<table', u'</table', u'<li', u'</li', u'<th', u'</th', u'<tr', u'</tr', u'<ul', u'</ul', u'<ol', u'</ol',u'<dl', u'</dl', u'<h1', u'</h1', u'<h2', u'</h2', u'<h3', u'</h3', u'<h4', u'</h4', u'<h5', u'</h5', u'<h6', u'</h6', u'<col', u'</col', u'<code', u'</code', u'<script', u'</script']:
						if tag in exclamative:
							noTag = False
					if noTag == True:

						#we look for parenthesis in the sentence
						if u'(' not in exclamative and len(exclamative) > 5:
							sentencesList.append(exclamative)
						else:
							parenthesizedElementsList = re.findall(ur'\((.+?)\)', exclamative)
							#if there are parenthesized elements
							if  len(parenthesizedElementsList) > 5:
								for pElement in parenthesizedElementsList:
									#we tokenize and tag the pos of each token
									tokens = nltk.word_tokenize(pElement)
									posTagsList = nltk.pos_tag(tokens)
									#we look in each token if there is no verb
									noVerb = True
									for posTag in posTagsList:
										#if there is a verb
										if u'VB' in posTag[1]:
											noVerb = False
									#if there was a verb inside the parenthesis, we asume it's a complete sentence,
									#since the OIEs can just suppress the parenthesis or ommit it completely, we place 
									#the sentence in parenthesis after the current sentence
									if noVerb != True and len(pElement) > 5:
										#for each element between parenthesis we add them to the sentences list and then 
										#we supress it from the original sentence
										sentencesList.append(pElement)
										exclamative = exclamative.replace(u'(%s)' %(pElement), u'')
									#if the parentesized sentence has no verb, we replace the parenthesis with comas
									else:
										exclamative = exclamative.replace(u'(%s).' %(pElement), u', %s.' %(pElement))
										exclamative = exclamative.replace(u'(%s)' %(pElement), u', %s, ' %(pElement))
								#we append the exclamative sentence depurated of its parenthesized sentences (or as is)
								if len(exclamative) > 5:
									sentencesList.append(exclamative)

							#in case there was an opened parenthesis but not a closed one
							else:
								if len(exclamative) > 5:
									sentencesList.append(exclamative)
	return sentencesList


def cleanListOfList(listOfList):
	'''
	Cleans a list of lists from the None elements and any doppelganger-list it might contain.
	It only supresses EXACT double list-elements, not similar ones.
	'''
	dictOfDejaVus = {u's': [], u'r':[], u'o':[]}
	cleanedListOfList= []

	for listElement in listOfList:
		if listElement != None:
			subj = listElement[0]
			rel = listElement[1]
			obj = listElement[2]
			#we pass if the subject, relation and object are identical
			if subj in dictOfDejaVus[u's'] and rel in dictOfDejaVus[u'r'] and obj in dictOfDejaVus[u'o']:
				pass
			#we also pass if the relation and object are identical since those are the informations we will ultimately keep
			#this code line is unnecessarily iterative with the precedent code line ('if') but it'll be useful if we want to change it later
			elif rel in dictOfDejaVus[u'r'] and obj in dictOfDejaVus[u'o']:
				pass
			#if there are no doubles
			else:
				cleanedListOfList.append(listElement)
				dictOfDejaVus[u's'].append(subj)
				dictOfDejaVus[u'r'].append(rel)
				dictOfDejaVus[u'o'].append(obj)
	return cleanedListOfList


def stringCleaner(string):
	'''
	Cleans all wikipedia-like reference from string
	'''
	#we remove all wikipedia-like reference
	cleanedString = re.sub(ur'\[[\d]+\]|\[.*needed\]|\[not verified.*\]|\[note.*\]|\(.*listen\)', u'', string)
	return cleanedString


def randomNbGenerator(lengthOfTheNb=5, numberOfNbrs=1):
	"""
	generates a list of N non repeated random numbers
	"""
	listOfNbrs = []
	maxNumber = int('9'*lengthOfTheNb)
	
	if numberOfNbrs == 0 or type(numberOfNbrs) is not int:
		raise Exception('unexpected argument in function, please use int numbers and no zeros')

	while len(listOfNbrs) != numberOfNbrs:
		randomNb = unicode(random.randint(0, maxNumber)).zfill(lengthOfTheNb)
		if randomNb not in listOfNbrs:
			listOfNbrs.append(randomNb)
	return listOfNbrs


def getRandomPseudoNamedEntities():
	'''
	Returns a list of random named entities taken from 
	a dictionary of wikidata-wikipedia correspondence
	'''
	listOfNamedEntities = []

	dictWikidata2Wikipedia = pickle.load(open("../008wikidataFreebaseCodeIdDictMaker/009dictWikidata2Wikipedia.p", "rb"))
	
	#make the list of named entities by extracting making a random list of
	#numbers and making them correspond to wikidata code ids and make them
	#correspond to wikipedia article names
	listOfNbrs = randomNbGenerator(lengthOfTheNb=7, numberOfNbrs=500)
	
	for nb in listOfNbrs:
		
		wikidCodeId = u'Q%s' %(nb)
		#if there is an entry in the dict
		if wikidCodeId in dictWikidata2Wikipedia:
			#if they are not yet in the list of named entities
			namedEntity = (dictWikidata2Wikipedia[wikidCodeId]).replace(u'_', u' ')
			if namedEntity not in listOfNamedEntities and u'Category:' not in namedEntity and u'List' not in namedEntity and namedEntity != None:
				listOfNamedEntities.append(namedEntity)
				#stop at 100 named entities
				if len(listOfNamedEntities) == 100:
					break
	return listOfNamedEntities


def transformsDictsInTsv(listOfTheDicts, nameOfColumns, namedEntity, path2Output, fileExtension=u'tsv'):
	'''
	Dumps a list of dicts in a tsv human-readeable file
	'''
	#we transform the dicts into lists so each key and corresponding
	#value can be enclosed in one case of the dataframe
	if len(listOfTheDicts) != 0:
		for indexDict in range(len(listOfTheDicts)):
			dictionary = listOfTheDicts[indexDict]
			if dictionary == None:
				listOfADict = [None]
			else:
				#we order the dictionnary
				listOfADict = []
				orderedDictionnary = collections.OrderedDict(sorted(dictionary.items()))
				for key in orderedDictionnary:
					keyList = key.split('.')
					#we discard the first element (the numbers)`
					nblessKey = '.'.join(keyList[1:])
					case = '%s: %s' %(nblessKey, orderedDictionnary[key]) 
					listOfADict.append(case)

			#we use the first dict to make the dataframe
			if indexDict == 0:
				dataFrame = pd.DataFrame({nameOfColumns[indexDict] : listOfADict})
			#we use the others dicts to add a column to the dataframe
			else:
				column = pd.Series(listOfADict, name=nameOfColumns[indexDict])
				dataFrame = pd.concat([dataFrame, column], ignore_index=True, axis=1)	
		#preparing to dump into file
		for char in [u' ', u'_', u'/', u'\\', u':', u'…', u'。', u';', u',', u'.', u'>', u'<', u'?', u'!', u'*', u'+', u'(', u')', u'[', u']', u'{', u'}', u'"', u"'", u'=']:
			namedEntity = namedEntity.replace(char, u'_')
		#we change the iri code if there is one
		if u'%' in namedEntity or '%' in namedEntity:
			namedEntity = iriToUri(namedEntity)

		#we look in the specified path to be sure there isn't already a file with the same name as the current one
		pathContent = os.listdir(path2Output)

		#the listdir output is a string, so we transform it to unicode
		for indexFile in range(len(pathContent)):
			fileName = pathContent[indexFile]
			pathContent[indexFile] = toUtf8(fileName)

		fileNb = 0
		newNamedEntity = u'%s_%s' %(namedEntity, unicode(fileNb))
		
		while (u'%s.%s' %(newNamedEntity, fileExtension)) in pathContent:
			fileNb += 1
			newNamedEntity = u'%s_%s' %(namedEntity, unicode(fileNb))

		#dump into file	
		dataFrame.to_csv(u'%s%s.%s' %(path2Output, newNamedEntity, fileExtension), sep='\t', header=nameOfColumns, encoding='utf-8')
		#return the data frame
		return dataFrame


def noTroublesomeName(string):
	'''
	Transforms the name into a non-troublesome name
	'''
	for char in [u' ', u' ', u'_', u'/', u'\\', u':', u';', u',', u'.', u'>', u'<', u'?', u'!', u'*', u'+', u'(', u')', u'[', u']', u'{', u'}', u'"', u"'", u'=']:
		string = string.replace(char, u'_')
	#we change the iri code if there is one
	if u'%' in string:
		string = iriToUri(string)
	return string
	

def noTroublesomeNameAndNoDoubleUnderscore(string):
	'''
	Transforms the name into a non-troublesome name
	'''
	for char in [u' ', u' ', u'_', u'/', u'\\', u':', u';', u',', u'.', u'>', u'<', u'?', u'!', u'*', u'+', u'(', u')', u'[', u']', u'{', u'}', u'"', u"'", u'=']:
		string = string.replace(char, u'_')

	#we change the iri code if there is one
	if u'%' in string:
		string = iriToUri(string)
		#if there is still a '%' char we replace it
		if u'%' in string:
			string = string.replace(u'%', u'_') 

	if len(string) > 0:
		#we replace all double underscore by a single underscore
		if u'__' in string:
			string.replace(u'__', u'_')
		#if there is an underscore at the begining and at the end of the name, we delete it
		if string[0] == u'_':
			string = string[1:]
		if len(string) > 0 and string[-1] == u'_':
			string = string[:-1]
	return string


def transformsListInTsv(dataListOrListOfLists, nameOfColumnOrColumnList, nameOfFile, path2Output, fileExtension=u'tsv'):
	'''
	Dumps a list or a list of lists in a tsv human-readeable file
	'''
	if len(dataListOrListOfLists) != 0:
		#if it's a single list not a list of lists
		if type(dataListOrListOfLists[0]) is not list:
			#we make the dataframe
			dataFrame = pd.DataFrame({nameOfColumnOrColumnList : dataListOrListOfLists})
		#if it's a list of lists
		else:
			#if what the dataListOrListOfLists variable is a list of lists
			if len(dataListOrListOfLists) == 1:
				#if the nameOfColumnOrColumnList variables has the same structure as the dataListOrListOfLists: a list on only one list
				if len(nameOfColumnOrColumnList) == 1 and nameOfColumnOrColumnList[0] is list:
					#we only take the first name of columns
					nameOfColumnOrColumnList = nameOfColumnOrColumnList[0]

				#we make the dataframe
				dataFrame = pd.DataFrame({nameOfColumnOrColumnList : dataListOrListOfLists[0]})
			#we use the others lists to add a column to the dataframe
			else:
				#the dataListOrListOfLists and nameOfColumnOrColumnList lists must have the same length, one column name per data column
				if len(dataListOrListOfLists) == len(nameOfColumnOrColumnList):
					#we add each list in a dict with the column name as a key so we can concatenate it to the dataframe
					for index in range(len(dataListOrListOfLists)):
						columnData = dataListOrListOfLists[index]
						columnName = nameOfColumnOrColumnList[index]
						#we use the first column to make the dataframe
						if index == 0:
							dataFrame = pd.DataFrame({columnName : columnData})
						#we concatenate the information
						else:
							column = pd.Series(columnData, name=columnName)
							dataFrame = pd.concat([dataFrame, column], ignore_index=True, axis=1)
				#otherwise, we raise an exception
				else:
					raise IndexError('the data list of lists and the column names list must have the same length: one column name per data column.\n data length: ', len(dataListOrListOfLists), '\t\tcolumn length: ', len(nameOfColumnOrColumnList))

		nameOfFile = noTroublesomeName(nameOfFile)

		#we look in the specified path to be sure there isn't already a file with the same name as the current one
		pathContent = os.listdir(path2Output)
		fileNb = 0
		newNameOfFile = u'%s_%s' %(nameOfFile, unicode(fileNb))
		while (u'%s.%s' %(newNameOfFile, fileExtension)) in pathContent:
			fileNb += 1
			newNameOfFile = u'%s_%s' %(nameOfFile, unicode(fileNb))

		#dump into file	
		dataFrame.to_csv(u'%s%s.%s' %(path2Output, newNameOfFile, fileExtension), sep='\t', header=nameOfColumnOrColumnList, encoding='utf-8')
		#return the data frame
		return dataFrame


def emptyTheFolder(directoryPath, fileExtensionOrListOfExtensions=u'*'):
	'''
	Removes all files corresponding to the specified file(s) extension(s).
	If the fil estension is '*' the function will remove all files except
	the system files (ie: '.p', '.java', '.txt') and folders
	'''
	#we first delete the content of the folder to make place to the new content
	try:
		if type(fileExtensionOrListOfExtensions) is list:
			filelist = []
			for extension in fileExtensionOrListOfExtensions:
				fileExtensionList = [file for file in os.listdir(directoryPath) if file.endswith(".%s" %(fileExtensionOrListOfExtensions)) ]
				filelist = filelist + fileExtensionList
		#the '*' implies we want all files deleted
		elif fileExtensionOrListOfExtensions == u'*':
			filelist = [file for file in os.listdir(directoryPath)]
		else:
			filelist = [file for file in os.listdir(directoryPath) if file.endswith(u".%s" %(fileExtensionOrListOfExtensions)) ]
		#we delete the files
		for file in filelist:
			os.remove(directoryPath + file)
	except OSError:
		pass


def deleteTheFile(directoryPath, nameOfFile, fileExtension):
	'''
	Removes all files corresponding to the given name and the specified file(s) extension(s).
	'''	
	#if the path is correctly written at the end
	if directoryPath[-1] !=u'/':
		directoryPath = u'%s/' %(directoryPath)

	#preparing to dump into file
	for char in [u' ', u'_', u'/', u'\\', u':', u'…', u'。', u';', u',', u'.', u'>', u'<', u'?', u'!', u'*', u'+', u'(', u')', u'[', u']', u'{', u'}', u'"', u"'", u'=']:
		nameOfFile = nameOfFile.replace(char, u'_')
	#we change the iri code if there is one
	if u'%' in nameOfFile or '%' in nameOfFile:
		nameOfFile = iriToUri(nameOfFile)

	#we make a list of all the possible names of the files to be deleted
	fileNamesToBeDeleted = []
	namePlusExt = u'%s.%s' %(nameOfFile, fileExtension)

	fileNamesToBeDeleted.append(namePlusExt)
	fileNamesToBeDeleted.append(noTroublesomeName(namePlusExt))
	for nb in range(10):
		fileNamesToBeDeleted.append(u'%s_%s.%s' %(nameOfFile, unicode(nb), fileExtension))
		fileNamesToBeDeleted.append(u'%s_%s.%s' %(noTroublesomeName(nameOfFile), unicode(nb), fileExtension))

	#we make a list of all extension-like 
	try:
		#we catch all corresponding names
		if type(fileExtension) is unicode:	
			filelist = [toUtf8(file) for file in os.listdir(directoryPath) if file.endswith(".%s" %(fileExtension.encode('utf8'))) ]
		elif type(fileExtension) is str:
			filelist = [toUtf8(file) for file in os.listdir(directoryPath) if file.endswith(".%s" %(fileExtension)) ]
		
	except OSError:
		filelist = []

	#we make a list of the intersection between the 2 lists
	intersection = list(set(fileNamesToBeDeleted) & set(filelist))
	#we delete the files
	for file in intersection:
		os.remove(directoryPath + file)


def theFileExists(directoryPath, nameOfFile, fileExtension=None):
	'''
	Returns false if the file does not exists at the directory
	and returns true if the file exists
	'''
	#if the path is correctly written at the end
	if directoryPath[-1] !=u'/':
		directoryPath = u'%s/' %(directoryPath)
	#all extensions
	if fileExtension == None:
		filelist = os.listdir(directoryPath)
		for file in filelist:
			splittedFileName = file.split('.')
			#if there was more than one '.'
			if len(splittedFileName) > 2:
				splittedFileName = ['.'.join(splittedFileName[:len(splittedFileName)-1])]
			#print(99999999999, toUtf8(splittedFileName[0]), noTroublesomeName(nameOfFile))
			#if the file exists
			for nb in range(10):
				if u'%s_%s' %(nameOfFile, unicode(nb)) == toUtf8(splittedFileName[0]) or u'%s_%s' %(noTroublesomeName(nameOfFile), unicode(nb)) == toUtf8(splittedFileName[0]):
					return True
		#if the file never appeared
		return False
	#exclusive extension
	else:
		return os.path.isfile(u'%s%s.%s' %(directoryPath, nameOfFile, fileExtension)) 


def reformatDates(string):
	'''
	We replace the english standard text way of writing dates
	with the format year-month-day
	'''
	monthsDict = {u'January': u'01', u'February': u'02', u'March': u'03', u'April': u'04', u'May': u'05', u'June': u'06', u'July': u'07', u'August': u'08', u'September': u'09', u'October': u'10', u'November': u'11', u'December': u'12', u'Jan': u'01', u'Feb': u'02', u'Mar': u'03', u'Apr': u'04', u'May': u'05', u'Jun': u'06', u'Jul': u'07', u'Aug': u'08', u'Sep': u'09', u'Oct': u'10', u'Nov': u'11', u'Dec': u'12'}

	#we catch the month
	monthsList = re.findall(ur'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', string)
	for month in monthsList:
		#for each month catched (possibility of multiple months in one fact) we catch the whole date
		datesList = re.findall(ur'%s [\d]?[\d], [\d]*' %(month), string)
		#for each date catched we transform it into an uniform format
		for date in datesList:
			dayAndYearList = date.replace(u'%s ' %(month), '').split(u', ')
			uniformDate = u'%s-%s-%s' %(dayAndYearList[1].zfill(2), monthsDict[month], dayAndYearList[0])
			string = string.replace(date, uniformDate)
	return string


def printOrderedDict(dictionary, noNumbers=True):
	"""`
	Prints the input dictionnaries in an orderly way
	"""
	if dictionary == None:
		print(u'Sorry, the dictionary is empty.')
	else:
		orderedDictionnary = collections.OrderedDict(sorted(dictionary.items()))
		for dictKey in orderedDictionnary:
			#if we don't want to have an output with numbers
			if noNumbers == True:
				keyOut = dictKey.split(u'.')[1]
			else:
				keyOut = dictKey
			try:
				try:
					print(keyOut, toUtf8(orderedDictionnary[dictKey]))
				except UnicodeEncodeError:
					print(keyOut, (orderedDictionnary[dictKey]))
			except AttributeError:
				print(type(orderedDictionnary[dictKey]))
				#raise TypeError('unexpected type of value in dictionnary', keyOut, orderedDictionnary[dictKey])


def dictValueShortener(dictionnary):
	'''
	If one of the values of the dictionnaries is more than 140 characters long, 
	we delete it.
	'''
	shortenedDict = {}

	#we browse the keys of the dict
	for keyAndNbOfDict in dictionnary:
		valueOfDict = dictionnary[keyAndNbOfDict]

		#if the value is longer than an ordinary tweet/text message
		if len(valueOfDict) < 141:
			shortenedDict[keyAndNbOfDict] = valueOfDict
	return shortenedDict


def dictUnifier(listOfDicts):
	'''
	Takes a list of dictionnaries as input and fusions them, 
	making sure there is no repeated or contary	entry.
	It returns a unified dictionnary
	'''
	oneDictToRuleThemAll = {}

	#we browse our dictionnary list
	for dictionnary in listOfDicts:
		#if the dictionary is not empty
		if dictionnary != None:
			#we delete the long values 
			dictionnary = dictValueShortener(dictionnary)
			#we browse the keys of each dict
			for keyAndNbOfDict in dictionnary:
				keyAndNbOfDictList = keyAndNbOfDict.split('.')
				keyOfDict = keyAndNbOfDictList[1]
				nbOfDict = keyAndNbOfDictList[0]
				valueOfDict = dictionnary[keyAndNbOfDict]			

				#if the encoding doesn't allow to compare the dict entries, we pass on that particular key
				########################################################################################
				####A AMELIORER
				try:
					#we search if the key already exists in the one dict
					keyAndNbOfTheOneDict = re.search(r'[\d]*\.%s' %(keyOfDict), '*'.join(oneDictToRuleThemAll.keys()))
					#if the key already exists we compare the values of the 2 dicts
					if keyAndNbOfTheOneDict != None:

						keyAndNbOfTheOneDict = keyAndNbOfTheOneDict.group()				
						try:
							valueOfTheOneDict = oneDictToRuleThemAll[keyAndNbOfTheOneDict]

							#we transform every value and key into unicode if needed:
							valueOfTheOneDict = toUtf8(valueOfTheOneDict)
							valueOfDict = toUtf8(valueOfDict)
							keyAndNbOfTheOneDict = toUtf8(keyAndNbOfTheOneDict)
							keyAndNbOfDict = toUtf8(keyAndNbOfDict)

							#we get the cosine similarity between the 2 values
							cosineSimilarity = Levenshtein.ratio(valueOfTheOneDict, valueOfDict)
							#we look at the key and number of both dicts, if they're extremely similar, then, 
							#the it must be a list of elements (information with the same key name but different value)
							#WE MAY BE LOSIN VERY SIMILAR INFORMATION, i.e.: some very similar aliases
							if cosineSimilarity > 0.5 and Levenshtein.ratio(keyAndNbOfTheOneDict, keyAndNbOfDict) > 0.92:
								oneDictToRuleThemAll[keyAndNbOfDict] = dictionnary[keyAndNbOfDict]
						#if there is a key error, it means that theOneDictTORuleThemAll has already a more 
						#precise segmentation of the information, so we pass on the more general information
						except KeyError:
							pass
					#if the key doesn't already exists we add it to the one dict
					else: 
						oneDictToRuleThemAll[keyAndNbOfDict] = (dictionnary[keyAndNbOfDict])
				#if the encoding doesn't allow to compare the dict entries, we pass on the key
				########################################################################################
				####A AMELIORER
				except UnicodeDecodeError:
					pass
	return oneDictToRuleThemAll


def dumpRawLines(listOfRawLines, filePath, addNewline=True): 
	'''
	Dumps a list of raw lines in a a file 
	so the Benchmark script can analyse the results
	'''
	folderPath = u'/'.join((filePath.split(u'/'))[:-1]+[''])
	if not os.path.exists(folderPath):
		os.makedirs(folderPath)
	#we dump an empty string to make sure the file is empty
	openedFile = codecs.open(filePath, 'w', encoding='utf8')
	openedFile.write('')
	openedFile.close()
	openedFile = codecs.open(filePath, 'a', encoding='utf8')
	#we dump every line of the list
	for line in listOfRawLines:
		if addNewline == True:
			openedFile.write(u'%s\n' %(line))
		else:
			openedFile.write(u'%s' %(line))
	openedFile.close()
	return None


def intersect(a, b, absoluteExact=True):
	'''
	returns the intersection of 2 lists of strings, 
	if the argument 'absoluteExact' is a float btwn 0 and 1,
	it looks for the cosinus similarity between each list element

	if the argument 'absoluteExact' is False we compare without case sensitivity (capital letters)

	if the argument 'absoluteExact' is True, we return the absolute exact

	ATTENTION: if one of the data is from KB and the other is from OIE, 
	the path to the KB data MUST be 'pathToFiles1'!!! 
	'''
	similIntersectList = []

	#if one of the lists of strings is empty, the there is no intersection possible, and we return an empty list
	if a == None or b == None or len(a) == 0 or len(b) == 0:
		return []

	if type(absoluteExact) == float or type(absoluteExact) == int:
		absoluteExact = float(absoluteExact)

		for valA in a:
			for valB in b:
				#we get the cosine similarity between the 2 values
				cosineSimilarity = Levenshtein.ratio(valA.lower(), valB.lower())
				#comparing expected and real similarity
				if cosineSimilarity >= absoluteExact:
					similIntersectList.append(valA)
					#print(valA, valB)
		return list(set(similIntersectList))
	#transform all to lower before
	elif absoluteExact == False:
		for valA in a:
			for valB in b:
				if valA.lower() == valB.lower():
					similIntersectList.append(valA)
		return list(set(similIntersectList))
	#absolute exact is true
	else:
		return list(set(a) & set(b))


def deleteFileContent(pathToFile, openAnAppendFile=False):
	'''
	Deletes a file's content without deleting the file by 
	writing an empty string into it.
	It returns the object corresponding to the file.
	If the openAnAppendFile is not False, it will return the
	object corresponding to an openend and append file
	'''
	openedFile = codecs.open(pathToFile, 'w', encoding='utf8')
	openedFile.write('')
	openedFile.close()
	if openAnAppendFile != False:
		openedFile = codecs.open(pathToFile, 'a', encoding='utf8')
	return openedFile


def readAllLinesFromFile(pathToFile):
	'''
	Returns a list containing all the lines in the file
	'''
	openedFile = codecs.open(pathToFile, 'r', encoding='utf8')
	linesList = openedFile.readlines()
	openedFile.close()

	#if linesList is None we return and empty list
	if linesList == None:
		linesList = []
	return linesList


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