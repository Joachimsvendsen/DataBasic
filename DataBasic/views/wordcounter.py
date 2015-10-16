from .. import app, mongo
from ..forms import WordCountForm
from ..logic import wordhandler, filehandler, oauth
from flask import Blueprint, render_template, request, redirect

mod = Blueprint('wordcounter', __name__, url_prefix='/<lang_code>/wordcounter', template_folder='../templates/wordcounter')

"""
@app.route('/', subdomain='wordcounter')
def index():
	return render_template('wordcounter/index.html')
"""

@mod.route('/', methods=('GET', 'POST'))
def index():

	counts = []
	csv_files = []
	form = WordCountForm()
	words = None
	tab = 'paste' if not 'tab' in request.args else request.args['tab']
	uuid = None if not 'id' in request.args else request.args['id']
	share_url = None

	if uuid is not None:
		share_url = 'localhost:5000' + request.path + "?id=" + uuid	
		doc = mongo.get_document('wordcounter', uuid)
		words = doc.get('doc')
		counts, csv_files = process_words(
			words, 
			doc.get('ignore_case'), 
			doc.get('ignore_stopwords')
			)

	if request.method == 'POST':

		tab = form['input_type'].data

		if form.validate():
			
			if tab == 'paste':
				words = form.data['area']
			elif tab == 'upload':
				words = process_upload(form.data['upload'])
			elif tab == 'link':
				doc = oauth.open_doc_from_url(form.data['link'], request.url + "?tab=link")
				if doc['authenticate'] is not None:
					return (redirect(doc['authenticate']))
				else:
					words = doc['doc']

			uuid = mongo.save_words('wordcounter', words, form.data['ignore_case'], form.data['ignore_stopwords'])
			counts, csv_files = process_words(words, form.data['ignore_case'], form.data['ignore_stopwords'])
			share_url = 'localhost:5000' + request.path + "?id=" + uuid		

	return render_template('wordcounter.html', form=form, tab=tab, results=counts, csv_files=csv_files, share_url=share_url)

@mod.route('/download-csv/<file_path>')
def download_csv(file_path):
	return filehandler.generate_csv(file_path)

def process_upload(doc):
	file_path = filehandler.open_doc(doc)
	words = filehandler.convert_to_txt(file_path)
	filehandler.delete_file(file_path)
	return words

def process_words(words, ignore_case, ignore_stopwords):

	counts = wordhandler.get_word_counts(
		words,
		ignore_case,
		ignore_stopwords)

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
