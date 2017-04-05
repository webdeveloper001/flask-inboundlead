import '../styles/less/main.less';
import 'jquery';
import _template from 'lodash/template';
import _filter from 'lodash/filter';
import _forEach from 'lodash/forEach';
import _keyBy from 'lodash/keyBy';
import _mapValues from 'lodash/mapValues';
import moment from 'moment';
import 'pickadate/lib/picker.date';
import 'pickadate/lib/picker.time';
import button_template from '../templates/button.html';
import email_template from '../templates/email.html';
import modal_template from '../templates/modal.html';
import calendar_template from '../templates/calendar.html';
import thanks_template from '../templates/thanks.html';
import appointment_template from '../templates/appointment.html';
import moreQuestions_template from '../templates/moreQuestions.html';

(function (){

  var methods = {

    uid: window.name.split('-')[0],

    init: function () {

      // get events asap
      methods.calendar.get_events();

      this.listen_to_parent_message();

      $('<div/>', { class: 'wrap' })
      .appendTo('body');

      var isMobileCheck={Android:function(){return navigator.userAgent.match(/Android/i)},BlackBerry:function(){return navigator.userAgent.match(/BlackBerry/i)},iOS:function(){return navigator.userAgent.match(/iPhone|iPad|iPod/i)},Opera:function(){return navigator.userAgent.match(/Opera Mini/i)},Windows:function(){return navigator.userAgent.match(/IEMobile/i)},any:function(){return isMobileCheck.Android()||isMobileCheck.BlackBerry()||isMobileCheck.iOS()||isMobileCheck.Opera()||isMobileCheck.Windows()}},
	  isMobile=isMobileCheck.any();

      //if(!isMobile){
        if (window.name.split('-')[1] == 'true') this.button.init();
      //}

    },

    button: {

      init: function () {

        $('.wrap').append( _template(button_template)() );

        this.$ = $('.button');

        // register events
        this.$.click( $.proxy(this.events.on_click, this) );
        $('body').click($.proxy(this.events.on_window_click, this));

        this.closeEmailTimeout = setTimeout($.proxy(function () {
            methods.email.init();
            this.$.toggleClass('show-email-active');
        }, this), 30000);
        return this;

      },

      events: {
        on_click: function (e) {
            console.log("hi5");
          e.stopPropagation();

          if (this.closeEmailTimeout) clearTimeout(this.closeEmailTimeout);
          if (this.closeThanksTimeout) clearTimeout(this.closeThanksTimeout);

          if ( this.$.hasClass('show-email-active') ) {
            methods.email.remove();
            methods.modal.remove();
            methods.set_iframe_size('small');
          }
          else
          {
            methods.email.init();
          }

          this.$.toggleClass('show-email-active');

        },

        on_window_click: function () {

          methods.email.remove();
          methods.modal.remove();
          methods.calendar.remove();

          methods.set_iframe_size('small');

          this.$.toggleClass('show-email-active');
        }
      }

    },

    email: {

      init: function () {

        // resize iframe
        methods.set_iframe_size('email', $.proxy(function (){

          $('.wrap').append( _template(email_template)() );

          this.$ = $('.email-form');

          // register events
          this.$.submit( $.proxy(this.events.on_submit, this) );
          this.$.click( $.proxy(this.events.on_click, this) );
          if ('ontouchstart' in window) this.$.find('input').focus($.proxy(this.events.on_focus, this));

          return this;


        }, this));

      },

      events: {
        on_submit: function (e) {

          e.preventDefault();

          var email = this.$.find('input[type="email"]').val();

          this.validate_email(email);

        },

        on_click: function (e) {
          e.stopPropagation();
        },

        on_focus: function () {
          window.top.postMessage('focused', '*');
        }
      },

      remove: function () {

        if (this.$) this.$.remove();

        return this;

      },

      validate_email: function (email) {

        $.ajax({
          url: '/iQualifyEmail/' + methods.uid,
          type: 'POST',
          dataType: 'json',
          contentType: 'application/json; charset=utf-8',
          data: JSON.stringify({
            email: email
          }),
          success: $.proxy(this.on_validate_email_success, this),
          error: $.proxy(this.on_validate_email_error, this)
        });


      },

      on_validate_email_success: function (data) {

        methods.leadId = data.leadId;
        methods.leadName = data.leadName;

        methods.modal.init(function () {

          if ( data.type === 'schedule' )
          {
            methods.calendar.init().get_events();
          }
          else if ( data.type === 'moreQuestions' )
          {

            methods.morequestions.init(data.questionFields);

          }
          else
          {
            methods.thanks.init();
          }

        });

        this.remove();




      },

      on_validate_email_error: function () {

        methods.modal.init(function() {
            methods.thanks.init();
        });

        this.remove();

      },


    },

    modal: {

      init: function (callback){

        $('body').addClass('modal-opened');

        console.log('Modal init called')

        methods.set_iframe_size('full', $.proxy(function () {

          console.log('modal init render');

          // prevent another form submission
          methods.button.$.addClass('disabled');

          console.log('modal init render2');
          $('.wrap').after( _template(modal_template)() );

          this.$ = $('.modal-wrap');

          this.$.click($.proxy(this.events.on_click, this));
          this.$.find('.close').click( $.proxy(this.events.on_close_click, this) );

          if (callback) callback();

          return this;


        }, this));


      },

      events: {
        on_click: function (e){
          e.stopPropagation();
        },
        on_close_click: function () {
          this.remove();
        }

      },

      remove: function (){

        $('body').removeClass('modal-opened');

        if (this.$) this.$.remove();

        // enable form submission
        methods.button.$.removeClass('disabled');


      }

    },

    calendar: {

      init: function () {

        $('.modal-wrap')
        .addClass('cal-wrap')
        .append( _template(calendar_template)() );


        this.$ = $('.cal-inner-wrap');

        var $datepicker = this.$.find('#datepicker').pickadate({
          today: '',
          clear: '',
          close: '',
          klass: {
            navPrev: 'picker__nav--prev',
            navNext: 'picker__nav--next',
          },
          min: moment.now(),
          disable: this.weekend,
          onSet: $.proxy(this.events.on_date_change, this)
        });

        var $timepicker = $('#timepicker').pickatime({
          clear: '',
          interval: this.call_duration,
          min: this.day_start,
          max: this.day_end,
          onSet: $.proxy(this.events.on_time_change, this)
        });

        this.datepicker = $datepicker.pickadate('picker');
        this.timepicker = $timepicker.pickatime('picker');

        this.datepicker.open();
        this.timepicker.open();

        this.set_disabed_time_slot( this.datepicker.get('highlight').pick );

        $('.cal-wrap').scrollTop(0);

        return this;
      },

      events: {
        on_date_change: function (date) {
          this.set_disabed_time_slot(date.select || this.datepicker.get('highlight').pick);
        },

        on_time_change: function(time) {
            console.log(time);
          if (time.select)
          {
            $('.btn-confirm')
            .removeClass('disabled')
            .off()
            .on('click', $.proxy(this.create_event, this));
          }
        },

        on_get_events_success: function (resp) {

          var self = this;

          this.day_start = resp.dayStart;
          this.day_end = resp.dayEnd;
          this.call_duration = resp.callDuration;
          this.weekend = resp.weekend;

          this.busyDates = _forEach(resp.mergedEvents, function (value, key, collection){

            collection[key] = {
              from: moment(value.start.dateTime || value.start.date).toDate(),
              to: moment(moment(value.end.dateTime).subtract(self.callDuration, 'minutes') || value.start.date).toDate()
            };

          });


        },

        on_get_events_error: function () {
          this.remove();
          methods.thanks.init();
        },

        on_create_event_success: function (){
            console.log("event created");
          this.remove();
          methods.appointment.init();
        },

        on_create_event_error: function (){
          this.remove();
          methods.thanks.init();
        },
      },

      remove: function () {
        $('.modal-wrap').removeClass('cal-wrap');
        if (this.$) this.$.remove();
      },

      get_events: function () {
        $.ajax({
          dataType: 'json',
          url: '/getEvents/' + methods.uid,
          success: $.proxy(this.events.on_get_events_success, this),
          error: $.proxy(this.events.on_get_events_error, this)
        });
      },

      create_event: function () {
        var phone = this.$.find('input[type="tel"]').val();
        if(phone==''){
            return
        }
        var slot = moment(this.datepicker.get('highlight').pick).add(this.timepicker.get('highlight').pick, 'minutes');
        console.log(slot.format());
        $.ajax({
          url: '/createEvent/' + methods.uid + '/' + methods.leadId,
          type: 'POST',
          dataType: 'json',
          contentType: 'application/json; charset=utf-8',
          data: JSON.stringify({
            start: slot.format(),
            end: slot.add(this.get_timepicker_interval(), 'm').format()
          }),
          success: $.proxy(this.events.on_create_event_success, this),
          error: $.proxy(this.events.on_create_event_error, this)
        });
      },

      set_disabled_dates: function (value) {
        this.datepicker.set('disable', value);
      },

      set_timepicker_interval: function (value) {
        this.timepicker.set('interval', value);
      },

      get_timepicker_interval: function () {
        return this.timepicker.get('interval');
      },

      set_timepicker_day_start: function (value) {
        this.timepicker.set('min', value);
      },

      set_timepicker_day_end: function (value) {
        this.timepicker.set('max', value);
      },

      set_disabed_time_slot: function (datetime) {

        var busyToday = _filter(this.busyDates, function (o){
          return moment(o.from).isSame(moment(datetime), 'day') && moment(o.to).isSame(moment(datetime), 'day');
        });


        this.timepicker.set('enable', true);
        this.timepicker.set('disable', busyToday);
      },

    },

    morequestions: {

      init: function (questionFields) {

        $('.modal-content').empty().append( _template(moreQuestions_template)({ questionFields: questionFields, _forEach: _forEach }) );
        var content=$('.modal-content').html().replace('{{ leadName }}',methods.leadName);
        $('.modal-content').html(content);
        this.$ = $('.questionForm');

        this.$.submit($.proxy(this.events.on_submit, this));

        this.show();

        return this;

      },

      events: {
        on_submit: function (e) {

          e.preventDefault();
          var responseDict = _keyBy(this.$.serializeArray(), 'name');
          responseDict = _mapValues(responseDict, 'value');
          console.log(responseDict);
          $.ajax({
            url: '/iMoreQuestions/' + methods.uid + '/' + methods.leadId,
            type: 'POST',
            contentType: 'application/json; charset=utf-8',
            dataType: 'json',
            data: JSON.stringify(responseDict),
            success: $.proxy(this.events.on_more_questions_success, this),
            error: $.proxy(this.events.on_more_questions_error, this)
          });
        },

        on_more_questions_success: function(data) {

          this.remove();
          if ( data.type === 'schedule' )
          {
            methods.calendar.init();
          }
          else
          {
            methods.thanks.init();
          }
        },

        on_more_questions_error: function() {
          methods.thanks.init();
        },

      },

      show: function () {
        this.$.show();
      },

      remove: function () {

        this.$.remove();

      }

    },

    thanks: {

      init: function () {
        $('.modal-wrap').css('width','350px');
        $('.modal-content').append( _template(thanks_template)({ leadId: methods.leadId }) );
        var content=$('.modal-content').html().replace('{{ leadName }}',methods.leadName);
        $('.modal-content').html(content);
        this.$ = $('.thanks');

        this.show();

        this.closeThanksTimeout  = setTimeout($.proxy(function () {

          this.remove();
          methods.modal.remove();
          methods.button.$.toggleClass('show-email-active');
          methods.set_iframe_size('small');

        }, this), 30000);

        return this;


      },

      remove: function () {
        this.$.remove();
      },

      show: function () {
        this.$.show();
      }

    },

    appointment: {

      init: function () {

        $(".modal-wrap").css("width","350px");
        $('.modal-content').append( _template(appointment_template)({ leadId: methods.leadId }) );
        var content=$('.modal-content').html().replace('{{ leadName }}',methods.leadName);
        $('.modal-content').html(content);

        this.$ = $('.appointment');

        this.show();

        setTimeout($.proxy(function () {

          this.remove();
          methods.modal.remove();
          methods.button.$.toggleClass('show-email-active');

        }, this), 30000);

        return this;

      },

      show: function () {
        this.$.show();
      },

      remove: function () {
        this.$.remove();
      }

    },


    set_iframe_size: function (size, callback) {


      window.top.postMessage(size, '*');

      window.onmessage = function(e){
        console.log(e.data);
        if (e.data == 'resized') {
          setTimeout(function () {
            if (callback) {
              callback();
              callback = null;
            }
          }, 0);

        }
        if (e.data == 'openCalendar'){
             methods.open_2calendar();
        }
      };


    },


    listen_to_parent_message: function () {
      window.onmessage = function(e){
        if ( e.data == 'openCalendar' ) {
            methods.open_2calendar();
        }
        if ( e.data == 'openButton' ) {
            methods.button.init();
        }
      };

    },

    open_2calendar : function() {
      if (window.name.split('-')[1] == 'true'){
        $('.button').trigger('click');
      }
    }

  }

  methods.init();

})();