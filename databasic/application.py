import logging, os, sys, ntpath, logging.handlers
from flask import Flask, Blueprint, g, redirect, request, abort
from flask.ext.babel import Babel
from flask_debugtoolbar import DebugToolbarExtension
from flask.ext.mail import Mail
from sassutils.wsgi import SassMiddleware
from babel.support import LazyProxy
from logic import oauth
from logic.db import MongoHandler

ENV_CONFIG_FILE_VAR = 'APP_CONFIG_FILE'	# the environment variable holding path to app config file
ENV_CONFIG_FILE_VAR_MISSING_VAL = 'NOTSET' # the default val indicating the user needs to set the env config var

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# make sure config file is specified
config_file_path = os.environ.get(ENV_CONFIG_FILE_VAR, ENV_CONFIG_FILE_VAR_MISSING_VAL)
if config_file_path is ENV_CONFIG_FILE_VAR_MISSING_VAL:
	print("ERROR! missing necessary environment variable %s" % ENV_CONFIG_FILE_VAR)
	print("Set it with something like this and try again")
	print("  export "+ENV_CONFIG_FILE_VAR+"=/abs/path/to/DataBasic/config/development.py")
	sys.exit()

# set up logging
app_mode = os.path.splitext(ntpath.basename(config_file_path))[0]
log_file_path = os.path.join(basedir,'logs', app_mode+'.log')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler(log_file_path, maxBytes=5242880, backupCount=10)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.info("Starting DataBasic in %s mode" % app_mode)

# Initialize the app
app = Flask(__name__, instance_relative_config=False)
app.config.from_object('config.default')
app.config.from_pyfile('../config/settings.py')
# Load the file specified by the APP_CONFIG_FILE environment variable
# Variables defined here will override those in the default configuration
app.config.from_envvar(ENV_CONFIG_FILE_VAR)

# Setup sass auto-compiling
app.wsgi_app = SassMiddleware(app.wsgi_app, {
	'databasic': ('static/sass', 'static/css', '/static/css')
})

babel = Babel(app)
mongo = MongoHandler(app)
mail = Mail(app)
# uncomment to use toolbar (this slows the app down quite a bit)
# toolbar = DebugToolbarExtension(app)

@app.before_request
def before():
	if request.view_args and 'lang_code' in request.view_args:
		if request.view_args['lang_code'] not in ('es', 'en'):
			return abort(404) # bail on invalid language
		g.current_lang = request.view_args['lang_code']
		request.view_args.pop('lang_code')

@babel.localeselector
def get_locale():
	return g.get('current_lang', 'en')

@app.route('/')
def index():
	return redirect('/' + get_locale())

@app.route('/auth')
def auth():
	if 'code' not in request.args:
		print 'permission was not granted'
	else:
		print request.args['code']
		oauth.authorize(request.args['code'])
	return redirect(oauth.redirect_to())

from databasic.views import home
from databasic.views import samediff
from databasic.views import wordcounter
from databasic.views import wtfcsv
app.register_blueprint(home.mod)
app.register_blueprint(samediff.mod)
app.register_blueprint(wordcounter.mod)#, subdomain='wordcounter')
app.register_blueprint(wtfcsv.mod)

