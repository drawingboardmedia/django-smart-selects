import locale

import django

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import get_model
from django.forms.widgets import Select
from django.utils.safestring import mark_safe

from smart_selects.utils import unicode_sorter


JQUERY_URL = getattr(settings, 'JQUERY_URL', 'http://ajax.googleapis.com/ajax/libs/jquery/1.3.2/jquery.min.js')

URL_PREFIX = getattr(settings, "SMART_SELECTS_URL_PREFIX", "")

class ChainedSelect(Select):
    def __init__(self, app_name, model_name, chain_field,
                 model_field, show_all, auto_choose,
                 manager=None, view_name=None, *args, **kwargs):
        self.app_name = app_name
        self.model_name = model_name
        self.chain_field = chain_field
        self.model_field = model_field
        self.show_all = show_all
        self.auto_choose = auto_choose
        self.manager = manager
        self.view_name = view_name
        super(Select, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, choices=()):
        if len(name.split('-')) > 1:  # formset
            chain_field = '-'.join(name.split('-')[:-1] + [self.chain_field])
        else:
            chain_field = self.chain_field
        if not self.view_name:
            if self.show_all:
                view_name = "chained_filter_all"
            else:
                view_name = "chained_filter"
        else:
            view_name = self.view_name
        kwargs = {'app': self.app_name, 'model': self.model_name,
                  'field': self.model_field, 'value': "1"}
        if self.manager is not None:
            kwargs.update({'manager': self.manager})
        url = URL_PREFIX + ("/".join(reverse(view_name, kwargs=kwargs).split("/")[:-2]))
        if self.auto_choose:
            auto_choose = 'true'
        else:
            auto_choose = 'false'
        empty_label = iter(self.choices).next()[1]  # Hacky way to getting the correct empty_label from the field instead of a hardcoded '--------'
        js = """
        <script type="text/javascript" src="/site_media/media/javascript/public/jquery-1.5.2.min.js"></script>
        <script type="text/javascript">
        //<![CDATA[
        // this is for accessing the fill_field globally
       
        (function($) {
            function fireEvent(element,event){
                if (document.createEventObject){
                // dispatch for IE
                var evt = document.createEventObject();
                return element.fireEvent('on'+event,evt)
                }
                else{
                // dispatch for firefox + others
                var evt = document.createEvent("HTMLEvents");
                evt.initEvent(event, true, true ); // event type,bubbling,cancelable
                return !element.dispatchEvent(evt);
                }
            };

            function dismissRelatedLookupPopup(win, chosenId) {
                var name = windowname_to_id(win.name);
                var elem = document.getElementById(name);
                if (elem.className.indexOf('vManyToManyRawIdAdminField') != -1 && elem.value) {
                    elem.value += ',' + chosenId;
                } else {
                    elem.value = chosenId;
                }
                fireEvent(elem, 'change');
                win.close();
            };
	    
            var fill_field = function(val, init_value){
	      	    if(!val || val==''){
                    options = '<option value="">%(empty_label)s<'+'/option>';
                    $("#%(id)s").html(options);
                    $('#%(id)s option:first').attr('selected', 'selected');
                    $("#%(id)s").trigger('change');                                                
                    return;
                }
                $.ajaxSetup({async:false});
                $.getJSON("%(url)s/"+val+"/", function(j){
                    var selected_state_value = '%(value)s';
                    if (j.out == ''){
                        // convert select field into textfield if no state is assigned for selected country
                        // User can fill Custom value into state field
                        $("#%(id)s").replaceWith('<input id="%(id)s" type="text" name="%(name)s" value="" />');
                        document.getElementById("%(id)s").value = selected_state_value;
                        $('label[for="%(id)s"]').html(j.political_divisions);
                        selected_state_value = '';
                    }
                    else {
                        var select_state = document.createElement("select");
                        select_state = $(select_state).attr('id', '%(id)s');
                        select_state = $(select_state).attr('name', '%(name)s');
                        $('input#%(id)s').replaceWith(select_state);
                        $('#%(id)s').empty();
                        $('label[for="%(id)s"]').html(j.political_divisions);
                        var options = '<option value="">%(empty_label)s<'+'/option>';
                        for (var i = 0; i < j.out.length; i++) {
                            options += '<option value="' + j.out[i].display + '">' + j.out[i].display + '<'+'/option>';
                            if (j.out[i] == selected_state_value) {
                                options[i].selected = true;
                            }
                        }
                        selected_state_value = '';
                        var width = $("#%(id)s").outerWidth();
                        $("#%(id)s").html(options);
                        if (navigator.appVersion.indexOf("MSIE") != -1)
                            $("#%(id)s").width(width + 'px');
                        $('#%(id)s option:first').attr('selected', 'selected');
                        var auto_choose = %(auto_choose)s;
                        if(init_value){
                            $('#%(id)s option[value="'+ init_value +'"]').attr('selected', 'selected');
                        }
                        if(auto_choose && j.out.length == 1){
                            alert('ssss');
                            $('#%(id)s option[value="'+ j.out[0].value +'"]').attr('selected', 'selected');
                        }
                        $("#%(id)s").trigger('change');
                    }
                });
            };
            $(document).ready(function(){
                if(!$("#id_%(chainfield)s").hasClass("chained")){
                    var val = $("#id_%(chainfield)s").val();
                    fill_field(val, "%(value)s");
                }
                $("#id_%(chainfield)s").change(function(){
                    var start_value = $("#%(id)s").val();
                    var val = $(this).val();
                    fill_field(val, start_value);
                });
              
            });
            if (typeof(dismissAddAnotherPopup) !== 'undefined') {
                var oldDismissAddAnotherPopup = dismissAddAnotherPopup;
                dismissAddAnotherPopup = function(win, newId, newRepr) {
                    oldDismissAddAnotherPopup(win, newId, newRepr);
                    if (windowname_to_id(win.name) == "id_%(chainfield)s") {
                        $("#id_%(chainfield)s").change();
                    }
                }
            }
            // making function which is returning state as global so that we can call this function when we need to fill the state filled on 
            // any event in the checkout stages
            window.fill_field = fill_field
        })(jQuery || django.jQuery);
        //]]>
        </script>


        """
        js = js % {"chainfield": chain_field,
                   "url": url,
                   "id": attrs['id'],
                   "name": name	,
                   'value': value,
                   'auto_choose': auto_choose,
                   'empty_label': empty_label}
        final_choices = []
        if value:
            try:
                item = self.queryset.get(pk=value)        #  change 
                try:
                    pk = getattr(item, self.model_field + "_id")
                    filter = {self.model_field: pk}
                except AttributeError:
                    try:  # maybe m2m?
                        pks = getattr(item, self.model_field).all().values_list('pk', flat=True)
                        filter = {self.model_field + "__in": pks}
                    except AttributeError:
                        try:  # maybe a set?
                            pks = getattr(item, self.model_field + "_set").all().values_list('pk', flat=True)
                            filter = {self.model_field + "__in": pks}
                        except:  # give up
                            filter = {}
                filtered = list(get_model(self.app_name, self.model_name).objects.filter(**filter).distinct())
                filtered.sort(cmp=locale.strcoll, key=lambda x: unicode_sorter(unicode(x)))
                for choice in filtered:
                    final_choices.append((choice.pk, unicode(choice)))
            except Exception, e:
                final_choices = [(value, value)] # changes
            if len(final_choices) > 1:
                final_choices = [("", (empty_label))] + final_choices
            if self.show_all:
                final_choices.append(("", (empty_label)))
                self.choices = list(self.choices)
                self.choices.sort(cmp=locale.strcoll, key=lambda x: unicode_sorter(x[1]))
                for ch in self.choices:
                    if not ch in final_choices:
                        final_choices.append(ch)
        self.choices = ()
        final_attrs = self.build_attrs(attrs, name=name)
        if 'class' in final_attrs:
            final_attrs['class'] += ' chained'
        else:
            final_attrs['class'] = 'chained'
        output = super(ChainedSelect, self).render(name, value, final_attrs, choices=final_choices)
        output += js
        return mark_safe(output)
