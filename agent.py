from flask import Flask, Blueprint, render_template, request, session, Markup
import dateutil.parser, json, arrow
from models import *
from assistantAIfunctions import *
from app import db

agent = Blueprint('agent', __name__,template_folder='templates',static_folder='static')

@agent.before_request
def check_valid_login():
  login_valid = 'loginValid' in session
  if request.method=='GET' and request.args.get('username')=="agent123" and request.args.get('password')=="agent321":
      session['loginValid'] = True
      return redirect(request.args.get('next') or url_for('.agentReview'))
  elif not login_valid:
      return render_template('forms/agentLogin.html')

@agent.route('/agent/addleads',methods=['GET','POST'])
def addLeads():
  try:
    if request.method=='POST':
      subject=request.form['subject']
      mailText=request.form['mailText']
      fileName=uploadFile(request)
      if fileName is not None:
        with open(fileName) as csvFile:
          f=csvFile.readlines()
        for line in f:
          leadInfo=line.split(',')
          salesRep=db.session.query(sales_rep).filter_by(email=leadInfo[0]).first()
          if salesRep is None:
            flash("The salesRep doesnt exist"+salesRep.email)
            continue
          lead=leads(salesRepId=salesRep.id, email = leadInfo[1], firstName = leadInfo[2], company=leadInfo[3])
          #lead.thread = leadThreads(leadId=lead.id)
          #lead.thread.subject=personalize(lead,subject)
          db.session.add(lead)
          db.session.commit()
          salesRep.onboardLead(lead,subject,mailText)
          db.session.commit()
        flash('leads created and outbound email sent!')
  except Exception as e:
    flash(repr(e))
    raiseError('addLeads Error: '+repr(e))
  return render_template('forms/agentAddLeads.html')


@agent.route('/agent/home', methods=['GET', 'POST'])
def agentHome():
  return redirect(url_for('.agentReview'))

@agent.route('/agent/logout', methods=['GET', 'POST'])
def agentLogout():
  session.pop('loginValid')
  print session
  return redirect(url_for('.agentHome'))

@agent.route('/agent/review',methods=['GET','POST'])
def agentReview():
  leadId=request.args.get('lead')
  if leadId is None:
    reviewLeads=db.session.query(leadThreads).filter_by(review=True).all()
    return render_template('pages/agentReview.html',leadReviews=reviewLeads)
  else:
    cancel=request.args.get('cancel')
    if cancel is not None and cancel=='1':
      lead=db.session.query(leads).filter_by(id=leadId).first()
      lead.status=constants.FREEZE
      lead.thread.setReview("not relevant lead",False)
      db.session.add(lead)
      db.session.commit()
      reviewLeads = db.session.query(leadThreads).filter_by(review=True).all()
      return render_template('pages/agentReview.html', leadReviews=reviewLeads)
    lead=db.session.query(leads).filter_by(id=leadId).first()
    salesRep = lead.salesRep
    host = db.session.query(hosts).filter_by(email=salesRep.hostEmail).first()
    if lead.callTime is None:
      callTime=None
    else:
      callTime=datetime.strftime(lead.callTime, "%B %d,%Y %H:%M:%S") #need to convert this to wit.ai readable form hence
    if request.method == 'POST':
      lead.review=False
      if request.form['firstName']!="None":
        lead.firstName=request.form['firstName']
      if request.form['phone']!="None":
        lead.phone=getTextEntities(request.form['phone'])['phone_number'][0]['value']
      if request.form['to'] != "None":
        lead.email=request.form['to']
      if request.form['cc'] != "None":
        lead.thread.latestParticipants=request.form['cc']
      if request.form['callTime'] is not None and request.form['callTime']!="None" and request.form['callTime']!="":
        try:
          callTimeSubmitted=getTextEntities(request.form['callTime'])['datetime'][0]['value']
          lead.callTime = arrow.get(callTimeSubmitted).datetime
          callTime = datetime.strftime(lead.callTime, "%B %d,%Y %H:%M:%S")
        except Exception as e:
          flash('callTime parse error: '+repr(e))
      db.session.add(lead)
      if request.form['submit']=="Send Reply":
        salesRep.sendReplyEmail(lead,request.form['replyEmail'])
      elif request.form['submit']=="Schedule Call":
        salesRep.scheduleCall(lead)
      elif request.form['submit']=="Check FreeBusy":
        if callTime is not None:
          freeBusy=salesRep.checkFreeBusy(dateutil.parser.parse(callTime))
          return render_template('pages/specificLeadReview.html', lead=lead, callTime=callTime,
                               templates=json.dumps(salesRep.templates, indent=4, separators=(',', ': ')),
                               dayStart=str(host.dayStart), dayEnd=str(host.dayEnd), freeBusy=json.dumps(freeBusy, indent = 4, separators = (',', ': ')))
        else:
          flash('Error: a valid time value is needed')
      db.session.commit()
      flash(Markup('Thanks! Your action has been processed! <a href="/agent/review">Back</a>'))
    return render_template('pages/specificLeadReview.html',lead=lead, callTime=callTime,
                           templates=json.dumps(salesRep.templates, indent = 4, separators = (',', ': ')),
                           dayStart=str(host.dayStart),dayEnd=str(host.dayEnd),freeBusy="None")
