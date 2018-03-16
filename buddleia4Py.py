#!/usr/bin/python
#-*- coding:utf-8 -*-


#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-IMPORTATIONS-------------------


import swagger_client
from swagger_client.rest import ApiException


#--------------END-IMPORTATIONS-------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------


#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-FONCTIONS-------------------


def toUtf8(stringOrUnicode): #A TESTER###################################
	'''
	Returns the argument in utf-8 encoding
	Unescape html entities???????
	'''
	typeArg = type(stringOrUnicode)
	if typeArg is unicode:
		return stringOrUnicode.encode('utf8').decode('utf8')
	elif typeArg is str:
		return stringOrUnicode.decode('utf8')


def charAnnotClean(string):
	'''
	Clears a string from any special annotation thet might cause an error:
	- '&gt;' instead of '>'
	- '&lt;'<'
	'''
	string = string.replace(u'>', u'&gt;')
	string = string.replace(u'<', u'&lt;')
	return string


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


def buddleiaWrapper(sentence):
	'''
	We use gottif@iro.umontreal.ca's platform to access the output from different
	OIEs and we return a dict for every OIE we need
	'''
	reverbDict={}
	ollieDict={}
	clausieDict={}
	stanfordDict={}
	openie4Dict={}
	propsDict={}

	#we replace troublesome characters with a special name, we will change it back later
	sentence = charAnnotClean(sentence)
	#we launch the api
	api_instance = swagger_client.DefaultApi()
	src_text = sentence # str | The source text
	extractors = ['reverb', 'ollie', 'clausie', 'stanford', 'openie', 'props'] # list[str] | The extractors used to extract triples.

	try:
		apiResponse = api_instance.oie_extract_triples_get(src_text, extractors)

		for dictApi in apiResponse:
			arg1 = charAnnotDirty(dictApi.arg1)
			rel = charAnnotDirty(dictApi.rel)		
			arg2 = charAnnotDirty(dictApi.arg2)
			score = dictApi.score
			sentence = charAnnotDirty(sentence)

			#we catch the reverb content 
			if dictApi.extractor == 'reverb':
				reverbDict[u'_'.join([toUtf8(arg1), rel, toUtf8(arg2)])] = [arg1, rel, arg2, sentence, score]
			#we catch the ollie content 
			elif dictApi.extractor == 'ollie':
				ollieDict[u'_'.join([toUtf8(arg1), rel, toUtf8(arg2)])] = [arg1, rel, arg2, sentence, score]
			#we catch the clausie content except if there was a timeout
			elif dictApi.extractor == 'clausie' and dictApi.rel != u'timeout':
				clausieDict[u'_'.join([toUtf8(arg1), rel, toUtf8(arg2)])] = [arg1, rel, arg2, sentence, score]
			#we catch the stanford content
			elif dictApi.extractor == 'stanford':
				stanfordDict[u'_'.join([toUtf8(arg1), rel, toUtf8(arg2)])] = [arg1, rel, arg2, sentence, score]
			#we catch the openie-4 content
			elif dictApi.extractor == 'openie':
				openie4Dict[u'_'.join([toUtf8(arg1), rel, toUtf8(arg2)])] = [arg1, rel, arg2, sentence, score]
			#we catch the props content
			elif dictApi.extractor == 'props':
				propsDict[u'_'.join([toUtf8(arg1), rel, toUtf8(arg2)])] = [arg1, rel, arg2, sentence, score]
	#if there is a problem with the server
	except ApiException as e:
		raise Exception("Exception when calling DefaultApi -> oie_extract_triples_get: {0}\n".format(e))
	return reverbDict, ollieDict, clausieDict, stanfordDict, openie4Dict, propsDict


#--------------END-FONCTIONS-------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------


#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------START-EXAMPLE-------------------




listOfSentences = [u"Chilly Gonzales (born Jason Charles Beck; 20 March 1972) is a Canadian musician who resided in Paris, France for several years, and now lives in Cologne, Germany."]

for sentence in listOfSentences:
	#we call the function
	reverbDict, ollieDict, clausieDict, stanfordDict, openie4Dict, propsDict = buddleiaWrapper(sentence)
	
	#inside the dict
	if openie4Dict:
		for tripleKey, content in openie4Dict.items():
			arg1 = content[0]
			rel = content[1]
			arg2 = content[2]
			sentence = content[3]
			score = content[4]		
			print(content)	




#--------------END-EXAMPLE-------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------

