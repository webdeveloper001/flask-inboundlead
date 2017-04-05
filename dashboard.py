from flask import Flask, Blueprint, render_template, request, session, Markup
import dateutil.parser, json, arrow
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from models import *
from assistantAIfunctions import *
from app import db
from authorization import storeCredentials
from scheduler import getCalendarList

dashboard = Blueprint('dashboard', __name__,template_folder='templates',static_folder='static')
compulsoryFieldDict={"Email":"","Name":"","Phone":"","Company":"","Department":"","Company size":"","Revenue":"","Age":"",
                     "location":"","Industry":"","Experience":""}
#----------------------------------------------------------------------------#
# Dashboard specific handlers
# ----------------------------------------------------------------------------#
@dashboard.route("/home", methods=["GET","POST"])
@login_required
def home():
  salesRep = db.session.query(sales_rep).filter_by(email=current_user.email).first()
  return render_template('dashboard/home.html',salesRep=salesRep)

@dashboard.route("/getScribe", methods=["GET","POST"])
@login_required
def getScribe():
  salesRep = db.session.query(sales_rep).filter_by(email=current_user.email).first()
  code="Your scribe code here..."
  if request.method=='POST':
    #formTitle=request.form['formTitle']
    print request.form['compulsoryFields']
    salesRep.compulsoryFields=request.form['compulsoryFields']
    if salesRep.spreadSheetId is None or salesRep.spreadSheetId == "":
      defaultRep=db.session.query(sales_rep).filter_by(id=config['DEFAULT_SALESREP_ID']).first()
      salesRep.spreadSheetId=createSpreadSheet(salesRep.email,defaultRep)
    db.session.add(salesRep)
    db.session.commit()
    code = getCode(salesRep)
  return render_template('dashboard/getScribe.html',code=code,compulsoryFields=salesRep.compulsoryFields)

@dashboard.route("/setup", methods=["GET","POST"])
@login_required
def setup():
  return render_template('dashboard/setup.html')

@dashboard.route('/integrate',methods=['GET','POST'])
@login_required
def integrate():
  salesRep = db.session.query(sales_rep).filter_by(email=current_user.email).first()
  if request.method=='POST':
    salesRep.webHookUrl=request.form['webHookUrl']
    db.session.add(salesRep)
    db.session.commit()
    flash("Thanks for integrating your webhook. We have redirected your lead data to the url")
  return render_template('dashboard/integrate.html',spreadSheetId=salesRep.spreadSheetId,spreadSheetHeader=constants.SPREADSHEET_HEADER)

@dashboard.route('/connectDrive',methods=['GET','POST'])
@login_required
def connectDrive():
  salesRep = db.session.query(sales_rep).filter_by(email=current_user.email).first()
  if salesRep.spreadSheetId is None or salesRep.spreadSheetId=="":
    defaultRep = db.session.query(sales_rep).filter_by(email=config['DEFAULT_REP']).first()
    salesRep.spreadSheetId=createSpreadSheet(current_user.email,defaultRep)
    db.session.add(salesRep)
    db.session.commit()
  return render_template('dashboard/integrate.html',spreadSheetId=salesRep.spreadSheetId,spreadSheetHeader=constants.SPREADSHEET_HEADER)


@dashboard.route('/connectMailbox',methods=['GET','POST'])
@login_required
def connectMailbox():
  salesRep = db.session.query(sales_rep).filter_by(email=current_user.email).first()
  return render_template('dashboard/connectMailbox.html',monitorEmail=salesRep.monitorEmail)

@dashboard.route('/schedule',methods=['GET','POST'])
@login_required
def schedule():
  salesRep = db.session.query(sales_rep).filter_by(email=current_user.email).first()
  calendarList=getCalendarList(salesRep.email)
  calendarValues={"callDuration":stringifyTime(salesRep.callDuration)}
  calendarValues['dayStart']=stringifyTime(salesRep.workHours['dayStart']['hour'])+":"+stringifyTime(salesRep.workHours['dayStart']['minute'])
  calendarValues['dayEnd'] = stringifyTime(salesRep.workHours['dayEnd']['hour']) + ":" + stringifyTime(salesRep.workHours['dayEnd']['minute'])
  if request.method=='POST':
    print request.form
    salesRep.callDuration=request.form['callDuration']
    dayStart=datetime.strptime(request.form['dayStartTime'],"%H:%M")
    dayEnd=datetime.strptime(request.form['dayEndTime'],"%H:%M")
    print dayStart, dayEnd
    workHours={'dayStart':{'hour':dayStart.hour,'minute':dayStart.minute},'dayEnd':{'hour':dayEnd.hour,'minute':dayEnd.minute}}
    salesRep.workHours=workHours
    print salesRep.workHours
    calendarIds=request.form.getlist('calendarIds')
    salesRep.updateAccounts(email=salesRep.email,type="add",value={"workHours":workHours,"calendars":calendarIds})
    db.session.add(salesRep)
    db.session.commit()
    flash("Thanks for connecting your calendars")
  return render_template('dashboard/schedule.html',calendarList=calendarList, calendarValues=calendarValues)


@dashboard.route("/qualify2", methods=["GET","POST"])
@login_required
def qualify2():
  return render_template('dashboard/qualify2.html', compulsoryFieldDict=compulsoryFieldDict)

@dashboard.route("/qualify", methods=["GET","POST"])
@login_required
def qualify():
  if request.method=='POST':
    salesRep = db.session.query(sales_rep).filter_by(email=current_user.email).first()
    salesRep.qualify['compulsoryFields']=[item.lower() for item in request.form.get('compulsoryFields')]
    salesRep.qualify['location']=[item.lower() for item in request.form.get('location')]
    salesRep.qualify['title']=[item.lower() for item in request.form.get('title')]
    salesRep.qualify['companySize']=[item.lower() for item in request.form.get('companySize')]
    salesRep.qualify['revenue']=[item.lower() for item in request.form.get('revenue')]
    salesRep.qualify['department'] = [item.lower() for item in request.form.get('department')]
    db.session.add(salesRep)
    db.session.commit()
    flash('Thanks for the submission. Your form will reflect the changes')
  return render_template('dashboard/qualify.html',compulsoryFieldDict=compulsoryFieldDict)

@dashboard.route('/deactivate',methods=['GET','POST'])
@login_required
def deactivate():
  if request.method=='POST':
    salesRep = db.session.query(sales_rep).filter_by(email=current_user.email).first()
    creds = db.session.query(gCredentials).filter_by(email=current_user.email).first()
    credentials = OAuth2Credentials.from_json(creds.credentials)
    db.session.commit()
    db.session.delete(salesRep)
    db.session.delete(creds)
    #db.session.delete(current_user)
    db.session.commit()
    credentials.revoke(httplib2.Http())
    flash("Your assistant has been deactivated")
    return redirect(url_for('index'))
  return render_template('dashboard/deactivate.html')

@dashboard.route("/logout", methods=["GET"])
@login_required
def logout():
  print current_user
  logout_user()
  return redirect(url_for('index'))