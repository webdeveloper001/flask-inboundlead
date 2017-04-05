from flask_testing import TestCase
import constants, time

from app import app, db
from models import *

class BaseTestCase(TestCase):
    """A base test case for flask-tracking."""

    def create_app(self):
        app.config.from_object('config.TestingConfig')
        return app

    def setUp(self):
        #db.create_all()
        return

    def tearDown(self):
        db.session.remove()
        db.leads.query.delete()
        #db.drop_all()

    def getSalesRep(self):
        hostEmail="sachinbhat.as@gmail.com"
        host=db.session.query(hosts).filter_by(email=hostEmail).first()
        salesRep = db.session.query(sales_rep).filter_by(email=host.salesRep).first()
        salesRep.watchAndStop()
        return salesRep

    def test_get_assistant_emails(self):
        salesRep = self.getSalesRep()
        subject="test email"
        sendMail(salesRep.email,"developer@tryscribe.com",subject,"test email body")
        time.sleep(60)
        salesRep.getNewAssistantEmails()
        leadList=db.session.query(leadThreads).filter_by(salesRep=salesRep.email).all()
        self.assertEquals(len(leadList),1)
        lead=leadList[0]
        self.assertEquals(lead.review,True)
        self.assertEquals(lead.subject,subject)
        self.assertEquals(lead.replyEmailCount,1)

    def test_check_free_busy(self):
        salesRep = self.getSalesRep()
