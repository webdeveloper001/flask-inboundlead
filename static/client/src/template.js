(function (){

	var iframe = document.createElement('iframe');
	var wrapper = document.createElement('div');
	var backdrop = document.createElement('div');
	var isMobile = 'ontouchstart' in window || navigator.maxTouchPoints;

	var methods = {

		init: function (){

			this.iframe.init();

			//this.backdrop.init();	

			document.body.appendChild(wrapper);
			wrapper.appendChild(iframe);
			//wrapper.appendChild(backdrop);


			this.listen_for_iframe_message();

		},

		backdrop: {
			init: function (argument) {
				backdrop.style.position = 'fixed';
				backdrop.style.width = '100%';
				backdrop.style.height = '100%';
				backdrop.style.top = '0';
				backdrop.style.left = '0';
				backdrop.style.opacity = '0';
				backdrop.style.background = 'rgba(0, 0, 0, 0.5)';
				backdrop.style.transition = 'opacity 0.5s';
				backdrop.style.pointerEvents = 'none';
				backdrop.style.zIndex = '2147483646';
			}
		},

		iframe: {
			init: function () {
				iframe.id = 'modalEmbed',
				iframe.src = methods.get_base_url()+'/modalTest';
				iframe.name = methods.get_uid() + '-' + methods.get_open_type() ;
	            iframe.frameBorder = '0';
	            iframe.scrolling = 'no';
	            iframe.style.position = 'fixed';
	            iframe.style.bottom = '0';
	            iframe.style.right = '0';
	            iframe.style.zIndex = '2147483647';
	            iframe.style.transition = 'opacity 0.5s';
	            iframe.style.opacity = '0';
	            iframe.style.width = '80px';
	            iframe.style.height = '80px';

				iframe.onload = function() {
					iframe.style.opacity = '1';
				};
			}
		},

		get_uid: function (){

			if (!document.currentScript)
			{
				document.currentScript = (function() {
				  var scripts = document.getElementsByTagName('script');
				  return scripts[scripts.length - 1];
				})();
			}


			return document.currentScript.getAttribute('data-uid');


		},

		get_open_type: function () {

			if (!document.currentScript)
			{
				document.currentScript = (function() {
				  var scripts = document.getElementsByTagName('script');
				  return scripts[scripts.length - 1];
				})();
			}


			return document.currentScript.getAttribute('data-opentype');

		},

		get_base_url: function () {

			if (!document.currentScript)
			{
				document.currentScript = (function() {
				  var scripts = document.getElementsByTagName('script');
				  return scripts[scripts.length - 1];
				})();
			}


			return document.currentScript.getAttribute('data-url');

		},

		listen_for_iframe_message: function () {

			var originalScrollPosition;
			var originalBodyPosition = document.body.style.position;
			var originalBodyOverflow = document.body.style.position;

			window.onmessage = function(e){
			    if (e.data == 'full') {
		            iframe.style.width = '100%';
		            iframe.style.height = '100%';
		            // document.body.style.position = 'fixed';
            		// document.body.style.overflow = 'hidden';
		            backdrop.style.opacity = '1';
		            // currentScrollPosition = document.documentElement.scrollTop || document.body.scrollTop;
		            iframe.contentWindow.postMessage('resized', '*');
			    }
			    else if (e.data == 'small') {
			    	iframe.style.width = '80px';
            		iframe.style.height = '80px';
            		document.body.style.position = originalBodyPosition;
            		document.body.style.overflow = originalBodyOverflow;
					backdrop.style.opacity = '0';
					if (isMobile && currentScrollPosition)
					{
						window.scrollTo(0,currentScrollPosition);
						currentScrollPosition = null;
					}
            		iframe.contentWindow.postMessage('resized', '*');
			    }
			    else if (e.data == 'email') {
			    	iframe.style.width = '340px';
            		iframe.style.height = '205px';
            		// document.body.style.position = 'fixed';
            		// document.body.style.overflow = 'hidden';
            		backdrop.style.opacity = '1';
            		// currentScrollPosition = document.documentElement.scrollTop || document.body.scrollTop;
            		iframe.contentWindow.postMessage('resized', '*');
			    }
			    else if (e.data == 'focused')
			    {
			    	currentScrollPosition = document.documentElement.scrollTop || document.body.scrollTop;
            		document.body.style.position = 'fixed';
            		document.body.style.overflow = 'hidden';
			    }
			    
			};

		},

		openCalendar: function () {
			iframe.contentWindow.postMessage('openCalendar', '*');

		}
	};

	methods.init();

	window.scribe = {
		openCalendar: methods.openCalendar
	}

})();

