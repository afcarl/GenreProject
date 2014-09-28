piketty
-------

A lot of Python scripts for metadata munging are collecting here. Some of them are related to a specific project undertaken w/ Hoyt Long and Richard So, exploring a claim from Thomas Piketty.

But as part of that project, I also did some general metadata munging that got reused elsewhere, and it's documented here (as well as in GenreProject/metadata).

The general flow was

1) Use the java code under /pages/pages to make page-level predictions for two datasets, pre-1900 and 1900-1923.

2) Use the python code under /GenreProject/python/extract to collate these predictions with the raw data and extract wordcounts for *only the fiction pages* from *only volumes with more than 70% of their pages identified as fiction.*

The scripts I used to build pbs arrays for these jobs are in /extract. The results of the extraction are stored in /projects/ichass/usesofscale/fiction/

3) Create the dataset /metadata/filteredfiction.tsv by running refine_fiction.py in this repo. This takes as raw material the file filenames.txt that was created in the /usesofscale/fiction/ directory. It compares it to metadata, and filters it by removing any volumes explicitly labeled as 'Biography' or 'Autobiography' in the metadata. Then it pairs filenames with the metadata to create the metadata subtable filteredfiction.

4) A final optional step involves selecting files from filteredfiction to use for topic modeling. I did this with constraints on temporal distribution (trying to get as close as possible to 50 vols per year) and also attempting to avoid duplication as far as possible with an easy metadata-based strategy.

FictionSample.py -- Used this for selecting the topic modeling sample.

refine_fiction.py -- Filtered the initial fiction extraction by comparing it to metadata and removing any known biographies.

modelingcounter.py -- A variant of wordcounter.py that I'm using for more precise counting of currency-related words.