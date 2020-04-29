import nltk, re, string, logging
from operator import itemgetter
from nltk import FreqDist
from nltk.corpus import stopwords

DEFAULT_TEXT = 'I am Sam\nSam I am\nThat Sam-I-am!\nThat Sam-I-am!\nI do not like that Sam-I-am!\nDo you like \ngreen eggs and ham?\nI do not like them, Sam-I-am.\nI do not like\ngreen eggs and ham.\nWould you like them \nhere or there?\nI would not like them\nhere or there.\nI would not like them anywhere.'

logger = logging.getLogger(__name__)

MAX_ITEMS = 10000

def get_word_counts(text=None, ignore_case=True, ignore_stop_words=True, stopwords_language='english', get_bigrams=True, get_trigrams=True):
    text = DEFAULT_TEXT if text is None else text
    words = _create_words(text, ignore_case)
    
    total_word_count = len(words)
    unique_words = _sort_count_list(_count_words(words, ignore_stop_words, stopwords_language))[0:MAX_ITEMS]
    
    if get_bigrams:
        bigrams = _sort_count_list(_count_bigrams(words))[0:MAX_ITEMS]
    else:
        bigrams = []
    
    if get_trigrams:
        trigrams = _sort_count_list(_count_trigrams(words))[0:MAX_ITEMS]
    else:
        trigrams = []

    logger.debug("  %d unique_words, %d bigrams, %d trigrams, %d total words" % (len(unique_words),len(bigrams), len(trigrams), total_word_count))
    return {"unique_words":unique_words, "bigrams" : bigrams, "trigrams":trigrams, "total_word_count":total_word_count}

def _create_words(text, ignore_case):
    words = re.findall(r"[\w']+|[.,!?;]", text, re.UNICODE)
    if ignore_case:
        words = [w.lower() for w in words]
    return [w for w in words if not w in string.punctuation]

def _sort_count_list(freq_dist):
    items = list(freq_dist.items())
    return sorted(items, key=itemgetter(1), reverse=True)

def _count_words(words, ignore_stop_words, stopwords_language):
    fdist = FreqDist(words)
    # remove stopwords here rather than in corpus text for speed
    if ignore_stop_words:
        # http://stackoverflow.com/questions/7154312/how-do-i-remove-entries-within-a-counter-object-with-a-loop-without-invoking-a-r
        for w in list(fdist):
            if w in stopwords.words(stopwords_language):
                del fdist[w]
    return fdist

def _count_bigrams(words):
    bigrams = nltk.bigrams(words)
    return nltk.FreqDist(bigrams)

def _count_trigrams(words):
    trigrams = nltk.trigrams(words)
    return nltk.FreqDist(trigrams)
