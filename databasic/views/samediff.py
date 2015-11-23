import datetime, logging, json
from operator import itemgetter
from collections import OrderedDict
from ..application import mongo, app, mail
from ..forms import SameDiffUpload, SameDiffSample
from ..logic import filehandler
import databasic.tasks
from flask import Blueprint, render_template, request, redirect, url_for, g, abort, Response
from flask.ext.babel import lazy_gettext as _

mod = Blueprint('samediff', __name__, url_prefix='/<lang_code>/samediff', template_folder='../templates/samediff')

@mod.route('/', methods=('GET', 'POST'))
def index():

	forms = OrderedDict()
	forms['sample'] = SameDiffSample()
	forms['upload'] = SameDiffUpload()

	if request.method == 'POST':

		btn_value = request.form['btn']
		email = None
		is_sample_data = False

		if btn_value == 'upload':
			files = request.files.getlist('upload')
			file_paths = filehandler.open_docs(files)
			email = forms['upload'].data['email']
		elif btn_value == 'sample':
			file_paths = forms['sample'].data['samples']
			is_sample_data = True
			email = forms['sample'].data['email']

		if btn_value is not None and btn_value is not u'':
			return queue_files(file_paths, is_sample_data, email)

	return render_template('samediff/samediff.html', forms=forms.items(), tool_name='samediff')

@mod.route('/results')
def results():

	doc_id = None if not 'id' in request.args else request.args['id']
	if doc_id is None:
		return redirect(g.current_lang + '/samediff')

	job = mongo.find_document('samediff', doc_id)

	if not 'complete' in job['status']:
		return render_template('samediff/results.html', results=job, tool_name='samediff')

	if not 'humanReadableSimilarity' in job:
		
		# make a statement about how similar the docs are to each other
		cosineDiff = abs(job['cosineSimilarity'][0][0] - job['cosineSimilarity'][0][1])
		job['humanReadableSimilarity'] = str(interpretCosineSimilarity(cosineDiff))

		job['sameWords'] = _most_common_words(doc_id, job['filenames'][0], job['filenames'][1])
		job['diffWordsDoc1'] = _most_common_unique_words(job, 0, job['sameWords'])
		job['diffWordsDoc2'] = _most_common_unique_words(job, 1, job['sameWords'])

		# update with the new results so that this code doesn't have to run every time the page is loaded
		mongo.update_document('samediff', doc_id, job)

	return render_template('samediff/results.html', results=job, tool_name='samediff')

@mod.route('/results/<file1>-and-<file2>-common-words')
def show_common_words(file1, file2):
	doc_id = None if not 'id' in request.args else request.args['id']
	if doc_id is None:
		return redirect(g.current_lang + '/samediff')
	try:
		job = mongo.find_document('samediff', doc_id)
		results = _most_common_words(doc_id,file1,file2)
		return render_template("samediff/words-in-common.html", job=job, file1=file1, file2=file2, results=results, doc_id=doc_id, tool_name='samediff')
	except Exception as e:
		print e
		abort(400)

@mod.route('/results/download/<doc_id>/<filename>-tfidf.csv')
def download_tfidf_csv(doc_id, filename):
	try:
		job = mongo.find_document('samediff', doc_id)
		doc_idx = job['filenames'].index(filename)
		# TODO: catch case where filename isn't in results
		tfidf_results = job['tfidf'][doc_idx]
		download_filename = filehandler.generate_filename('csv', 'tfidf', filename)
		return Response(stream_csv(tfidf_results,
			['term','tfidf','frequency'],['word','tfidf score','time used']), 
			mimetype='text/csv; charset=utf-8', 
            headers={"Content-Disposition":"attachment;filename="+download_filename})
	except Exception as e:
		print e
		abort(400)

@mod.route('/results/download/<doc_id>/<filename1>-<filename2>-common-words.csv')
def download_common_words(doc_id, filename1, filename2):
	try:
		results = _most_common_words(doc_id,filename1,filename2)
		download_filename = filehandler.generate_filename('csv', 'common-words', filename1, filename2)
		return Response(stream_csv(results,
			['term','avg','doc1','doc2','total'],
			['word','average times used','times used in '+filename1,'times used in '+filename2,'times used in both files']), 
			mimetype='text/csv; charset=utf-8', 
            headers={"Content-Disposition":"attachment;filename="+download_filename})
	except Exception as e:
		print e
		abort(400)

@mod.route('/results/download/<doc_id>/<filename>-most-frequent-words.csv')
def download_most_frequent_words(doc_id, filename):
	# TODO
	# results = mongo.find_document('samediff', doc_id)
	# download_filename = filehandler.generate_filename('csv', 'most-frequent-words', filename)
	pass

def _most_common_words(job_id,filename1,filename2):
	job = mongo.find_document('samediff', job_id)
	doc1_idx = job['filenames'].index(filename1)
	doc2_idx = job['filenames'].index(filename2)
	# TODO: catch case where filename isn't in results
	doc1_freq_dist = { t['term']:t['frequency'] for t in job['tfidf'][doc1_idx]}
	doc2_freq_dist = { t['term']:t['frequency'] for t in job['tfidf'][doc2_idx]}
	terms = set(doc1_freq_dist.keys()+doc2_freq_dist.keys())
	
	results = [ {'term':t,'avg':float(doc1_freq_dist[t]+doc2_freq_dist[t])/2.0, 
			  'doc1':doc1_freq_dist[t], 'doc2':doc2_freq_dist[t],
			  'total':doc1_freq_dist[t]+doc2_freq_dist[t]} for t in terms 
		if t in doc1_freq_dist.keys() and t in doc2_freq_dist.keys() ]
	return sorted(results, key=itemgetter('avg','total'),reverse=True)

def _most_common_unique_words(job, index, sameWords):
	doc = job['filenames'][index]
	doc_freq_dist = { t['term']:t['frequency'] for t in job['tfidf'][index]}
	return sorted(
		[ {'term':t, 'freq': doc_freq_dist[t] } for t in doc_freq_dist.keys() if t not in (i['term'] for i in job['sameWords']) ],
		key=itemgetter('freq', 'term'), reverse=True)

'''
# trying to track status of the celery task here
@mod.route('/status/<task_id>')
def taskstatus(task_id):
	task = queue_files.AsyncResult(task_id)
	response = task.state
	return json.dumps(response)
	# return redirect('/')
'''

def queue_files(file_paths, is_sample_data, email):
	file_names = filehandler.get_file_names(file_paths)
	job_id = mongo.save_queued_files('samediff', file_paths, file_names, is_sample_data, email, request.url + 'results?id=')
	result = databasic.tasks.save_tfidf_results.apply_async(args=[job_id])
	print result
	return redirect(request.url + 'results?id=' + job_id)

def interpretCosineSimilarity(cosineDiff):
	# Cosine Similarity
	if cosineDiff <= 0.1:
		return _('similar')
	elif cosineDiff <= 0.2:
		return _('sort of similar')
	elif cosineDiff <= 0.3:
		return _('pretty different')
	else:
		return _('very different')

def stream_csv(data,prop_names,col_names):
    yield ','.join(col_names) + '\n'
    for row in data:
        try:
            attributes = []
            for p in prop_names:
                value = row[p]
                cleaned_value = value
                if isinstance( value, ( int, long, float ) ):
                    cleaned_value = str(row[p])
                else:
                    cleaned_value = '"'+value.encode('utf-8').replace('"','""')+'"'
                attributes.append(cleaned_value)
            yield ','.join(attributes) + '\n'
        except Exception as e:
            print "Couldn't process a CSV row: "+str(e)
            print e
            print row