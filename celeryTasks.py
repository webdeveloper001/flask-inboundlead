from googleAppFunctions import *
from app import celery, db
from assistantAIfunctions import *
from models import *
from time import sleep
from celery.task import periodic_task
import gc, resource
#----------------------------------------------------------------------------#
# celery background async functions
# ----------------------------------------------------------------------------#

@celery.task(ignore_result=True)
def processMessage(userEmail):
    sleep(60)
    salesRep = db.session.query(sales_rep).filter_by(email=userEmail).first()
    if salesRep is None:
        return
    salesRep.getNewAssistantEmails()
    db.session.commit()
    return

#need to change this to push
@periodic_task(run_every=timedelta(seconds=120),ignore_result=True)
def processInboxes():
    salesReps = db.session.query(sales_rep).all()
    for salesRep in salesReps:
        try:
            if salesRep.pollingError<5 and salesRep.monitorEmail:
                salesRep.getNewAssistantEmails()
                db.session.commit()
        except Exception as e:
            raiseError("celeryError: Stopped polling for inbound emails"+repr(e)+" for salesRep: "+salesRep.email)
            salesRep.pollingError+=1
            db.session.add(salesRep)
            db.session.commit()
    gc.collect()
    return