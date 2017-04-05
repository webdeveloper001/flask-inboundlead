from flask import Blueprint, session
from flask_login import current_user, login_user
from assistantAIfunctions import *
from models import *
from googleAppFunctions import *
from datetime import datetime, timedelta
import json

authorization = Blueprint('authorization', __name__,template_folder='templates',static_folder='static')

SCOPES_DRIVE = 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/calendar ' \
               'https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email'

SCOPES_CALENDAR = 'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.profile ' \
              'https://www.googleapis.com/auth/userinfo.email'

SCOPES_GMAIL = 'https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/userinfo.email ' \
         'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.profile'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'representativ'

scopeDict = {'calendar':SCOPES_CALENDAR,'drive':SCOPES_DRIVE,'gmail':SCOPES_GMAIL}

def storeCredentials(credentials,credType):
  print credentials
  http = credentials.authorize(httplib2.Http())
  response,info=http.request("https://www.googleapis.com/oauth2/v2/userinfo",'GET')
  if response['status'] == '403':
    credentials.refresh(http)
    response, info = http.request("https://www.googleapis.com/oauth2/v2/userinfo", 'GET')
  userInfo=json.loads(info)
  creds=db.session.query(gCredentials).filter_by(email=userInfo['email']).first()
  if creds is not None and creds.credType!="gmail" and credType=="gmail" and creds.email!=config['DEFAULT_SALES_REP']:
    refreshToken=json.loads(creds.credentials)['refresh_token']
    creds.credType=credType
    credsUpdated = json.loads(credentials.to_json())
    credsUpdated['refresh_token']=refreshToken
    creds.credentials=client.OAuth2Credentials.from_json(json.dumps(credsUpdated)).to_json()
  elif creds is None:
    print credType
    creds=gCredentials(email=userInfo['email'],credentials=credentials.to_json(),credType=credType)
  db.session.add(creds)
  db.session.commit()
  return userInfo

@authorization.route('/Callback',methods=['GET'])
def oauth2callback():
  scopeType=request.args.get('scopeType')
  scope=scopeDict['calendar']
  if scopeType is not None:
    scope=scopeDict[scopeType]
  flow = client.flow_from_clientsecrets(
    CLIENT_SECRET_FILE,
    scope=scope,
    redirect_uri=url_for('authorization.oauth2callback', _external=True))
  flow.user_agent = APPLICATION_NAME
  flow.params['access_type'] = 'offline'
  flow.params['state'] = "scopeType="+ifNotNone(scopeType)+"&"
  flow.params['include_granted_scopes']="true"
  if 'code' not in request.args:
    auth_uri = flow.step1_get_authorize_url()
    return redirect(auth_uri)
  else:
    auth_code = request.args.get('code')
    state = splitStateUrlParams(request.args.get('state'))
    credentials = flow.step2_exchange(auth_code)
    userInfo = storeCredentials(credentials,scopeType)
    return redirect(url_for('authorization.updateAuth', email=userInfo['email'], given_name=userInfo['given_name'], type=state['scopeType']))

@authorization.route('/updateAuth',methods=['GET'])
def updateAuth():
  email=request.args.get('email')
  type=request.args.get('type')
  salesRep = db.session.query(sales_rep).filter_by(email=email).first()
  if salesRep is None:
    salesRep = sales_rep(email=email)
  salesRep.firstName = request.args.get('given_name')
  db.session.add(salesRep)
  db.session.commit()
  login_user(salesRep, remember=True)
  if type=='gmail':
    salesRep.monitorEmail=True
    #salesRep.watchAndStop()
  db.session.add(salesRep)
  db.session.commit()
  return redirect(request.args.get('next') or url_for('dashboard.home'))

@authorization.route('/CallbackCalendarInvite',methods=['GET'])
def oauth2callbackCalendarInvite():
  sid=request.args.get('id')
  print sid
  id=-1
  if sid is not None:
    id=int(sid)
  scopeType='calendar'
  scope=scopeDict[scopeType]
  flow = client.flow_from_clientsecrets(
    CLIENT_SECRET_FILE,
    scope=scope,
    redirect_uri=url_for('authorization.oauth2callbackCalendarInvite', _external=True))
  flow.user_agent = APPLICATION_NAME
  flow.params['access_type'] = 'offline'
  flow.params['state'] = "id="+str(id)+"&"
  flow.params['include_granted_scopes']="true"
  if 'code' not in request.args:
    auth_uri = flow.step1_get_authorize_url()
    return redirect(auth_uri)
  else:
    auth_code = request.args.get('code')
    print request.args.get('state')
    state = splitStateUrlParams(request.args.get('state'))
    credentials = flow.step2_exchange(auth_code)
    userInfo = storeCredentials(credentials,scopeType)
    return redirect(url_for('calendarConnect', email=userInfo['email'], given_name=userInfo['given_name'], id=state['id']))