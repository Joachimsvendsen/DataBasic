import os, random, logging
from collections import OrderedDict
from databasic import app, mongo
from databasic.forms import WordCounterPaste, WordCounterUpload, WordCounterSample, WordCounterLink
from databasic.logic import wordhandler, filehandler, oauth
from flask import Blueprint, render_template, request, redirect, g, abort
from flask.ext.babel import lazy_gettext as _

mod = Blueprint('wordcounter', __name__, url_prefix='/<lang_code>/wordcounter', template_folder='../templates/wordcounter')

logger = logging.getLogger(__name__)

"""
@app.route('/', subdomain='wordcounter')
def index():
	return render_template('wordcounter/index.html')
"""

@mod.route('/', methods=('GET', 'POST'))
def index():

	words = None

	forms = OrderedDict()
	forms['sample'] = WordCounterSample()
	forms['paste'] = WordCounterPaste('I am Sam\nSam I am\nThat Sam-I-am!\nThat Sam-I-am!\nI do not like that Sam-I-am!\nDo you like \ngreen eggs and ham?\nI do not like them, Sam-I-am.\nI do not like\ngreen eggs and ham.\nWould you like them \nhere or there?\nI would not like them\nhere or there.\nI would not like them anywhere.')
	forms['upload'] = WordCounterUpload()
	forms['link'] = WordCounterLink()

	if request.method == 'POST':
		ignore_case = True
		ignore_stopwords = True
		titles = _('')
		btn_value = request.form['btn']
		sample_id = ''

		if btn_value == 'paste':
			words = forms['paste'].data['area']
			ignore_case = forms[btn_value].data['ignore_case_paste']
			ignore_stopwords = forms[btn_value].data['ignore_stopwords_paste']
			title = _('your text')
		elif btn_value == 'upload':
			upload_file = forms['upload'].data['upload']
			words = process_upload(upload_file)
			ignore_case = forms[btn_value].data['ignore_case_upload']
			ignore_stopwords = forms[btn_value].data['ignore_stopwords_upload']
			title = upload_file.filename
		elif btn_value == 'sample':
			basedir = os.path.dirname(os.path.abspath(__file__))
			sample_file = forms['sample'].data['sample']
			words = filehandler.convert_to_txt(os.path.join(basedir,'../','../',sample_file))
			ignore_case = forms[btn_value].data['ignore_case_sample']
			ignore_stopwords = forms[btn_value].data['ignore_stopwords_sample']
			samplename = filehandler.get_sample_title(sample_file)
			title = samplename
			sample_id = title
		elif btn_value == 'link':
			url = forms['link'].data['link']
			if not 'http://' in url:
				url = 'http://' + url
			content = filehandler.download_webpage(url)
			words = content['text']
			ignore_case = forms[btn_value].data['ignore_case_link']
			ignore_stopwords = forms[btn_value].data['ignore_stopwords_link']
			title = _(content['title'])

		if words is not None:
			counts, csv_files = process_words(words, ignore_case, ignore_stopwords, btn_value=='sample')
			doc_id = mongo.save_words('wordcounter', counts, csv_files, ignore_case, ignore_stopwords, title, sample_id)
			return redirect(request.url + 'results/' + doc_id)

	return render_template('wordcounter.html', forms=forms.items(), tool_name='wordcounter')

@mod.route('/results/<doc_id>')
def results(doc_id):
	
	counts = None
	csv_files = None
	results = []

	try:
		doc = mongo.find_document('wordcounter', doc_id)
	except:
		logger.warning("Unable to find doc '%s'", doc_id)
		abort(400)

	counts = doc.get('counts')
	csv_files = doc.get('csv_files')

	# only render the top 40 results on the page (the csv contains all results)
	for c in range(len(counts)):
		results.append([])
		for w in range(_clamp(len(counts[c]), 0, 40)):
			results[c].append(counts[c][w])

	max_index = min(20, len(results[0]))
	min_index = max(0, max_index-5)
	random_unpopular_word = ['','']
	top_word = ''
	word_in_bigrams_count = 0
	word_in_trigrams_count = 0

	if len(results[0]) > 0:
		random_unpopular_word = results[0][random.randrange(min_index, max_index+1)] if len(results[0]) > 1 else results[0][0]

		'''
		Find the most popular word that is also present in bigrams and trigrams. 
		If none can be found, just get the most popular word.
		'''

		if len(results) == 3:
			for word in results[0]:
				top_word = word[0]
				word_in_bigrams_count = 0
				word_in_trigrams_count = 0
				for b in results[1]:
					if top_word in b[0]:
						word_in_bigrams_count += 1
				for t in results[2]:
					if top_word in t[0]:
						word_in_trigrams_count += 1
				if word_in_bigrams_count > 0 and word_in_trigrams_count > 0:
					break	

		if word_in_bigrams_count == 0 and word_in_trigrams_count == 0:
			top_word = results[0][0][0]

	whatnext = {}
	whatnext['top_word'] = top_word
	whatnext['word_in_bigrams_count'] = word_in_bigrams_count
	whatnext['word_in_trigrams_count'] = word_in_trigrams_count
	whatnext['random_unpopular_word'] = random_unpopular_word[0]
	whatnext['random_unpopular_word_count'] = random_unpopular_word[1]

	return render_template('wordcounter/results.html', results=results, whatnext=whatnext, csv_files=csv_files, tool_name='wordcounter', title=doc['title'], doc_id=doc_id)

@mod.route('/results/<doc_id>/download/<file_path>')
def download_csv(doc_id, file_path):
	if filehandler.file_exists(file_path):
		return filehandler.generate_csv(file_path)
	else:
		# if temp file has expired, generate a new one
		doc = mongo.find_document('wordcounter', doc_id)
		files = create_csv_files(doc.get('counts'))
		f = files[0]
		if '-bigram-counts.csv' in file_path:
			f = files[1]
		elif '-trigram-counts.csv' in file_path:
			f = files[2]
		return filehandler.generate_csv(f)

def process_upload(doc):
	file_path = filehandler.open_doc(doc)
	words = filehandler.convert_to_txt(file_path)
	filehandler.delete_file(file_path)
	return words

def process_words(words, ignore_case, ignore_stopwords, is_sample):

	stopwords_language = 'english' if is_sample or g.current_lang == 'en' else 'spanish'
	counts = wordhandler.get_word_counts(
		words,
		ignore_case,
		ignore_stopwords,
		stopwords_language)

	csv_files = create_csv_files(counts)

	return counts, csv_files

def create_csv_files(counts):
	files = []
	files.append(filehandler.write_to_csv(['word', 'frequency'], counts[0], '-word-counts.csv'))

	bigrams = []
	for w in counts[1]:
		freq = w[1]
		phrase = " ".join(w[0])
		bigrams.append([phrase, freq])

	files.append(filehandler.write_to_csv(['bigram phrase', 'frequency'], bigrams, '-bigram-counts.csv'))
	
	trigrams = []
	for w in counts[2]:
		freq = w[1]
		phrase = " ".join(w[0])
		trigrams.append([phrase, freq])

	files.append(filehandler.write_to_csv(['trigram phrase', 'frequency'], trigrams, '-trigram-counts.csv'))
	return files

def _clamp(n, minn, maxn):
    return max(min(maxn, n), minn)
