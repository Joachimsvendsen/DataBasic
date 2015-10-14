import os, sys, json, gspread
import gdata.docs.service
from oauth2client.client import SignedJwtAssertionCredentials, OAuth2WebServerFlow

'''
Public API
'''
def authorize(code):
	oauth.authorize(code)

def open_doc_from_url(url, redirect_to):
	oauth.redirect_to = redirect_to
	if not oauth.authorized:
		return {
			'authenticate': oauth.authenticate_app(),
			'doc': None
		}
	else:
		return {
			'authenticate': None,
			'doc': oauth.open_url(url)
		}

def redirect_to():
	return oauth.redirect_to

'''
Handler for Google's OAuth2
https://gist.github.com/cspickert/1650271
'''
class OAuthHandler:

	def __init__(self, redirect_uri='http://localhost:5000/auth'):
		self.authorized = False
		self.redirect_to = ""
		self._data_client = gdata.docs.service.DocsService() # used for docs
		self._load_credentials()
		self.flow = OAuth2WebServerFlow(
			client_id=self._key['client_email'],
			client_secret=self._key['client_secret'],
			scope=['https://www.googleapis.com/auth/drive.readonly', 'https://spreadsheets.google.com/feeds'],
			redirect_uri=redirect_uri)

	def _load_credentials(self):
		if os.path.isfile('instance/credentials.json'):
			self._key = json.load(open('instance/credentials.json'))
		else:
			print 'Credentials could not be loaded. If you haven\'t created them, follow the instructions at https://developers.google.com/api-client-library/python/auth/web-app'
			self._key = {
				'client_email': '',
				'client_secret': ''
			}

	def authenticate_app(self):
		return self.flow.step1_get_authorize_url()

	def authorize(self, code):
		credentials = self.flow.step2_exchange(code)
		self._client = gspread.authorize(credentials)
		self._data_client.ClientLogin(self._key['client_email'], self._key['client_secret'])
		self.authorized = True

	def open_url(self, url):
		# TODO: make this work with docs as well (only spreadsheets work at the moment)
		return self._client.open_by_url(url)

oauth = OAuthHandler()