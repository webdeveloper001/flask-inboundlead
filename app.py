# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#
from flask import Flask, render_template, flash, jsonify, send_from_directory, request
from flask import url_for, redirect, session
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CsrfProtect
import logging, csv, os
from logging import Formatter, FileHandler
#from flask.ext.heroku import Heroku
from flask_mail import Mail, Message
from flask_paginate import Pagination
from flask_migrate import Migrate
from flask_sslify import SSLify
from werkzeug.utils import secure_filename
from raven.contrib.flask import Sentry
from celery import Celery
import constants, json
from oauth2client import tools
from celery.schedules import crontab
import dateutil.parser
from flask_admin import Admin
from flask_cors import CORS, cross_origin

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#


app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
config=app.config

db = SQLAlchemy(app, session_options={"autoflush": True})
sentry = Sentry(app, dsn=config['SENTRY_DSN'])
celery = Celery(app.name, broker=os.environ['REDIS_URL'],backend=os.environ['REDIS_URL'],
                CELERY_TASK_RESULT_EXPIRES = 3600,CELERY_IGNORE_RESULT = True,
                CELERYBEAT_SCHEDULE = {
                  'every-minute': {
                    'task': 'tasks.processInboxes',
                    'schedule': crontab(minute='*/1'),
                    'args': (1,2),
                  },
                })

csrf = CsrfProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
mail = Mail(app)
sslify = SSLify(app)

try:
  flags = tools.argparser.parse_args([])
except ImportError:
  flags = None

# ----------------------------------------------------------------------------#
# google app integration specific functions
# ----------------------------------------------------------------------------#

from models import *
from forms import *
from assistantAIfunctions import *
from celeryTasks import processInboxes, processMessage
from agent import agent
from dashboard import dashboard
from web2lead import web2lead
from intercom2lead import intercom2lead
from authorization import authorization

admin = Admin(app, name='admin', template_mode='bootstrap3')
app.register_blueprint(agent)
app.register_blueprint(dashboard)
app.register_blueprint(web2lead)
app.register_blueprint(intercom2lead)
app.register_blueprint(authorization)

from scheduler import *

#----------------------------------------------------------------------------#
# aiScheduling specific handlers
# ----------------------------------------------------------------------------#
@app.route('/login',methods=['GET','POST'])
def login():
  return render_template('index/login.html')

@app.route('/calendarInvite',methods=['GET','POST'])
def calendarInvite():
  id=int(request.args.get('id'))
  return render_template('index/calendarInvite.html',id=id)

@app.route('/calendarConnect',methods=['GET','POST'])
def calendarConnect():
  sid=request.args.get('id')
  if sid=='-1':
    flash("the link you provided is incorrect. Please check your link again!")
    return redirect(url_for(login))
  id=int(sid)
  salesRep = db.session.query(sales_rep).filter_by(id=id).first()
  email=request.args.get('email')
  print email
  calendarList=getCalendarList(email)
  calendarValues={"callDuration":stringifyTime(30)}
  calendarValues['dayStart']=stringifyTime(9)+":"+stringifyTime(00)
  calendarValues['dayEnd'] = stringifyTime(18) + ":" + stringifyTime(00)
  if request.method=='POST':
    print request.form
    dayStart=datetime.strptime(request.form['dayStartTime'],"%H:%M")
    dayEnd=datetime.strptime(request.form['dayEndTime'],"%H:%M")
    print dayStart, dayEnd
    workHours={'dayStart':{'hour':dayStart.hour,'minute':dayStart.minute},'dayEnd':{'hour':dayEnd.hour,'minute':dayEnd.minute}}
    calendarIds=request.form.getlist('calendarIds')
    salesRep.updateAccounts(email=email,type="add",value={"workHours":workHours,"calendars":calendarIds})
    db.session.add(salesRep)
    db.session.commit()
    flash("Thanks for connecting your calendars")
    redirect(url_for(index))
  return render_template('index/calendarConnect.html',calendarList=calendarList, calendarValues=calendarValues, salesRep=salesRep)

@app.route('/addTemplates',methods=['GET','POST'])
@login_required
def addTemplates():
  form = AddTemplates(request.form)
  if form.validate_on_submit():
    salesRep = db.session.query(sales_rep).filter_by(email=current_user.salesRep).first()
    if salesRep.templates is None:
      salesRep.templates={}
    templates={}
    templates['common']={}
    templates['common'][form.data['template1q']] = form.data['template1a']
    templates['common'][form.data['template2q']] = form.data['template2a']
    templates['common'][form.data['template3q']] = form.data['template3a']
    templates['common'][form.data['template4q']] = form.data['template4a']
    templates['common'][form.data['template5q']] = form.data['template5a']
    templates['common']['onboardingSubject']=form.data['onboardingSubject']
    templates['common']['first'] = form.data['template6a']
    templates['common']['second'] = form.data['template7a']
    print templates
    db.session.query(sales_rep).filter_by(email=salesRep.email).update({"templates": templates})
    #SQLALCHEMY JSON update needs to be for the entire dictionary and through session update
    db.session.add(salesRep)
    db.session.commit()
    flash("Thanks for updating email templates")
    return redirect(url_for('home'))
  return render_template('forms/addTemplates.html',form=form)

#celery task per sales_rep. cuz repetitive. For now, will use flask call
@app.route('/sendDripMails/<user_id>')
def sendDripMails(user_id):
  salesRep=db.session.query(sales_rep).filter_by(email=user_id).first()
  salesRep.followUpColdLeads()
  db.session.commit()
  return 'OK', 200

@app.route('/processInbox/<user_id>')
def processReplies(user_id):
  salesRep = db.session.query(sales_rep).filter_by(email=user_id).first()
  salesRep.getNewAssistantEmails()
  db.session.commit()
  return 'OK', 200


@app.route('/_ah/push-handlers/gmailListener/',methods=['GET','POST'])
@csrf.exempt
def getEmailReply():
  try:
    data=json.loads(request.data)
    message=json.loads(base64.b64decode(data['message']['data']))
    historyId=message['historyId']
    print historyId, message['emailAddress']
    #processMessage.delay(message['emailAddress'])
    return 'OK', 200
  except:
    return 'NOT OK', 400

@app.route('/frontReply',methods=['GET','POST'])
@csrf.exempt
def frontReply():
  print "TESTING !!!"
  print request.data
  if request.method=='POST':
    print "FRONT REPLY REQUEST >>> ",json.loads(request.data)
  return 'OK',200

@app.route('/frontScheduleCall',methods=['GET','POST'])
@csrf.exempt
def frontScheduleCall():
  print "TESTING Call !!!"
  print request.data
  if request.method=='POST':
    print "FRONT Schedule Call Request >>> ",json.loads(request.data)
  return 'OK',200

@app.route('/pricing',methods=['GET','POST'])
def pricing():
  return render_template('index/pricing.html')

@app.route('/integrations',methods=['GET','POST'])
def integrations():
  return render_template('index/integrations.html')

@app.route('/',methods=['GET','POST'])
def index():
  if request.method=='POST':
    email=request.form['email']
    betaUser = betaUsers(email)
    db.session.add(betaUser)
    db.session.commit()
    flash("Thanks for your interest and subscribing!")
  return render_template('index/index.html')

@app.route('/privacyPolicy',methods=['GET','POST'])
def privacyPolicy():
  return redirect(url_for('static', filename='/'.join(['indexAssets', 'privacyPolicy.pdf'])), code=301)

@app.route('/tos',methods=['GET','POST'])
def tos():
  return redirect(url_for('static', filename='/'.join(['indexAssets', 'privacyPolicy.pdf'])), code=301)

#----------------------------------------------------------------------------#
# login and other generic controllers
# ----------------------------------------------------------------------------#
@app.teardown_request
def shutdown_session(exception=None):
  if exception:
    db.session.rollback()
  db.session.remove()

@app.teardown_appcontext
def shotdown_session(exception=None):
  if exception:
    db.session.rollback()
  db.session.remove()

@login_manager.user_loader
def load_user(id):
  if id is None or id == 'None':
    id = -1
  return sales_rep.query.get(int(id))

# ----------------------------------------------------------------------------#
# google domain verification Handlers
# ----------------------------------------------------------------------------#
@app.route('/google983e1c851ab9e1ed.html')
@csrf.exempt
def googleDomainVerifier():
  return send_from_directory('static','google983e1c851ab9e1ed.html' )

# ----------------------------------------------------------------------------#
# Error Handlers
# ----------------------------------------------------------------------------#
@app.errorhandler(config['ERROR_HANDLER_LEVEL'])
def internal_error(error):
  print error
  db.session.rollback()
  #raiseError(json.dumps(error))
  return render_template('errors/500.html'), 500

@app.errorhandler(404)
def not_found_error(error):
  return render_template('errors/404.html'), 404

if not app.debug:
  from logging.handlers import SMTPHandler
  mail_handler = SMTPHandler('127.0.0.1',
                             'hi@tryscribe.com',
                             ['admin@tryscribe.com'], 'Your Application Failed')
  mail_handler.setFormatter(Formatter('''
  Message type:       %(levelname)s
  Location:           %(pathname)s:%(lineno)d
  Module:             %(module)s
  Function:           %(funcName)s
  Time:               %(asctime)s

  Message:

  %(message)s
  '''))
  mail_handler.setLevel(logging.ERROR)
  app.logger.addHandler(mail_handler)
  file_handler = FileHandler('error.log')
  file_handler.setFormatter(
    Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
  )
  app.logger.setLevel(logging.INFO)
  file_handler.setLevel(logging.INFO)
  app.logger.addHandler(file_handler)
  app.logger.info('errors')


