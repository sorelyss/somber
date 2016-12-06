import numpy as np

from preprocessing.ortho import Orthographizer
from thsom import THSom


def wordlist_from_dpalign(filename, maxlen):

    wordlist = []

    for line in open(filename):

        word, pron = line.strip().split()

        if len(word) <= maxlen and "-" not in word:
            wordlist.append("#{0}#".format(word))

    return wordlist

if __name__ == "__main__":

    np.random.seed(44)

    wordlist = wordlist_from_dpalign("data/dpalign-txt-dutch.txt.dpalign", 15)

    test_list = ['#gedaan', '#haan', '#maan', '#ongedaan', '#spaans', '#man', '#mannen', '#kan', '#kannen']

    o = Orthographizer(15)
    X = o.transform(wordlist)
    np.random.shuffle(X)

    X_test = o.transform(test_list)

    r = THSom(30, 30, X.shape[2], 1.0, 0.2)
    bmus = r.train(X[:1000], batch_size=100, num_epochs=100)
