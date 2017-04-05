from sqlalchemy.dialects.postgresql import JSON, JSON
from sqlalchemy import ForeignKey, CheckConstraint, TEXT, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from datetime import datetime, timedelta
import pytz, json
from googleAppFunctions import *
from assistantAIfunctions import *
from app import db, config
import constants
import email, arrow
from oauth2client.client import OAuth2Credentials
import dateutil.parser

class betaUsers(db.Model):
  __tablename__ = 'betaUsers'

  id = db.Column(db.Integer, primary_key=True)
  email = db.Column(db.String(120))

  def __init__(self, email=None):
    self.email = email

  def __repr__(self):
    return "%d/%s" % (self.id, self.email)


class sales_rep(db.Model):
  __tablename__ = 'sales_rep'

  id = db.Column(db.Integer, primary_key=True)
  email = db.Column(db.String(120), unique=True)
  firstName = db.Column(db.String(120))
  company = db.Column(db.String(120))
  signature = db.Column(TEXT)
  latestHistoryId = db.Column(db.String(120))
  created_on = db.Column(db.DateTime)
  templates = db.Column(JSON)
  qualify = db.Column(JSON)
  compulsoryFields = db.Column(TEXT)
  spreadSheetId = db.Column(db.String(120))
  webHookUrl = db.Column(db.String(120))
  totalEmailsSent = db.Column(db.Integer, default=0)
  totalEmailsReceived = db.Column(db.Integer, default=0)
  avgResponseTime = db.Column(db.FLOAT, default=0.0) #in seconds
  totalEmailsReviewedByHumans = db.Column(db.Integer, default=0)
  pollingError = db.Column(db.Integer, default=0)
  monitorEmail = db.Column(db.Boolean, default=False)
  workHours = db.Column(JSON)
  callDuration = db.Column(db.Integer, default=30)
  connectedAccounts=db.Column(JSON)
  leads=db.relationship('leads',backref=db.backref('salesRep', single_parent=True), cascade="all, delete-orphan", lazy='dynamic', order_by='desc(leads.id)')

  def __init__(self, email=None, firstName=None, company=None, signature=None,
               latestHistoryId=None, templates=None):
    workHours={"dayEnd":{"minute":"0","hour":"17"},"dayStart":{"minute":"0","hour":"9"}}
    self.email = email
    self.firstName = firstName
    self.company = company
    self.signature = signature
    self.latestHistoryId = latestHistoryId
    self.created_on = datetime.now()
    self.templates = templates
    self.workHours = workHours
    self.compulsoryFields = "email,name,company"
    self.spreadSheetId = ""
    self.connectedAccounts = {email:{'workHours':workHours,'calendars':''}}

  @hybrid_property
  def avgLeadCallConversion(self):
    if len(self.leads.all())==0:
      return 0.0
    else:
      convertedLeads=self.leads.filter_by(status=constants.HOT).all()
      return round(len(convertedLeads)*1.0/len(self.leads.all()),2)

  @hybrid_property
  def totalCallsScheduled(self):
    if len(self.leads.all())==0:
      return 0
    else:
      convertedLeads=self.leads.filter(leads.status==constants.HOT).all()
      return len(convertedLeads)

  def setIntegrations(self,key,value):
    integrations=self.integrations
    integrations[key]=value
    db.session.query(sales_rep).filter_by(id=self.id).update({"integrations": integrations})
    db.session.add(self)
    db.session.commit()
    return

  def updateAccounts(self,email,type="add",value=None):
    try:
      accounts = self.connectedAccounts
      if accounts is None:
        accounts={}
      if type=='add':
        accounts[email]=value
        print value
      else:
        del accounts[email]
      db.session.query(sales_rep).filter_by(id=self.id).update({"connectedAccounts":accounts})
      db.session.add(self)
      db.session.commit()
    except Exception as e:
      print e
    return

  def getServices(self):
    creds = db.session.query(gCredentials).filter_by(email=self.email).first()
    credentials = OAuth2Credentials.from_json(creds.credentials)
    http = credentials.authorize(httplib2.Http())
    if credentials.access_token_expired:
      credentials.refresh(http)
    services = {}
    if self.monitorEmail:
      services['gmail'] = discovery.build('gmail', 'v1', http=http)
    services['calendar'] = discovery.build('calendar', 'v3', http=http)
    services['sheets'] = discovery.build('sheets', 'v4', http=http)
    services['drive'] = discovery.build('drive', 'v3', http=http)
    return services

  def watchAndStop(self):
    gmail = self.getServices()['gmail']
    subscriptionRequest = {
      'labelIds': ['INBOX'],
      'topicName': 'projects/rapid-clover-160304/topics/representativ'
    }
    self.latestHistoryId = gmail.users().watch(userId=self.email, body=subscriptionRequest).execute()['historyId']
    gmail.users().stop(userId=self.email).execute()
    db.session.add(self)
    db.session.flush()
    return

  # ----------------------------------------------------------------------------#
  # lead qualification
  # ----------------------------------------------------------------------------#

  def qualifyCompulsoryFields(self,leadInfo):
    compulsoryFields=[]
    for field in self.compulsoryFields.split(','):
      if field not in leadInfo.keys():
        compulsoryFields.append(field)
      elif leadInfo[field] is None or leadInfo[field] is "":
        compulsoryFields.append(field)
    if len(compulsoryFields)>0:
      return {'compulsoryFields':compulsoryFields}
    else:
      return {}

  def score(self,leadId):
    #return True
    score=0 #score from 0 to xx and its not averaged
    lead=db.session.query(leads).filter_by(id=leadId).first()
    entities=lead.entities
    print entities
    print self.qualify
    if self.qualify is None:
      return True
    for field,valueDict in self.qualify.items(): #Fields will have scores -1,0,1,10
      if field not in entities.keys():
        raiseError("entity: "+field+" not asked for lead with id: " + str(lead.id))
        continue
      leadFieldValue=entities[field]
      print field, leadFieldValue
      if field=="#Sales representatives in your team" or field=="":
        try:
          print "LEADFIELDVALUE"
          if int(leadFieldValue)<3:
            print leadFieldValue
            score+=-2
        except Exception as e:
          score += -2
      elif field=="company":
        if leadFieldValue is None or leadFieldValue=="":
          score += -2
      elif leadFieldValue in valueDict.keys():
        score+=valueDict[leadFieldValue]
      print score
    lead.score=score
    db.session.add(lead)
    db.session.commit()
    print "SCORE"
    print score
    #grade=self.grade(lead)
    return score>-3 #self.qualificationThreshold

  #qualify={"company":{"":-1,None:-1},"#Sales representatives in your team":{"0":-1,"1":-1}}
  def postLeadToEndpoints(self, leadInfo):
    '''leadInfo.keys()='companyPhoneNumbers','sector','raised','twitter','site','linkedin','timezone','seniority','companyUrl',
        'title','companyEmails','foundedYear','state','location','companyDescription','type','email','bio','tags','company','companyLocation',
        'facebook','industryGroup','github','name','gender','employees','subIndustry','tech','country','marketCap','industry'
    '''
    print leadInfo
    try:
      values = [[getLeadEntityValue('email', leadInfo), getLeadEntityValue('name', leadInfo),
                 getLeadEntityValue('gender', leadInfo), getLeadEntityValue('company', leadInfo),
                 getLeadEntityValue('title', leadInfo), getLeadEntityValue('seniority', leadInfo),
                 getLeadEntityValue('location', leadInfo), getLeadEntityValue('linkedin', leadInfo),
                 getLeadEntityValue('companyDescription', leadInfo), getLeadEntityValue('sector', leadInfo),
                 getLeadEntityValue('type', leadInfo),
                 getLeadEntityValue('Industry', leadInfo), getLeadEntityValue('subIndustry', leadInfo),
                 getLeadEntityValue('sector', leadInfo), getLeadEntityValue('foundedYear', leadInfo),
                 getLeadEntityValue('employees', leadInfo),
                 getLeadEntityValue('tech', leadInfo), getLeadEntityValue('marketCap', leadInfo),
                 getLeadEntityValue('raised', leadInfo), getLeadEntityValue('companyUrl', leadInfo),
                 getLeadEntityValue('companyEmails', leadInfo)]]
      print values
      ss = self.spreadSheetId
      body = {'values': values}
      defaultRep = db.session.query(sales_rep).filter_by(id=config['DEFAULT_SALESREP_ID']).first()
      print ss
      writeToClientSpreadSheet(body, ss, defaultRep)
      print self.webHookUrl
      if self.webHookUrl is not None and self.webHookUrl != "":
        url = self.webHookUrl
        print "URL>>>", url
        data = leadInfo
        requests.post(url, data=data)
    except Exception as e:
      print e
    return
  # ----------------------------------------------------------------------------#
  # Process salesRep inbox for new lead emails
  # ----------------------------------------------------------------------------#

  def getUpdatesSinceGivenId(self):
    try:
      service = self.getServices()['gmail']
      history = (service.users().history().list(userId=self.email, startHistoryId=self.latestHistoryId).execute())
      updates = history['history'] if 'history' in history else []
      while 'nextPageToken' in history:
        page_token = history['nextPageToken']
        history = (service.users().history().list(userId=self.email, startHistoryId=self.latestHistoryId,
                                                  pageToken=page_token).execute())
        updates.extend(history['history'])
      self.watchAndStop()
    except errors.HttpError, error:
      raiseError("gettingNewUpdates: " + repr(error) + " for salesRep: " + self.email)
      updates = []
    return updates

  def getNewAssistantEmails(self, updates=None):
    if not self.monitorEmail:
      return
    processedThreads = []
    if updates is None:
      updates = self.getUpdatesSinceGivenId()
    try:
      for update in updates:
        if 'messagesAdded' not in update.keys():
          continue
        for newMessage in update['messagesAdded']:
          if 'labelIds' in newMessage['message'].keys() and 'INBOX' in newMessage['message']['labelIds']:
            [msg_id, thread_id] = [newMessage['message']['id'], newMessage['message']['threadId']]
            uniqueThread = thread_id + " % " + msg_id
            if uniqueThread not in processedThreads:
              processedThreads.append(uniqueThread)
              self.processNewInboundMessage(thread_id, msg_id)
    except Exception as e:
      raiseError("gettingNewEmails for salesRep: "+self.email)
    return

  def processNewInboundMessage(self, thread_id, msg_id):
    try:
      service = self.getServices()['gmail']
      message = service.users().messages().get(userId=self.email, id=msg_id, format='raw').execute()
      msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
      mime_msg = email.message_from_string(msg_str)
      processedEmail = processMimeMsg(mime_msg, msg_id, thread_id)
      print processedEmail
      thread=db.session.query(leadThreads).filter_by(gThreadId=thread_id).first() #there can be many here
      if thread is not None:
        print thread
        lead = self.leads.filter_by(id=thread.leadId).first()
        print lead
      else:
        lead=leads(salesRepId=self.id)
        db.session.add(lead)
        lead.thread=leadThreads(leadId=lead.id,gThreadId=thread_id)
        db.session.commit()
      print lead
      lead.thread.setConversation(processedEmail['body'])
      lead.thread.setSubject(processedEmail['subject'])
      lead.setEmail(processedEmail['from'])
      lead.thread.setMsgId(processedEmail['msgId'], 'reply')
      lead.thread.setReview("New received email")
      if 'cc' in processedEmail.keys():
        lead.thread.setParticipants(processedEmail['cc'])
      db.session.add(lead)
      db.session.add(self)
      db.session.commit()
      try:
        data = {"sender": {"handle": processedEmail['from']}, "subject": processedEmail['subject'],
              "body": processedEmail['body'], "metadata": {"thread_ref": lead.thread.threadRef}}
        r = requests.post(url=config['frontFwdUrl'], headers=config['frontHeaders'], data=json.dumps(data))
        print r.json()
      except Exception as e:
        raiseError("frontFwdError")
    except Exception as e:
      raiseError("processingInboundMessage" + repr(e) + " for salesRep: " + self.email)
    return

  # ----------------------------------------------------------------------------#
  # Send Emails to leads
  # ----------------------------------------------------------------------------#

  def sendMessage(self, to, subject, messageText, cc=None, thread_id=None):
    if self.firstName is None:
      fromEmail=self.email
    else:
      fromEmail = self.firstName+'<'+self.email+'>'
    messageToBeSent = CreateMessage(fromEmail, to, subject, messageText, cc, thread_id)
    service = self.getServices()['gmail']
    message = (service.users().messages().send(userId=self.email, body=messageToBeSent).execute())
    return message

  def sendReplyEmail(self, lead, mailText, includeParticipants=False):
    if not self.monitorEmail:
      return
    try:
      if mailText is None:
        raiseError("Empty message Text for lead: " + lead.email + " having salesRep: " + self.email)
        return
      if lead.thread is None:
        raiseError("led has no thread to reply to")
        return
      if lead.thread.checkForUpdateIfAny():
        lead.thread.setReview("Email received on thread just before reply")
        return
      lead.status = constants.WARM
      db.session.add(lead)
      self.sendEmailAndUpdateFields(lead, mailText, includeParticipants)
    except Exception as error:
      raiseError("sendingReply: " + str(lead.email) + " error: " + repr(error))
    db.session.commit()
    return

  def sendTemplateEmail(self, lead, workflow, sequence):
    if not self.monitorEmail:
      return
    if workflow in self.templates.keys() and sequence in self.templates[workflow].keys():
      try:
        messagePersonalized=personalize(lead, self.templates[workflow][sequence])
        if lead.thread is None:
          print lead.id
          lead.thread = leadThreads(leadId=lead.id)
          db.session.add(lead)
          db.session.commit()
        print lead.thread
        if lead.thread.subject is None and 'onboardingSubject' in self.templates[workflow].keys():
          lead.thread.subject=personalize(lead, self.templates[workflow]['onboardingSubject'])
          db.session.add(lead)
          db.session.commit()
      except Exception as e:
        raiseError("messagePersonalizationError:" + repr(e) +" salesRep: " + self.email +" workflow:" + workflow +" sequence:" + sequence +" for lead:" + lead.email)
        return
      self.sendEmailAndUpdateFields(lead, messagePersonalized)
    else:
      raiseError("doesn't exist workflow: "+workflow+" sequence: "+sequence+" for salesRep:"+self.email)
    return

  def onboardLead(self, lead, subject=None, mailText=None):
    if not self.monitorEmail:
      return
    try:
      if lead.thread.gThreadId is not None:
        raiseError("onboardingLead: " + str(lead.email) + " error: " + "No subject or lead gThreadId exists")
        return
      if mailText is not None and subject is not None:
        messagePersonalized = personalize(lead, mailText)
        lead.thread = leadThreads(leadId=lead.id)
        lead.thread.subject=personalize(lead,subject)
        db.session.add(lead)
        db.session.commit()
        self.sendEmailAndUpdateFields(lead, messagePersonalized)
      else:
        print "first"
        self.sendTemplateEmail(lead=lead, workflow="common", sequence="first")
    except Exception as error:
      raiseError("onboardingLead: " + str(lead.email) + " error: " + repr(error))
      db.session.commit()
    return

  def followUpColdLeads(self):  # drip emails
    if not self.monitorEmail:
      return
    leadList = self.leads.filter_by(status=constants.COLD).all()
    for lead in leadList:
      if lead.status != constants.COLD:
        continue
      if lead.thread is None:
        self.onboardLead(lead)
        return
      if lead.thread.receivedEmailCount > 0:
        raiseError("lead status cold despite reply for lead: " + lead.email)
        return
      try:
        gapTime = datetime.now() - timedelta(days=constants.DRIP_GAP_DAYS)
        if lead.thread.lastEmailSentTime < gapTime and not lead.thread.checkForUpdateIfAny():
          messagePersonalized = personalize(lead, constants.DRIP_TEMPLATE[lead.sentEmailCount])
          self.sendEmailAndUpdateFields(lead,messagePersonalized)
      except Exception as error:
        raiseError("processingColdLead: " + str(lead.email) + " error: " + repr(error))
        db.session.commit()
    return

  def sendEmailAndUpdateFields(self, lead, mailText, includeParticipants=False):
    try:
      thread = lead.thread
      messageText = appendSignature(self.signature, mailText)
      cc=None
      if includeParticipants:
        cc=thread.latestParticipants
      message = self.sendMessage(to=lead.email, subject=thread.subject, messageText=messageText, cc=cc, thread_id=thread.gThreadId)
      if message is not None:
        if thread.gThreadId is None:
          thread.gThreadId = message['threadId']
          thread.setConversation(ifNotNone(messageText))
          thread.setMsgId(message['id'], 'sent')
          thread.setReview("mail sent", False)
          db.session.add(lead)
          db.session.commit()
    except Exception as e:
      raiseError("SendEmailAndUpdateFields error: " + repr(e) +" salesRep: " + self.email +" lead:" + lead.email)
    return


  def __repr__(self):
    return "%d/%s" % (self.id, self.email)

  def is_authenticated(self):
    return self.authenticated

  def is_active(self):
    return self.active

  def get_id(self):
    return unicode(self.id)

  def is_anonymous(self):
    return False


class leads(db.Model):
  __tablename__ = 'leads'
  id = db.Column(db.Integer, primary_key=True)
  salesRepId = db.Column(db.Integer, ForeignKey("sales_rep.id"))
  email = db.Column(db.String(120))
  firstName = db.Column(db.String(120))
  company = db.Column(db.String(120))
  status = db.Column(db.String(120), default=constants.COLD)
  phone = db.Column(db.String(120))
  callTime = db.Column(db.DateTime)
  interest = db.Column(db.Integer)
  entities = db.Column(JSON)
  thread = db.relationship('leadThreads', uselist=False,backref=db.backref('lead',uselist=False, cascade="all, delete-orphan", single_parent=True))
  UniqueConstraint('salesRepId', 'thread.gThreadId', name='unique1')

  def __init__(self, salesRepId=salesRepId, email=None, firstName=None, company=None, status=constants.COLD,
               phone=None, callTime=None, interest=0, entities=None):
    self.email = email
    self.salesRepId = salesRepId
    self.firstName = firstName
    self.company = company
    self.status = status
    self.phone = phone
    self.callTime = callTime
    self.interest = interest
    self.entities = entities

  def setPhone(self, phone):
    if phone is not None and self.phone is None:
      self.phone = phone
      self.interest = 1
    elif phone is not None and self.phone is not None:
      self.thread.setReview("multiple phone numbers")
    return

  def setCallTime(self, callTime):
    if callTime is not None and self.callTime is None:
      self.callTime = callTime
      self.interest = 1
    elif callTime is not None and self.callTime is not None:
      self.thread.setReview("multiple call time requests")
    return

  def setInterest(self, interest):
    if interest > 0 and self.interest <= interest:
      self.interest = interest
    elif interest < self.interest:
      self.thread.setReview("reduction in interest")
    return

  def updateEntities(self, leadInfo):
    entities = self.entities
    for k,v in leadInfo.iteritems():
      if v is not None and v!="":
        entities[k]=v
    db.session.query(leads).filter_by(id=self.id).update({"entities": entities})
    db.session.add(self)
    db.session.commit()
    return

  def updateScheduleEntities(self, entityStatus):
    self.setInterest(entityStatus['interest'])
    self.setPhone(entityStatus['phone'])
    self.setCallTime(entityStatus['callTime'])
    if entityStatus['review']:
      self.thread.setReview("review email entities")
    db.session.add(self)
    db.session.commit()
    return

  def setEmail(self, leadEmail):
    if leadEmail is not None:
      self.email=leadEmail
      db.session.add(self)
      db.session.commit()
    return

  def __repr__(self):
    return "%d/%s/%s" % (self.id, self.email, self.salesRep)


#each thread has 1 active lead and each lead has 1 active thread. So, 1 to 1 mapping. Each salesRep has many leads 1-many
class leadThreads(db.Model):
  __tablename__ = 'lead_threads'

  id = db.Column(db.Integer, primary_key=True)
  leadId = db.Column(db.Integer, ForeignKey("leads.id"))
  gThreadId = db.Column(db.String(120))
  subject = db.Column(TEXT)
  review = db.Column(db.Boolean, default=False)
  reviewReason = db.Column(TEXT)
  msgIds = db.Column(TEXT)
  latestReply = db.Column(TEXT)
  latestParticipants = db.Column(TEXT)
  conversationText = db.Column(TEXT)
  sentEmailCount = db.Column(db.Integer, default=0)
  receivedEmailCount = db.Column(db.Integer, default=0)
  lastEmailSentTime = db.Column(db.DateTime)
  lastEmailReceivedTime = db.Column(db.DateTime)
  frontConversationId = db.Column(db.String(120))

  def __init__(self, email = None, leadId = None, review=False, reviewReason=None, subject=None, gThreadId=None,
               msgIds=None, sentEmailCount=0, receivedEmailCount=0, lastEmailSentTime=None, lastEmailReceivedTime=None):
    self.email = email
    self.leadId = leadId
    self.review = review
    self.reviewReason = reviewReason
    self.subject = subject
    self.gThreadId = gThreadId
    self.msgIds = msgIds
    self.sentEmailCount = sentEmailCount
    self.receivedEmailCount = receivedEmailCount
    self.lastEmailSentTime = lastEmailSentTime
    self.lastEmailReceivedTime = lastEmailReceivedTime

  @hybrid_property
  def threadRef(self):
    return self.gThreadId + "%" + self.lead.salesRep.email

  def checkForUpdateIfAny(self):  # just checking for updates for now
    service = self.lead.salesRep.getServices()['gmail']
    gthread = service.users().threads().get(userId=self.lead.salesRep.email, id=self.gThreadId).execute()
    if len(gthread['messages']) != self.sentEmailCount + self.receivedEmailCount:
      return True
    return False

  def setMsgId(self, msgId, type):
    if self.msgIds is None:
      self.msgIds = msgId
    else:
      self.msgIds = ifNotNone(self.msgIds) + "\n" + msgId
    if type == 'reply':
      if self.lead.salesRep.totalEmailsReceived is None:
        self.lead.salesRep.totalEmailsReceived = 1
      else:
        self.lead.salesRep.totalEmailsReceived += 1
      self.lastEmailReceivedTime = datetime.now()
      if self.receivedEmailCount is None:
        self.receivedEmailCount = 1
      else:
        self.receivedEmailCount += 1
        self.msgIds = ifNotNone(self.msgIds) + "\n" + msgId
    if type == 'sent':
      self.lastEmailSentTime = datetime.now()
      if self.lead.salesRep.totalEmailsReceived is None:
        self.lead.salesRep.totalEmailsSent = 1
      else:
        self.lead.salesRep.totalEmailsSent += 1
      try:
        if self.lastEmailReceivedTime is not None:
          self.lead.salesRep.avgResponseTime= (self.lead.salesRep.avgResponseTime*self.lead.salesRep.totalEmailsSent +
                                     (datetime.now()-self.lastEmailReceivedTime).seconds/60.0)/(self.lead.salesRep.totalEmailsSent+1)
      except Exception as e:
        raiseError("avgResponseTime Update Error: "+repr(e))
      if self.sentEmailCount is None:
        self.sentEmailCount = 1
      else:
        self.sentEmailCount += 1
    db.session.add(self)
    db.session.commit()
    return

  def setConversation(self, latestReply):
    if latestReply is not None and self.conversationText is None:
      self.latestReply = latestReply
      self.conversationText = latestReply
    elif latestReply is not None and self.latestReply is not None:
      self.latestReply = latestReply
      self.conversationText += "\n----------------\n" + latestReply
    return

  def setReview(self, reason, review=True):
    self.review = review
    if review:
      self.reviewReason = "REASON: " + ifNotNone(reason) + " latestReply: " + ifNotNone(self.latestReply)
      self.sendForReview()
    return

  def setSubject(self, subject):
    if subject is None:
      raiseError("subject is None")
    else:
      self.subject = subject
    return

  def setParticipants(self,participants=None):
    if participants is not None:
      self.latestParticipants = ",".join(participants)
    return

  def sendForReview(self):
    baseUrl = config.BASE_URL + '/agent/review'
    if self.reviewReason is None:
      self.reviewReason = ""
    html = "Reason: " + self.reviewReason + "\n reviewUrl: " + baseUrl
    print html
    sendMail('sachin@representativ.com', 'support@tryscribe.com', "lead: "+self.lead.email+"salesRep: "+self.lead.salesRep.email, html)
    sendMail('rutika@tryscribe.com', 'support@tryscribe.com', "lead: "+self.lead.email+"salesRep: "+self.lead.salesRep.email, html)
    sendMail('urgentreview@scribetechnologies.mailclark.ai', 'support@tryscribe.com', "lead: "+self.lead.email+"salesRep: "+self.lead.salesRep.email, html)
    return

  def __repr__(self):
    return "%d/%d/%s,%r" % (self.id, self.leadId, self.gThreadId, self.review)



class gCredentials(db.Model):
  __tablename__ = 'gCredentials'

  id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
  email = db.Column(db.String(120), unique=True)
  credentials = db.Column(JSON)
  credType = db.Column(db.String(120))

  def __init__(self, email=None, credentials=None, credType="salesRep"):
    self.email = email
    self.credentials = credentials
    self.credType = credType

  def __repr__(self):
    return "%d/%s/%s" % (self.id, self.email, self.credType)


'''

class message(db.Model):
  __tablename__ = 'lead_messages'

  id = db.Column(db.Integer, primary_key=True)
  threadId = db.Column(db.String(120),ForeignKey("lead_threads.threadId"))
  messageId = db.Column(db.String(120))
  participantList = db.Column(TEXT) #comma separated emails
  mailText = db.Column(TEXT)
  created_on = db.Column(db.DateTime)
  UniqueConstraint('messageId', 'threadId', name='unique2')

  def __init__(self, threadId=None, messageId=None, subject=None, participantList=None, mailText=None):
    self.threadId = threadId
    self.messageId = messageId
    self.subject = subject
    self.participantList = participantList
    self.mailText = mailText
    self.created_on = datetime.now()

  def __repr__(self):
    return "%d/%s/%s/%s" % (self.id, self.messageId, self.threadId,self.subject)


class agent(db.Model):
  __tablename__ = 'agent'

  id = db.Column(db.Integer, primary_key=True)
  email=db.Column(db.String(120),default="agent")
  password=db.Column(db.String(120),default="agent")
  created_on = db.Column(db.DateTime)

  def __init__(self, salesRep=None, threadId=None, subject=None, fromEmail=None, leadReply=None,
               entityValues=None, suggestedReply=None):
      self.salesRep = salesRep
      self.threadId = threadId
      self.subject = subject
      self.fromEmail = fromEmail
      self.leadReply = leadReply
      self.entityValues = entityValues
      self.suggestedReply = suggestedReply
      self.created_on = datetime.now()

  def __repr__(self):
      return "%d/%s/%s" % (self.id, self.salesRep, self.leadReply)

  def get_id(self):
      return unicode(self.id)
'''
# Create tables.
# db.create_all()
# Base.metadata.create_all(bind=engine)
