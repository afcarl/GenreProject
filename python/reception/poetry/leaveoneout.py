# Reads all volumes meeting a given set of criteria,
# and uses a leave-one-out strategy to distinguish
# reviewed volumes (class 1) from random
# class 0. In cases where an author occurs more
# than once in the dataset, it leaves out all
# volumes by that author whenever making a prediction
# about one of them.

import numpy as np
import pandas as pd
import csv, os, random
from collections import Counter

from sklearn.linear_model import Ridge
from sklearn.linear_model import LogisticRegression

usedate = False

def dirty_pairtree(htid):
    period = htid.find('.')
    prefix = htid[0:period]
    postfix = htid[(period+1): ]
    if '=' in postfix:
        postfix = postfix.replace('+',':')
        postfix = postfix.replace('=','/')
    dirtyname = prefix + "." + postfix
    return dirtyname

def forceint(astring):
    try:
        intval = int(astring)
    except:
        intval = 0

    return intval

def normalizeandexport(featurearray, usedate):
    '''Normalizes an array by centering on means and
    scaling by standard deviations. Also returns the
    means and standard deviations for features, so that
    they can be pickled.
    '''

    numinstances, numfeatures = featurearray.shape
    means = list()
    stdevs = list()
    lastcolumn = numfeatures - 1
    for featureidx in range(numfeatures):

        thiscolumn = featurearray.iloc[ : , featureidx]
        thismean = np.mean(thiscolumn)

        thisstdev = np.std(thiscolumn)

        if (not usedate) or featureidx != lastcolumn:
            # If we're using date we don't normalize the last column.
            means.append(thismean)
            stdevs.append(thisstdev)
            featurearray.iloc[ : , featureidx] = (thiscolumn - thismean) / thisstdev
        else:
            print('FLAG')
            means.append(thismean)
            thisstdev = 0.1
            stdevs.append(thisstdev)
            featurearray.iloc[ : , featureidx] = (thiscolumn - thismean) / thisstdev
            # We set a small stdev for date.

    return featurearray, means, stdevs

def get_metadata(classpath, volumeIDs, excludeif, excludeifnot, excludebelow, excludeabove):
    '''
    As the name would imply, this gets metadata matching a given set of volume
    IDs. It returns a dictionary containing only those volumes that were present
    both in metadata and in the data folder.

    It also accepts four dictionaries containing criteria that will exclude volumes
    from the modeling process.
    '''

    metadict = dict()

    with open(classpath, encoding = 'utf-8') as f:
        reader = csv.DictReader(f, delimiter = '\t')

        anonctr = 0

        for row in reader:
            volid = dirty_pairtree(row['docid'])
            theclass = row['recept'].strip()

            # I've put 'remove' in the reception column for certain
            # things that are anomalous.
            if theclass == 'remove':
                continue

            bail = False
            for key, value in excludeif.items():
                if row[key] == value:
                    bail = True
            for key, value in excludeifnot.items():
                if row[key] != value:
                    bail = True
            for key, value in excludebelow.items():
                if forceint(row[key]) < value:
                    bail = True
                    print(row[key])
            for key, value in excludeabove.items():
                if forceint(row[key]) > value:
                    bail = True

            if bail:
                continue

            birthdate = forceint(row['birth'])

            pubdate = forceint(row['date'])

            gender = row['gender'].rstrip()
            nation = row['nationality'].rstrip()

            #if pubdate >= 1880:
                #continue

            if nation == 'ca':
                nation = 'us'
            elif nation == 'ir':
                nation = 'uk'
            # I hope none of my Canadian or Irish friends notice this.

            notes = row['notes'].lower()
            author = row['author']
            if len(author) < 1:
                author = "anonymous" + str(anonctr)
                anonctr += 1

            title = row['title']
            canon = row['canon']

            # I'm creating two distinct columns to indicate kinds of
            # literary distinction. The reviewed column is based purely
            # on the question of whether this work was in fact in our
            # sample of contemporaneous reviews. The obscure column incorporates
            # information from post-hoc biographies, which trumps
            # the question of reviewing when they conflict.

            if theclass == 'vulgar':
                obscure = 'obscure'
                reviewed = 'not'
            elif theclass == 'elite':
                obscure = 'known'
                reviewed = 'rev'
            elif theclass == 'addcanon':
                obscure = 'known'
                reviewed = 'addedbecausecanon'
            else:
                print(theclass)

            if notes == 'well-known':
                obscure = 'known'
            if notes == 'obscure':
                obscure = 'obscure'

            if canon == 'y':
                if theclass == 'addcanon':
                    actually = 'Norton, added'
                else:
                    actually = 'Norton, in-set'
            elif reviewed == 'rev':
                actually = 'reviewed'
            else:
                actually = 'random'

            metadict[volid] = (reviewed, obscure, pubdate, birthdate, gender, nation, author, title, actually)

    # These come in as dirty pairtree; we need to make them clean.

    cleanmetadict = dict()
    allidsinmeta = set([x for x in metadict.keys()])
    allidsindir = set([dirty_pairtree(x) for x in volumeIDs])
    missinginmeta = len(allidsindir - allidsinmeta)
    missingindir = len(allidsinmeta - allidsindir)
    print("We have " + str(missinginmeta) + " volumes in missing in metadata, and")
    print(str(missingindir) + " volumes missing in the directory.")

    for anid in volumeIDs:
        dirtyid = dirty_pairtree(anid)
        if dirtyid in metadict:
            cleanmetadict[anid] = metadict[dirtyid]

    return cleanmetadict

def get_features(wordcounts, wordlist):
    numwords = len(wordlist)
    wordvec = np.zeros(numwords)
    for idx, word in enumerate(wordlist):
        if word in wordcounts:
            wordvec[idx] = wordcounts[word]

    return wordvec

def get_features_with_date(wordcounts, wordlist, date, totalcount):
    numwords = len(wordlist)
    wordvec = np.zeros(numwords + 1)
    for idx, word in enumerate(wordlist):
        if word in wordcounts:
            wordvec[idx] = wordcounts[word]

    wordvec = wordvec / (totalcount + 0.0001)
    wordvec[numwords] = date
    return wordvec

def sliceframe(dataframe, yvals, excludedrows, testrow):
    numrows = len(dataframe)
    newyvals = list(yvals)
    for i in excludedrows:
        del newyvals[i]
        # NB: This only works if we assume that excluded rows
        # has already been sorted in descending order !!!!!!!

    trainingset = dataframe.drop(dataframe.index[excludedrows])

    newyvals = np.array(newyvals)
    testset = dataframe.iloc[testrow]

    return trainingset, newyvals, testset

## MAIN code starts here.

excludeif = dict()
excludeifnot = dict()
excludeabove = dict()
excludebelow = dict()

excludebelow['date'] = 1700

sourcefolder = '/Users/tunder/Dropbox/GenreProject/python/reception/poetry/texts/'
extension = '.poe.tsv'
classpath = '/Users/tunder/Dropbox/GenreProject/python/reception/poetry/amplifiedmeta.tsv'
outputpath = '/Users/tunder/Dropbox/GenreProject/python/reception/poetry/linearpredictions.csv'

# sourcefolder = '/Users/tunder/Dropbox/GenreProject/python/reception/fiction/texts/'
# extension = '.fic.tsv'
# classpath = '/Users/tunder/Dropbox/GenreProject/python/reception/fiction/amplifiedficmeta.tsv'
# outputpath = '/Users/tunder/Dropbox/GenreProject/python/reception/fiction/logisticpredictions.csv'

if not sourcefolder.endswith('/'):
    sourcefolder = sourcefolder + '/'

# This just makes things easier.

# Get a list of files.
allthefiles = os.listdir(sourcefolder)
# random.shuffle(allthefiles)

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

# Get the class and date vectors, indexed by volume ID

metadict = get_metadata(classpath, volumeIDs, excludeif, excludeifnot, excludebelow, excludeabove)

IDspresent = set([x for x in metadict.keys()])

# make a vocabulary list and a volsize dict
wordcounts = Counter()

volspresent = list()
orderedIDs = list()

for volid, volpath in zip(volumeIDs, volumepaths):
    if volid not in IDspresent:
        continue
    else:
        volspresent.append((volid, volpath))
        orderedIDs.append(volid)

    with open(volpath, encoding = 'utf-8') as f:
        for line in f:
            fields = line.strip().split('\t')
            if len(fields) > 2 or len(fields) < 2:
                print(line)
                continue
            word = fields[0]
            if len(word) > 1 and word[0].isalpha():
                count = int(fields[1])
                wordcounts[word] += 1

donttrainon = list()

# Here we create a list of volumed IDs not to be used for training.
# For instance, we have supplemented the dataset with volumes that
# are in the Norton but that did not actually occur in random
# sampling. We want to make predictions for these, but never use
# them for training.

for idx1, anid in enumerate(orderedIDs):
    reviewed = metadict[anid][0]
    if reviewed == 'addedbecausecanon':
        donttrainon.append(idx1)


authormatches = [list(donttrainon) for x in range(len(orderedIDs))]
# For every index in authormatches, identify a set of indexes that have
# the same author. Obvs, there will always be at least one.

# Since we are going to use these indexes to exclude rows, we also add
# all the ids in donttrainon to every volume

for idx1, anid in enumerate(orderedIDs):
    thisauthor = metadict[anid][6]
    for idx2, anotherid in enumerate(orderedIDs):
        otherauthor = metadict[anotherid][6]
        if thisauthor == otherauthor and not idx2 in authormatches[idx1]:
            authormatches[idx1].append(idx2)

for alist in authormatches:
    alist.sort(reverse = True)

# I am reversing the order of indexes so that I can delete them from
# back to front, without changing indexes yet to be deleted.

vocablist = [x[0] for x in wordcounts.most_common(3200)]
VOCABSIZE = len(vocablist)

volsizes = dict()
voldata = list()
classvector = list()

for volid, volpath in volspresent:

    with open(volpath, encoding = 'utf-8') as f:
        voldict = dict()
        totalcount = 0
        for line in f:
            fields = line.strip().split('\t')
            if len(fields) > 2 or len(fields) < 2:
                print(line)
                continue

            word = fields[0]
            count = int(fields[1])
            voldict[word] = count
            totalcount += count

    date = metadict[volid][2]
    date = date - 1700
    if date < 0:
        date = 0


    if usedate:
        features = get_features_with_date(voldict, vocablist, date, totalcount)
        voldata.append(features)
    else:
        features = get_features(voldict, vocablist)
        voldata.append(features / (totalcount + 0.001))


    volsizes[volid] = totalcount
    reviewed = metadict[volid][0]
    if reviewed == 'rev':
        classvector.append(1)
    else:
        classvector.append(0)

data = pd.DataFrame(voldata)

# Now do leave-one-out predictions.

linearpredictions = dict()
logisticpredictions = dict()

for i, volid in enumerate(orderedIDs):
    # trainingset = pd.concat([data[0:i], data[i+1:]])
    # trainingy = classvector[0:i] + classvector[i+1:]
    # yvals = np.array(trainingy)
    # testset = data[i: i + 1]
    listtoexclude = authormatches[i]
    trainingset, yvals, testset = sliceframe(data, classvector, listtoexclude, i)
    #model = Ridge(alpha = 0.001)
    # model.fit(trainingset, yvals)
    # linearpredictions[volid] = model.predict(testset)[0]
    linearpredictions[volid] = 0

    newmodel = LogisticRegression(C = .00005)
    trainingset, means, stdevs = normalizeandexport(trainingset, usedate)
    newmodel.fit(trainingset, yvals)

    testset = (testset - means) / stdevs
    logisticpredictions[volid] = newmodel.predict_proba(testset)[0][1]
    print(i)

with open(outputpath, mode = 'w', encoding = 'utf-8') as f:
    writer = csv.writer(f)
    header = ['volid', 'reviewed', 'obscure', 'pubdate', 'birthdate', 'gender', 'nation', 'allwords', 'linear', 'logistic', 'author', 'title', 'actually']
    writer.writerow(header)
    for volid in IDspresent:
        metadata = metadict[volid]
        reviewed = metadata[0]
        obscure = metadata[1]
        pubdate = metadata[2]
        birthdate = metadata[3]
        gender = metadata[4]
        nation = metadata[5]
        author = metadata[6]
        title = metadata[7]
        actually = metadata[8]
        allwords = volsizes[volid]
        linear = linearpredictions[volid]
        logistic = logisticpredictions[volid]
        outrow = [volid, reviewed, obscure, pubdate, birthdate, gender, nation, allwords, linear, logistic, author, title, actually]
        writer.writerow(outrow)


coefficients = list(zip((newmodel.coef_[0] * np.array(stdevs)), vocablist + ['pub.date']))
coefficients.sort()
for coefficient, word in coefficients:
    print(word + " :  " + str(coefficient))
















