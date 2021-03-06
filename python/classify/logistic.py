import os, sys
import numpy as np
import pandas as pd
from bagofwords import BagOfWords, StandardizingVector
import epistolarymetadata
import pickle
from sklearn.linear_model import LogisticRegression
from sklearn import cross_validation
import SonicScrewdriver as utils

def select_common_features(trainingset, n):
	''' Very simply, selects the top n features in the training set.
	Not a sophisticated feature-selection strategy, but in many
	cases it gets the job done.
	'''
	allwordcounts = dict()

	for avolume in trainingset:
		utils.add_dicts(avolume.rawcounts, allwordcounts)
		# The add_dicts function will add up all the raw counts into
		# a single master dictionary.

	descendingbyfreq = utils.sortkeysbyvalue(allwordcounts, whethertoreverse = True)
	# This returns a list of 2-tuple (frequency, word) pairs.

	if n > len(descendingbyfreq):
		n = len(descendingbyfreq)
		print("We only have " + str(n) + " features.")

	# List comprehension that gets the second element of each tuple, up to
	# a total of n tuples.

	topfeatures = [x[1] for x in descendingbyfreq[0 : n]]

	return topfeatures

def train_a_model(sourcefolder, extension, include_punctuation, maxfeatures, outputfolder):

	if not os.path.exists(outputfolder):
		os.makedirs(outputfolder)

	if not sourcefolder.endswith('/'):
		sourcefolder = sourcefolder + '/'
	if not outputfolder.endswith('/'):
		outputfolder = outputfolder + '/'
	# This just makes things easier.

	# Get a list of files.
	allthefiles = os.listdir(sourcefolder)

	# Now we have a list of file names. But we want volumeIDs, paired with complete
	# paths to the file. We're going to achieve the pairing by zipping two lists,
	# rather than with a dict, because ordering also matters here.

	volumeIDs = list()
	volumepaths = list()

	for filename in allthefiles:

		if filename.endswith(extension):
			volID = filename.replace(extension, "")
			# The volume ID is basically the filename minus its extension.
			# Extensions are likely to be long enough that there is little
			# danger of accidental occurrence inside a filename. E.g.
			# '.fic.tsv'
			path = sourcefolder + filename
			volumeIDs.append(volID)
			volumepaths.append(path)

	# Now we actually read volumes and create a training corpus, which will
	# be a list of bags of words.

	trainingset = list()
	for volID, filepath in zip(volumeIDs, volumepaths):
		volume = BagOfWords(filepath, volID, include_punctuation)
		# That reads the volume from disk.
		trainingset.append(volume)

	# We select the most common words as features.
	featurelist = select_common_features(trainingset, maxfeatures)
	numfeatures = len(featurelist)
	# Note that the number of features we actually got is not necessarily
	# the same as maxfeatures.

	for volume in trainingset:
		volume.selectfeatures(featurelist)
		volume.normalizefrequencies()
		# The volume now contains feature frequencies:
		# raw counts have been divided by the total number of words in the volume.

	standardizer = StandardizingVector(trainingset, featurelist)
	# This object calculates the means and standard deviations of all features
	# across the training set.

	listofvolumefeatures = list()
	for volume in trainingset:
		volume.standardizefrequencies(standardizer)
		# We have now converted frequencies to z scores. This is important for
		# regularized logistic regression -- otherwise the regularization
		# gets distributed unevenly across variables because they're scaled
		# differently.

		listofvolumefeatures.append(volume.features)

	# Now let's make a data frame by concatenating each volume as a separate column,
	# aligned on the features that index rows.

	data = pd.concat(listofvolumefeatures, axis = 1)
	data.columns = volumeIDs

	# Name the columns for volumes. Then transpose the matrix:

	data = data.T

	# So that we have a matrix with features (variables) as columns and instances (volumes)
	# as rows. Would have been easier to make this directly, but I don't know a neat
	# way to do it in pandas.

	classvector = epistolarymetadata.get_genrevector(volumeIDs, "nonepistolary / epistolary")
	# This part is going to be very specific to the model you train, so I've
	# encapsulated it in a separate module. For our purposes, it's just a function
	# that returns a pandas series of zeroes and ones indexed by volumeID.
	# zero = non, one = epistolary.

	logisticmodel = LogisticRegression(C = 1)
	classvector = classvector.astype('int')
	logisticmodel.fit(data, classvector)

	# Let's sort the features by their coefficient in the model, and print.

	coefficients = list(zip(logisticmodel.coef_[0], featurelist))
	coefficients.sort()
	for coefficient, word in coefficients:
		print(word + " :  " + str(coefficient))

	# Pickle and write the model & standardizer. This will allow us to apply the model to
	# new documents of unknown genre.

	modelfile = outputfolder + "logisticmodel.p"
	with open(modelfile, mode = 'wb') as f:
		pickle.dump(logisticmodel, f)
	standardizerfile = outputfolder + "standardizer.p"
	with open(standardizerfile, mode = 'wb') as f:
		pickle.dump(standardizer, f)

	accuracy_tries = cross_validation.cross_val_score(logisticmodel, data, classvector, cv=5)
	print(accuracy_tries)

	# Note that with the full epistolary dataset a straightforward cross-validation is actually
	# a pretty bad measure of accuracy, because we have many multivolume novels and novels
	# by the same author in our training set. The classifier may be learning those
	# incidental associations as much as it's learning the epistolary / non-epistolary boundary.

	# I've reduced this problem a bit by using a subset of the corpus that includes only one
	# volume for each title. But for a really rigorous measure of accuracy we'd want a
	# better cross-validation strategy.

	# Yay, we're done.

if __name__ == "__main__":

	sourcefolder = input("source folder? ")
	extension = '.fic.tsv'
	include_punctuation = False
	maxfeatures = 1000
	outputfolder = input("output folder? ")

	train_a_model(sourcefolder, extension, include_punctuation, maxfeatures, outputfolder)











