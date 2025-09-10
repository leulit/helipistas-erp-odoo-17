/*
widget_wait_signature = {
    init: function(){
        this._super.apply(this, arguments);
    },
    start: function() {
        var self = this;
        self.field_manager.on("field_changed:otp", this, function() {
            self.startCheck();
        });
        self.startCheck();
    },
    startCheck: function() {                
        var self = this;
        self.checking = true;
        var qritem = self.field_manager.get_field_value( 'otp' );
        if (qritem) {
            var iditem = self.field_manager.get_field_value( 'id' );
            var args = [iditem, qritem, self.field_manager.dataset.context];            
            self.field_manager.dataset.call('check_item_signed',args).done(function(r) {
                if (r) {
                    if (r.pendiente) {
                        self.field_manager.set_values({ "otp": r.otp});
                        setTimeout(
                            function() { 
                                self.startCheck();
                            }, 
                            2000
                        );                        
                    }
                    else {
                        self.view.reload();
                    }
                }
            }).fail(function(result) {
            });                
        }
    }
}

hack_signature = {
    init: function(){
        this._super.apply(this, arguments);
    },
    startHack: function() {
        var self = this;
        $('#hackcontainer').show();
        $('#hackbutton').click(function(evt){
            var iditem = self.field_manager.get_field_value( 'id' );
            var idpersona =  $("#idpersona"). val()
            var iddocumento =  $("#iddocumento"). val()
            var estado =  $("#strestado"). val()
            var args = [iditem, idpersona, iddocumento, estado, self.field_manager.dataset.context];            
            self.field_manager.dataset.call('hacksignature',args).done(function(r) {
                self.view.reload();
            }).fail(function(result) {
            });               
        });        
    },
    start: function() {
        var self = this;
        $("body").bind("keydown",function(e) {
            if ((e.ctrlKey)&&(e.keyCode == 13)){
                self.startHack();
            }    
        });
    },
}


openerp.leulit_esignature = function (instance, m) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    var _lt = instance.web._lt;


    instance.leulit_esignature.widget_wait_signature = instance.web.form.FormWidget.extend(widget_wait_signature);
    instance.web.form.custom_widgets.add('widget_wait_signature', 'instance.leulit_esignature.widget_wait_signature');

    instance.leulit_esignature.hack_signature = instance.web.form.FormWidget.extend(hack_signature);
    instance.web.form.custom_widgets.add('hack_signature', 'instance.leulit_esignature.hack_signature');

    instance.web.form.csv_code = instance.web.form.FormWidget.extend(csv_code(instance));
    instance.web.form.custom_widgets.add('csv_code', 'instance.web.form.csv_code');
};
*/