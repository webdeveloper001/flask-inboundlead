from flask_restful import Resource, Api
from app import app, db
from models import *
api = Api(app)
from assistantAIfunctions import raiseError, ifNotNone
from datetime import datetime



def getEventsFromCalendars(salesRep):

  response = {
    'dayStart' : [int(salesRep.workHours['dayStart']['hour']), int(salesRep.workHours['dayStart']['minute'])],
    'dayEnd' : [int(salesRep.workHours['dayEnd']['hour']), int(salesRep.workHours['dayEnd']['minute'])],
    'callDuration' : int(salesRep.callDuration),
    'weekend' : [1, 7],
    'mergedEvents' : []
  }

  accounts=salesRep.connectedAccounts

  for email,value in accounts.iteritems():
    try:
      creds = db.session.query(gCredentials).filter_by(email=email).first()
      credential = OAuth2Credentials.from_json(creds.credentials)
      http = credential.authorize(httplib2.Http())
      service = discovery.build('calendar', 'v3', http=http)
      now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
      print now
      eventsResult = service.events().list(calendarId='primary', timeMin=now).execute()
      events = eventsResult.get('items', [])
      response['mergedEvents'].append(events)
      response['mergedEvents'] = flatten(response['mergedEvents'])
    except Exception as e:
      print e
  print response
  return response

def getSummary(salesRep, lead):
  try:
    print lead
    leadName = lead.email
    repName = salesRep.email
    if salesRep.firstName is not None:
      repName = salesRep.firstName.title()
      if salesRep.company is not None:
        repName = repName + ' (' + salesRep.company.title() + ') '
    if lead.firstName is not None:
      leadName = lead.firstName.title()
    return leadName + '<>' + repName + " Introduction Call"
  except Exception as e:
    raiseError("callSummaryError: " + repr(e))
    return "Introduction Call"

def scheduleCall(salesRep, lead, otherAttendeeEmails=None, timezone="pst"):
  print lead
  service = salesRep.getServices()['calendar']
  if lead.callTime is None:
    return
  summary = getSummary(salesRep,lead)
  print summary
  try:
    startTime = arrow.get(lead.callTime).datetime  # dateutil.parser.parse(lead.callTime)
    #if timezone=="utc":
    startTime=startTime+timedelta(hours=7) #because your event is in los_angeles timezone
    print startTime
    endTime = startTime + timedelta(minutes=int(salesRep.callDuration))
    attendees = [{'email': lead.email}, {'email': salesRep.email}]
    if otherAttendeeEmails is not None:
      for attendeeEmail in otherAttendeeEmails:
        attendees.append({'email': attendeeEmail})
    event = {
      'summary': summary,
      'description': "contact number: " + ifNotNone(lead.phone),
      'start': {'dateTime': startTime.isoformat(), 'timeZone': 'America/Los_Angeles'},
      'end': {'dateTime': endTime.isoformat(), 'timeZone': 'America/Los_Angeles'},
      'attendees': attendees,
      'organisers': {'email': salesRep.email},
    }
    print event
    calendarEvent = service.events().insert(calendarId='primary', body=event, sendNotifications=True).execute()
    if not calendarEvent:
      raiseError('Error scheduling call' + lead.email + '<>' + salesRep.email)
      return
    lead.status = constants.HOT
    db.session.add(salesRep)
    db.session.add(lead)
    db.session.commit()
    return
  except Exception as e:
    raiseError("schedulingError: " + repr(e) + "for salesRep: " + salesRep.email)
    return

def flatten(S):
  if S == []:
    return S
  if isinstance(S[0], list):
    return flatten(S[0]) + flatten(S[1:])
  return S[:1] + flatten(S[1:])

def getCalendarList(email):
  creds = db.session.query(gCredentials).filter_by(email=email).first()
  credential = OAuth2Credentials.from_json(creds.credentials)
  http = credential.authorize(httplib2.Http())
  service = discovery.build('calendar', 'v3', http=http)
  page_token = None
  calendarList = {}
  while True:
    calendar_list = service.calendarList().list(pageToken=page_token).execute()
    for calendar_list_entry in calendar_list['items']:
      calendarList[calendar_list_entry['id']] = calendar_list_entry['summary']
    page_token = calendar_list.get('nextPageToken')
    if not page_token:
      break
  return calendarList
'''
class GetEvents(Resource):
  def get(self,id):
    salesRep = db.session.query(sales_rep).filter_by(id=id).first()
    return getEventsFromCalendars(salesRep), 200, {'Access-Control-Allow-Origin': '*'}

api.add_resource(GetEvents, '/getEvents/<id>')

class CreateEvent(Resource):
  def get(self,salesRepId,leadId):
    salesRep=db.session.query(sales_rep).filter_by(id=salesRepId).first()
    lead=db.session.query(leads).filter_by(id=leadId).first()
    return scheduleCall(salesRep, lead), 201, {'Access-Control-Allow-Origin': '*'}

api.add_resource(CreateEvent, '/createEvent/<salesRepId>/<leadId>')
'''

'''Backward compatibility code. tbd '''
def getNextWeekFreeSlots(salesRep, month):  # slots for next 15 days wit 15 min gap
  try:
    startTime = datetime.now() + timedelta(days=1)
    monthEnd = datetime(datetime.today().year, month + 1, 1) - timedelta(days=1)
    endTime = datetime.combine(monthEnd, datetime.min.time())
    startTime = startTime.replace(hour=int(salesRep.workHours['dayStart']['hour']),
                                  minute=int(salesRep.workHours['dayStart']['minute']), second=0)
    endTime = endTime.replace(hour=int(salesRep.workHours['dayEnd']['hour']), minute=int(salesRep.workHours['dayEnd']['minute']),
                              second=0)
    d = startTime
    times = []
    weekend = set([5, 6])
    # checkingFreeBusy needs merge slot
    while d < endTime:
      if d.weekday() not in weekend:
        t = d
        while t < d.replace(hour=int(salesRep.workHours['dayEnd']['hour']), minute=int(salesRep.workHours['dayEnd']['minute']),
                            second=0):
          times.append(t.isoformat())
          t = t + timedelta(minutes=salesRep.callDuration)
      d += timedelta(days=1)
    return times
  except Exception as e:
    raiseError("freeSlotsError: "+repr(e)+" for salesRep: "+salesRep.email)
    return []

class addAccount(Resource):
  def addAccount(self,id):
    salesRep = db.session.query(sales_rep).filter_by(id=id).first()

