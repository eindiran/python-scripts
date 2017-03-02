# -*- coding: utf-8 -*-
import numpy as np
import re
import time
from collections import defaultdict, Counter
from twython import Twython

TWITTER_APP_KEY = 'R1fNZIlwi5Jr6Hm8jsvoZ5jXj'
TWITTER_APP_KEY_SECRET = 'bwjMoQI51lBxiaSekC2X03Bb5WVYhviRH5f2jzZL9twT3zMwWv'
TWITTER_ACCESS_TOKEN = '781583492240945152-n8n7gkTZg9z1h8rMdpy5zgLRgqgEZAM'
TWITTER_ACCESS_TOKEN_SECRET = 'NFYjygVlXQO3WiUCz01KupJR0Dz3HUGh3SUDwHyc6PCol'
TWITTER_OWNER_ID = '781583492240945152'

twitter = Twython(app_key=TWITTER_APP_KEY, 
            app_secret=TWITTER_APP_KEY_SECRET, 
            oauth_token=TWITTER_ACCESS_TOKEN, 
            oauth_token_secret=TWITTER_ACCESS_TOKEN_SECRET)

def scrub_tweets(tweet_list):
    out = [] 
    for tweet in tweet_list:
        text = tweet['text']
        text = re.sub('@([A-Za-z0-9_]+)', '', text)
        text = re.sub('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        text = re.sub('^RT[ \t\n\r\f\v]+?', '', text)
        text = re.sub('^:[ \t\n\r\f\v]+?', '', text)
        if text:
            out.append(text)
    return out

def hashtag_finder(text):
    return re.findall('#\w+', text)

def sanitize_output_hashtags(text):
    hash_tags = hashtag_finder(text)
    for ht in hash_tags:
        tag_count = text.count(ht)
        if tag_count > 1:
            text = ''.join(text.rsplit(ht, tag_count-1))
            text = text.replace('  ', ' ')
    return text

def get_random_line(f):
    f.seek(0)
    line = next(f) #increment filepointer
    for i, current_line in enumerate(f):
        if np.random.randint(i + 2):
            continue
        line = current_line
    return line

def build_term_set_and_get_bounds(f):
    terms = []
    min_len = 140
    max_len = 0
    for i in xrange(10):
        line = get_random_line(f)
        if len(line) > max_len:
            max_len = len(line)
        if len(line) < min_len:
            min_len = len(line)
        for word in line:
            terms.append(word)
    return (set(terms), min_len, max_len)

def generate_term_vector(text, set_of_words):
    tv = defaultdict(int)
    for word in set_of_words:
        tv[word] = 1 if word in text else 0
    return tv

def compare_tweet_to_corpus(text, set_of_words, min_len, max_len):
    c = 0
    if len(text) < min_len:
        c -= 15
    elif len(text) > max_len:
        c -= 15
    c += sum(generate_term_vector(text, set_of_words).values())
    c -= (len(text)-min_len)/2
    return c

def sentence_splitter(text):
    text = text.replace(" ", "$$__$$__$$").replace("\t", "$$__$$__$$")
    text = text.replace(".", " ").replace("!", " ").replace("?", " ")
    split_text = text.split()
    sentences = []
    for sentence in split_text:
        sentences.append(sentence.replace("$$__$$__$$", " "))
    return sentences

def generate_count_dict(corpus):
    sentences = []
    for t in corpus:
        sentences.extend(sentence_splitter(t))
    count_dict = defaultdict(lambda : Counter())
    count_dict['<\s>']['<\s>'] = 0
    count_dict['</s>']['</s>'] = 0
    for sentence in sentences:
        words = sentence.strip().split()
        if not words: continue
        count_dict['<\s>'][words[0]] += 1
        for i, word in enumerate(words[:-1]):
            count_dict[word][words[i+1]] += 1
        count_dict[words[-1]]['</s>'] += 1
    return count_dict

def generate_mapping_dict(count_dict):
    mapping_dict = defaultdict(lambda : defaultdict(float))
    for k in count_dict.keys():
        s = 0.0
        for kk in count_dict[k].keys():
            s += count_dict[k][kk]
        for kk in count_dict[k].keys():
            try:
                mapping_dict[k][kk] = float(count_dict[k][kk])/s
            except ZeroDivisionError:
                mapping_dict[k][kk] = 0.0
    return mapping_dict
        
def test_print_count_dict(count_dict):
    for k in count_dict.keys():
        print "\n" + str(k) + ':\t',
        print count_dict[k]

def test_print_mapping_dict(mapping_dict):
    for k in mapping_dict.keys():
        print "\n" + str(k) + ":\t",
        print str(mapping_dict[k])

def generate_mapping(tl):
    cd = generate_count_dict(tl)
    return generate_mapping_dict(cd)


class MarkovChain(object):
    def __init__(self, corpus, hashtag):
        self.mapping_dict = generate_mapping(corpus)
        self.tag = hashtag

    def _accumulate_sentence(self, seed, max_count=(None, 0)):
        sentence = [seed] if seed != '<\s>' else []
        word = seed
        while word != '</s>':
            if sentence.count(max_count[0]) > max_count[1]:
                next_word = self._get_next_word(word, max_count[0])
            else:
                next_word = self._get_next_word(word)
            sentence.append(next_word)
            word = next_word
        return " ".join(sentence[:-1])

    def _get_next_word(self, word, prohibitted=None):
        probs = np.array([x[1] for x in sorted(self.mapping_dict[word].items(), key=lambda x: x[1])])
        probs /= probs.sum()
        candidates = [x[0] for x in sorted(self.mapping_dict[word].items(), key=lambda x: x[1])]
        next_word = np.random.choice(candidates, p=probs)
        if next_word == prohibitted:
            return self._get_next_word(word, prohibitted)
        else:
            return next_word

    def random_sentence(self):
        return self._accumulate_sentence('<\s>', (self.tag, 1))

    def random_seeded_sentence(self, word):
        return self._accumulate_sentence(word)

    def generate_tweet(self, mandatory_hashtag=None):
        sentences = []
        chars = 0 if not mandatory_hashtag else len(mandatory_hashtag)
        retries = 0
        for i in xrange(np.random.randint(2, 5)):
            sentence = self.random_sentence()
            if chars + len(sentence) > 140:
                if chars > 20:
                    break
                else:
                    continue
            elif sentence in sentences:
                if retries > 4 and chars > 20:
                    break
                i -= 1
                retries += 1
                continue
            else:
                sentences.append(sentence)
                chars += len(sentence)
        output_tweet = " ".join(sentences)
        if mandatory_hashtag:
            if mandatory_hashtag not in output_tweet:
                output_tweet = np.random.choice([mandatory_hastag+" "+output_tweet,
                                                 output_tweet+" "+mandatory_hashtag])
        return output_tweet

def scrape_tweets(hashtag, popular=False):
    if popular:
        query = twitter.search(q=hashtag, lang='en', result_type='popular')
        #For some bizarre reason the popular flag can only return fifteen tweets
    else:
        query = twitter.search(q=hashtag, lang='en', count=100)
    tweets = query['statuses']
    tweet_list = scrub_tweets(tweets)
    return tweet_list

def prompt_user_for_hashtag():
    search_for = None
    while not search_for:
        search_for = raw_input("Enter a hashtag to search:  ")
    if search_for[0] != '#':
        search_for = '#' + search_for
    mandatory_hashtag = search_for if raw_input("Press y if want the hashtag to be mandatory or n:  ") else None
    return (search_for, mandatory_hashtag)

def build_mc():   
    search_for, mandatory_hashtag = prompt_user_for_hashtag()
    tweet_list = scrape_tweets(search_for)
    corpus = []
    with open(search_for[1:]+'.twt', 'a+') as f:
        for tweet in tweet_list:
            f.write(tweet.encode('utf-8')+"\n")
        f.seek(0) # reset file pointer to beginning
        for line in f:
            if line:
                corpus.append(line)
    m = MarkovChain(corpus, search_for)
    return m

def generate_tweet_pool(markov_chain):
    tweet_pool = []
    for i in xrange(10):
        tweet_pool.append(markov_chain.generate_tweet())
    return tweet_pool

def get_best_tweet(markov_chain):
    tweet_pool = generate_tweet_pool(markov_chain)
    search_for = markov_chain.tag
    with open(search_for[1:]+'.twt', 'r') as f:
        r = build_term_set_and_get_bounds(f)
        term_set = r[0]
        min_len = r[1]
        max_len = r[2]
    current_best_score = -30
    best_tweet = ''
    for tweet in tweet_pool:
        s = compare_tweet_to_corpus(tweet, term_set, min_len, max_len)
        if s > current_best_score:
            current_best_score = s
            best_tweet = tweet
    return best_tweet

if __name__ == '__main__':
    m = build_mc()
    print get_best_tweet(m)
