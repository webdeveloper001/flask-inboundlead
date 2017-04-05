from flask import Blueprint, render_template
from flask_cors import CORS, cross_origin

from assistantAIfunctions import *
from app import csrf, config
from models import sales_rep, leads
from datetime import datetime, timedelta
from scheduler import *
import json

intercom2lead = Blueprint('intercom2lead', __name__,template_folder='templates',static_folder='static')

cors = CORS(intercom2lead)
#----------------------------------------------------------------------------#
# web2lead specific handlers
# ----------------------------------------------------------------------------#

@intercom2lead.route('/iQualifyEmail/<id>',methods=['GET','POST'])
@csrf.exempt
@cross_origin()
def iQualifyEmail(id):
  salesRep = db.session.query(sales_rep).filter_by(id=id).first()
  data = json.loads(request.data)
  email = data['email']
  leadInfo = getLeadInfo(email)
  lead = db.session.query(leads).filter_by(email=email,salesRepId=salesRep.id).first()
  if lead is None:
    lead = leads(salesRepId=salesRep.id, firstName=leadInfo['name'], company=leadInfo['company'], email=email,
               entities=leadInfo)
    db.session.add(lead)
    db.session.commit()
  else:
    lead.updateEntities(leadInfo)
  leadId = lead.id
  compulsoryFieldResponse = salesRep.qualifyCompulsoryFields(lead.entities)
  responseObject={'type':'thanks','leadId':leadId,'leadName':ifNotNone(lead.firstName)}
  #temp for scribe
  if len(compulsoryFieldResponse)>0:
    responseObject['type']='moreQuestions'
    responseObject['questionFields']=compulsoryFieldResponse['compulsoryFields']
    return json.dumps(responseObject)
  qualified = salesRep.score(leadId)
  salesRep.postLeadToEndpoints(leadInfo)
  if qualified:
    responseObject['type'] = 'schedule'
  return json.dumps(responseObject)

@intercom2lead.route('/iMoreQuestions/<id>/<leadId>',methods=['GET','POST'])
@csrf.exempt
@cross_origin()
def iMoreQuestions(id,leadId):
  salesRep = db.session.query(sales_rep).filter_by(id=id).first()
  lead = db.session.query(leads).filter_by(id=leadId).first()
  data = json.loads(request.data)
  print data
  lead.updateEntities(data)
  responseObject={'type':'thanks','leadId':leadId,'leadName':ifNotNone(lead.firstName)}
  qualified = salesRep.score(leadId)
  print "QUALIFIED"
  print qualified
  salesRep.postLeadToEndpoints(lead.entities)
  if qualified:
    responseObject['type'] = 'schedule'
  return json.dumps(responseObject)

@intercom2lead.route('/iSchedule/<id>/<leadId>',methods=['GET','POST'])
@csrf.exempt
@cross_origin()
def iSchedule(id,leadId,month=datetime.today().month+1):
  salesRep = db.session.query(sales_rep).filter_by(id=id).first()
  if request.method=='POST':
    try:
      lead = db.session.query(leads).filter_by(id=leadId).first()
      data = json.loads(request.data)
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

@intercom2lead.route('/iThanks/<id>/<leadId>',methods=['GET','POST'])
@csrf.exempt
@cross_origin()
def iThanks(id,leadId):
  return render_template('intercom2lead/thanks.html',id=id,leadId=leadId)

@intercom2lead.route('/iAppointment/<id>/<leadId>',methods=['GET','POST'])
@csrf.exempt
@cross_origin()
def iAppointment(id,leadId):
  return render_template('intercom2lead/appointment.html',id=id,leadId=leadId)
