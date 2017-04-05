import os
from app import config
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import quotequail
from html2text import html2text
import talon, constants
from talon import quotations
from werkzeug.utils import secure_filename
talon.init()
import clearbit
from flask import flash, request, url_for, redirect
from flask_mail import Mail, Message
from app import mail, db
from itsdangerous import URLSafeTimedSerializer
import re
from models import *
clearbit.key = config['CLEARBIT_KEY']

ALLOWED_EXTENSIONS = set(['csv'])

# ----------------------------------------------------------------------------#
# web2lead functions
# ----------------------------------------------------------------------------#
def getCode(salesRep):
  code='<script data-uid="'+str(salesRep.id)+'" data-url="'+config['BASE_URL']+'" data-opentype="true" type="text/javascript" src="'+config['BASE_URL']+'"/static/client/dist/clientEmbedCode.bundle.js"></script>"'
  return code

def fieldScore(fieldValueRatings,entities,weight,type):
  if 'field' not in entities.keys():
    return 0
  if type=='boolean': #customer should have a value for this field
    return weight*entities['field']['confidence']
  if type=='multipleChoice': #customer's value is part of a big set of possible values that salesRep has rated
    value=entities['field']['value']
    if value not in fieldValueRatings.keys():
      return 0
    return weight*fieldValueRatings[value]


def createSpreadSheet(email,defaultRep):
  try:
    sheet = defaultRep.getServices()['sheets']
    data = {'properties': {'title': 'Scribe/' + email}}
    newSheet = sheet.spreadsheets().create(body=data).execute()
    id = newSheet['spreadsheetId']
    body = {'values': constants.SPREADSHEET_HEADER}
    result = sheet.spreadsheets().values().append(
      spreadsheetId=id, range='Sheet1!A1:U1',
      valueInputOption='USER_ENTERED', body=body).execute()
    domain_permission = {
      'type': 'user',
      'role': 'writer',
      'emailAddress': email,
    }
    drive = defaultRep.getServices()['drive']
    req = drive.permissions().create(
      fileId=id,
      body=domain_permission,
      fields="id"
    )
    req.execute()
    return id
    #salesRep=db.session.query(sales_rep).filter_by(email).first()
    #salesRep.Integrations['spreadSheetId'] = id
    #db.session.add(salesRep)
    #db.session.commit()
  except Exception as e:
    raiseError("error creating  sheet for user: " + email)
  return ""

def writeToClientSpreadSheet(body, ss, defaultRep):
  try:
    sheet = defaultRep.getServices()['sheets']
    result = sheet.spreadsheets().values().append(
      spreadsheetId=ss, range='Sheet1!A1:U1',
      valueInputOption='USER_ENTERED', body=body).execute()
  except Exception as e:
    print "Error: "+repr(e)
    raiseError("error writing to sheet: "+str(ss))
  return

def getLeadEntityValue(field, leadInfo):
  if field in leadInfo.keys():
    return leadInfo[field]
  return ""

def getLeadInfo(email,company=None,name=None):
  '''persons=['twitter','site','linkedin','employment','id','aboutme','location','emailProvider','email','bio','indexedAt',
  'facebook','fuzzy','geo','github','name','gender','googleplus','utcOffset','gravatar','avatar','timeZone']
  company=['domain','twitter','site','linkedin','crunchbase','logo','id','category','geo','foundedYear','location','domainAliases',
 'emailProvider','type','description','tags','indexedAt','metrics','phone','facebook','ticker','name','utcOffset','tech',
 'legalName','timeZone']'''
  leadInfo = {'name': name, 'email': email, 'company': company}
  try:
    response=clearbit.Enrichment.find(email=email,stream=True)
    print response
    if 'person' not in response:
      return leadInfo
    person=response['person']
    leadInfo = {'name':person['name']['givenName'],'email':email,'company':person['employment']['name'],'gender':person['gender'],'state':person['geo']['state'],
            'timezone':person['timeZone'],'seniority':person['employment']['seniority'],'title':person['employment']['title'],
            'bio':person['bio'],'twitter':person['twitter']['handle'],'github':person['github']['handle'],'linkedin':person['linkedin']['handle'],
            'site':person['site'],'facebook':person['facebook']['handle'],'country':person['geo']['country'],'location':person['location'],
            }
    domain=person['employment']['domain']
    if domain is None: #things get messed up here and often you end up getting wrong info
      try:
        approxDomain=company+'.com'
        companyInfo = clearbit.Enrichment.find(domain=approxDomain, stream=True)
      except Exception as e:
        raiseError("no domain for company "+company+" for lead email: "+email)
        return leadInfo
    if domain is not None:
      companyInfo = clearbit.Enrichment.find(domain=domain, stream=True)
      print companyInfo
    if companyInfo == None or 'pending' in companyInfo:
      return leadInfo
    leadCompany = {'company':companyInfo['name'],'tags':companyInfo['tags'],'tech':companyInfo['tech'],'type':companyInfo['type'],'companyLocation':companyInfo['location'],
                   'companyUrl':companyInfo['site']['url'],'companyPhoneNumbers':companyInfo['site']['phoneNumbers'],'companyEmails':companyInfo['site']['emailAddresses'],
                   'foundedYear':companyInfo['foundedYear'],'companyDescription':companyInfo['description'],'industry':companyInfo['category']['industry'],
                   'industryGroup':companyInfo['category']['industryGroup'],'sector':companyInfo['category']['sector'],'subIndustry':companyInfo['category']['subIndustry'],
                   'employees':companyInfo['metrics']['employees'],'raised':companyInfo['metrics']['raised'],'marketCap':companyInfo['metrics']['marketCap'],
                   }
    leadInfo.update(leadCompany)
    return leadInfo
  except Exception as e:
    print e
    return leadInfo
# ----------------------------------------------------------------------------#
# scheduling specific functions
# ----------------------------------------------------------------------------#

def sendMail(to, from_addr, subject, html):
  msg = MIMEMultipart('alternative')
  msg['Subject'] = subject
  msg['From'] = from_addr
  #msg['To'] = ",".join(to)
  msg['To'] = to
  content = MIMEText(html, 'html')
  msg.attach(content)
  s = smtplib.SMTP_SSL(config['MAIL_SERVER'], config['MAIL_PORT'])
  s.ehlo()
  s.login(config['MAIL_USERNAME'], config['MAIL_PASSWORD'])
  s.sendmail(from_addr, to, msg.as_string())
  s.quit()

def raiseError(body):
  sendMail('sachin@tryscribe.com', 'support@tryscribe.com', 'raise error', body)
  return

def ifNotNone(string,title=False):
  if string is None:
    return ""
  if title:
    return string.title()
  return string

def appendSignature(signature, messageText):
  text = ifNotNone(messageText) + "\n\n" + ifNotNone(signature)
  return text

def personalize(lead,text):
  if text is None:
    raiseError("no text")
    return
  try:
    values={'name':ifNotNone(lead.firstName),'company':ifNotNone(lead.company)}
    for x in ['name', 'company']:
      text = text.replace('%%%' + x + '%%%', values[x].strip())
    if '%%%' not in text:
      return text
    else:
      raiseError('personalization error:%%% still exists for lead: ' + lead.firstName)
      raise Exception
  except Exception as e:
    raiseError('personalization error: '+repr(e)+'for lead: '+lead.firstName)
    raise Exception


def processMimeMsg(mime_msg,msg_id,thread_id):
  #parser = MailParser()
  try:
    #parser.parse_from_string(mime_msg)
    #body=parser.body
    messageMainType = mime_msg.get_content_maintype()
    if messageMainType == 'multipart':
      for part in mime_msg.get_payload():
        if part.get_content_maintype() == 'text':
          body=part.get_payload()
    elif messageMainType == 'text':
      body=mime_msg.get_payload()
    processedEmail={'mimeMsg':mime_msg,'msgId':msg_id,'threadId':thread_id,'from':mime_msg['From'],'subject':mime_msg['Subject'],'body':""}
    if 'cc' in mime_msg.keys():
      processedEmail['cc'] = mime_msg['cc']
    if body is not None:
      customerReplyText=quotations.extract_from_plain(quotequail.quote(html2text(body))[0][1])
      processedEmail['body']=customerReplyText
    return processedEmail
  except Exception as e:
    raiseError("mimeMsgPRocessingError: "+repr(e)+" for mime_msg: "+mime_msg)
    return

def getTextEntities(customerReplyText):
  witHeaders={'Authorization': 'Bearer XB3R7L7M5P2QLB6BAPT5AXUK7XRZS7UP'}
  witParams={'q':customerReplyText}
  witResponse=requests.get('https://api.wit.ai/message',headers=witHeaders,params=witParams)
  wr=witResponse.json()
  entities={}
  if 'entities' not in wr.keys():
    return {}
  for wrEntity in wr['entities'].keys():
    for wrEntityValues in wr['entities'][wrEntity]:
      print wrEntityValues
      if wrEntity not in entities.keys():
        entities[wrEntity]=[{'value':wrEntityValues['value'],'confidence':wrEntityValues['confidence']}]
      else:
        entities[wrEntity].append({'value':wrEntityValues['value'],'confidence':wrEntityValues['confidence']})
  return entities

def getBestEntityValue(entities,entity):
  returnValue=None
  review=False #make this true for first few days
  if entity in entities.keys():
    if len(entities[entity])>1 or entities[entity][0]['confidence']<0.8:
      review=True
    else:
      returnValue=entities[entity][0]['value']
  return (returnValue,review)

def getEntityStatus(entities):
  review=False
  interestReview=False
  interest=0
  (phone,phoneReview)=getBestEntityValue(entities,'phone_number')
  (callTime,timeReview)=getBestEntityValue(entities,'datetime')
  if 'interestIntent' in entities.keys():
    for intent in entities['interestIntent']:
      if intent['value']!='interested' or intent['confidence']<0.8:
        interestReview=True
        break
      interest=max(interest,intent['confidence'])
  if interestReview or phoneReview or timeReview:
    review=True
  return {"interest":interest,"phone":phone,"callTime":callTime,"review":review}

def allowed_file(filename):
  return '.' in filename and \
         filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def uploadFile(request):
  if 'file' not in request.files:
    flash('No file part')
    return None
  file = request.files['file']
  if file.filename == '':
    flash('No selected file')
    return None
  if file and allowed_file(file.filename):
    filen = secure_filename(file.filename)
    filename = os.path.join(config['UPLOAD_FOLDER'], filen)
    file.save(filename)
    return filename

def actOnNewMessage(salesRep, lead):
  if lead.phone is not None and lead.callTime is not None and lead.interest > 0:
    lead.status = constants.HOT
    salesRep.scheduleCall(lead)
  elif lead.phone is not None and lead.callTime is None and lead.interest > 0:
    salesRep.sendReplyEmail(lead, constants.REQUEST_INFO_TEMPLATE['time'])
  elif lead.callTime is not None and lead.phone is None and lead.interest > 0:
    salesRep.sendReplyEmail(lead, constants.REQUEST_INFO_TEMPLATE['phone'])
  elif lead.interest > 0:
    salesRep.sendReplyEmail(lead, constants.REQUEST_INFO_TEMPLATE['phone&time'])
  else:
    lead.status = constants.FREEZE
  db.session.add(lead)
  db.session.commit()
  return
# ----------------------------------------------------------------------------#
# Site functions
# ----------------------------------------------------------------------------#
def stringifyTime(x):
  return "0"+str(x) if len(str(x))<2 else str(x)

def splitStateUrlParams(state):
  params={}
  if state is None:
    return params
  st=state.split('&')
  for prm in st:
    p=prm.split('=')
    if len(p)>1:
      params[p[0]]=p[1]
  return params

def dbCommit():
  try:
    db.session.commit()
  except:
    db.session.rollback()
  finally:
    db.session.close()

def flash_errors(form):
  for field, errors in form.errors.items():
    for error in errors:
      flash(u"Error in the %s field - %s" % (
        getattr(form, field).label.text,
        error
      ))

def sendConfirmationMail(to, subject, template):
  msg = Message(
    subject,
    recipients=[to],
    html=template,
    sender=config['MAIL_DEFAULT_SENDER']
  )
  mail.send(msg)

def generate_confirmation_token(email):
  serializer = URLSafeTimedSerializer(config['SECRET_KEY'])
  return serializer.dumps(email, salt=config['SECURITY_PASSWORD_SALT'])

def confirm_token(token, expiration=3600):
  serializer = URLSafeTimedSerializer(config['SECRET_KEY'])
  try:
    email = serializer.loads(
      token,
      salt=config['SECURITY_PASSWORD_SALT'],
      max_age=expiration
    )
  except:
    return False
  return email

def setSearchOption(request):
  search = False
  q = request.args.get('q')
  if q:
    search = True
  return search

def redirect_url(default='index'):
  return request.args.get('next') or request.referrer or url_for(default)


# ----------------------------------------------------------------------------#
# web2lead and lead qualification
# ----------------------------------------------------------------------------#
'''
def createAssistant(user):
  domain=user.email.split('@')[1]
  defaultName='alex'
  defaultEmail=defaultName+'@'+domain.split('.')[0]+'.tryscribe.com'
  defaultTitle='Business Analyst'
  assistant=assistants(user.id,defaultEmail,defaultName,user.company,
             defaultTitle, '')
  return assistant

def tryDictAdd(lead,a,data,b):
  try:
    d=data
    fields=b.split('%')
    for f in fields:
        d=d[f]
    lead[a]=listToString(d)
  except:
    print "error for "+str(a)

def listToString(d):
    if isinstance(d,list):
      l=",".join(d)
    else:
      l=d
    return l

def getLeadInfo(email,company,name):
  baseUrl = "https://api.fullcontact.com/v2/person.json"
  r = requests.get(baseUrl, params={'email': email}, headers={'X-FullContact-APIKey': '4064ca15e6a0cc42'})
  data = r.json()
  lead = {}
  lead['name']=name
  lead['email']=email
  lead['company']=company
  #tryDictAdd(lead, 'fullName', data, 'contactInfo' + "%" + 'fullName')
  tryDictAdd(lead, 'gender', data, 'demographics' + "%" + 'gender')
  tryDictAdd(lead, 'location', data, 'demographics' + "%" + 'locationDeduced' + "%" + 'normalizedLocation')
  try:
    #lead['company'] = listToString(data['organizations'][0]['name'])
    lead['title'] = listToString(data['organizations'][0]['title'])
  except:
    print "no organization"
    #lead['company'] = ""
    lead['title'] = ""
  tryDictAdd(lead, 'likelihood', data, 'likelihood')
  try:
    lead['tags'] = ",".join([topic['value'] for topic in data['digitalFootprint']['topics']])
  except:
    print "no tags"
    lead['tags'] = ""
  try:
    lead['bios'] = ",".join([profile['bio'] for profile in data['socialProfiles'] if 'bio' in profile.keys()])
  except:
    print "no bio"
    lead['bios'] = ""
  return lead
'''
