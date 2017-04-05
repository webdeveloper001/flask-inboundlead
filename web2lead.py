from flask import Blueprint, render_template
from flask_cors import CORS, cross_origin

from assistantAIfunctions import *
from app import csrf, config
from models import sales_rep, leads
from datetime import datetime, timedelta
from scheduler import *
import json

web2lead = Blueprint('web2lead', __name__,template_folder='templates',static_folder='static')

cors = CORS(web2lead)
#----------------------------------------------------------------------------#
# web2lead specific handlers
# ----------------------------------------------------------------------------#

@web2lead.route('/scribeFormPost1/<id>',methods=['GET','POST'])
@csrf.exempt
@cross_origin()
def scribeFormPost1(id):
  #raiseError("INTO SCRIBE FORM POST 1")
  print config
  responseObject={}
  leadId=None
  salesRep = db.session.query(sales_rep).filter_by(id=id).first()
  data = json.loads(request.data)
  if 'leadId' in data.keys():
    lead=db.session.query(leads).filter_by(id=data['leadId']).first()
    lead.updateEntities(data)
    leadId=data['leadId']
    print lead.entities['name']
    responseObject = {'id': id, 'leadId':leadId}
  elif 'leadId' not in data.keys():
    email = data['email']
    company=""
    if 'company' in data.keys():
      company=data['company']
    leadInfo={'email':email,'name':"",'company':company}
    try:
      leadInfo = getLeadInfo(email)
      print leadInfo
    except Exception as e:
      print e
    lead=leads(salesRepId=salesRep.id,firstName=leadInfo['name'],company=leadInfo['company'],email=email,entities=leadInfo)
    db.session.add(lead)
    db.session.commit()
    leadId=lead.id
    responseObject = {'id': id, 'leadId': leadId}
    print responseObject
    compulsoryFieldResponse = salesRep.qualifyCompulsoryFields(leadInfo)
    if 'compulsoryFields' in compulsoryFieldResponse.keys():
      fields=compulsoryFieldResponse['compulsoryFields']
      if 'name' in fields:
        fields.remove('name')
      if 'company' in fields:
        fields.remove('company')
      if len(fields)>0:
        fieldsRequired=[]
        for field in fields:
          fieldsRequired.append([field,field,'text',True])
        responseObject['fields']=fieldsRequired
        return json.dumps(responseObject)
  qualified = salesRep.score(leadId)
  if qualified:
    print id, leadId
    url = config['BASE_URL'] + '/scribeSchedule/'+str(id)+'/'+str(leadId)
    responseObject['url']=url
    print url
    return json.dumps(responseObject)
  else:
    responseObject['submit'] = ['Submit', 'submit', True]
    return json.dumps(responseObject)

#POST https://www.tryscribe.com/scribeSchedule/<salesRep.id>/<lead.id> with phone, callTime to schedule a call between the 2
@web2lead.route('/scribeSchedule/<id>/<leadId>',methods=['GET','POST'])
@csrf.exempt
@cross_origin()
def scribeSchedule(id,leadId,month=datetime.today().month+1):
  salesRep = db.session.query(sales_rep).filter_by(id=id).first()
  print salesRep
  if request.method=='POST':
    try:
      lead = db.session.query(leads).filter_by(id=leadId).first()
      data = json.loads(request.data)
      print data
      if 'callTime' in data.keys():
        lead.callTime = data['callTime']
        lead.phone = data['phone']
        db.session.add(lead)
        db.session.commit()
        scheduleCall(salesRep,lead,timezone="utc")
      responseObject={}
      responseObject['submit'] = ['Submit', 'submit', True]
      return json.dumps(responseObject)
    except Exception as e:
      return {}
  else:
    responseObject={'id':id,'leadId':leadId}
    responseObject['freeSlots']=getNextWeekFreeSlots(salesRep,month)
    return json.dumps(responseObject)

@web2lead.route('/scribeForm/<id>', methods=["GET", "POST"])
@csrf.exempt
def scribeForm(id):
  action='/scribeFormPost1/'+id #config['BASE_URL']+
  return render_template('web2lead/scribeForm.html', action=action)

@web2lead.route('/getEvents/<id>', methods=['GET','POST'])
@csrf.exempt
@cross_origin()
def getEvents(id):
  salesRep = db.session.query(sales_rep).filter_by(id=id).first()
  print salesRep
  return json.dumps(getEventsFromCalendars(salesRep))

@web2lead.route('/createEvent/<id>/<leadId>', methods=['GET','POST'])
@csrf.exempt
@cross_origin()
def createEvents(id,leadId):
  salesRep = db.session.query(sales_rep).filter_by(id=id).first()
  lead = db.session.query(leads).filter_by(id=leadId).first()
  data = json.loads(request.data)
  print data
  lead.callTime = data['start']
  print lead.callTime
  db.session.add(lead)
  db.session.commit()
  return json.dumps(scheduleCall(salesRep, lead))

@web2lead.route("/modalTest", methods=["GET","POST"])
def modalTest():
  return render_template('web2lead/modalTest.html')