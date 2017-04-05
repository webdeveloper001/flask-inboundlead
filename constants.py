DEFAULT_SIGNATURE = "-- \n R \n Sales Assistant"

OUTBOUND_SUBJECT = "Regarding your interest in "
FIRST_MAIL_TEMPLATE =  "Thanks for visiting our website. I just wanted to check with you if you found everything you were looking for. " \
                       "Otherwise, I am happy to help. Let me know if you want to schedule a call"
SECOND_TEMPLATE="I will set up a call with my executive right away. What would be a good number to contact you?"
DRIP_TEMPLATE=[FIRST_MAIL_TEMPLATE,SECOND_TEMPLATE,SECOND_TEMPLATE,SECOND_TEMPLATE]
DRIP_GAP_DAYS=3

REQUEST_INFO_TEMPLATE={}
REQUEST_INFO_TEMPLATE['phone']="Sure. Let me quickly schedule a call. What's a good number to contact you?"
REQUEST_INFO_TEMPLATE['time']="Sure. Let me quickly schedule a call. What's a good time to contact you?"
REQUEST_INFO_TEMPLATE['phone&time']="Sure. Let me quickly schedule a call. What's a good number and time to contact you?"


CALL_DURATION=30
#LEAD STATUSES
FREEZE="Not Interested" #said he is not interested
COLD="cold" #no reply yet
WARM="warm" #has shown interest but has not given phone and time
HOT="hot"
PROVIDED_PHONE="phone" #has provided phone number
PROVIDED_TIME="time" #has provided time
PROVIDED_TIMEZONE="timezone" #has provided timezone

#SpreadSheet Header
SPREADSHEET_HEADER=[['Email', 'Name', 'Gender', 'Company', 'Title', 'Seniority', 'Location', 'LinkedIn', 'Company Description', 'Company Sector', 'Company Type',
'Company Industry', 'Company Sub Industry', 'Company Sector', 'Company Founded Year', 'Company Employee Count','Company Tech', 'Market Cap', 'Raised', 'Company Url', 'Company Emails']]