csv_code = function(instance) {    
    return {
        datatable: null,
        datos : [],

        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            $('#btn_signaturedocquerey').click(function(evt){
                $('#table_signaturedocquerey').DataTable().destroy();
                self.doQuery();
            });
            $('.oe_view_manager_header').hide();
        },

        drawTable: function(){
            var self = this;
            self.datatable = $('#table_signaturedocquerey').DataTable( {
                "lengthMenu": [ [10, 25, 50, -1], [10, 25, 50, "All"] ],
                order: [[1, 'desc']],
                buttons: [],
                dom: 'lrtip',
                "scrollY":        '60vh',
                "scrollCollapse": true,
                "paging":         false
            } );
            $('.custom_form_button_csv_verificar').click(function(evt){
                //console.log(evt);
                //return this.session.url('/web/binary/saveas', {model: 'ir.attachment', field: 'datas', filename_field: 'datas_fname', id: attachment['id']});javascript:void(0)
                
                var item = $(evt.currentTarget);
                var id = item.attr("data-id");
                /*
                var attachment_id = item.attr("data-attachment_id");
                var model = item.attr("data-model");
                
                var datas_fname = item.attr("data-filename");
                */
                var obj = self.findById(id)
                //url = instance.session.url('/web/binary/saveas', {model: model, field: "datas", id: id});
                //console.log(url);
                //window.location.href = url;
                instance.session.get_file({
                    url: '/web/binary/saveas_ajax',
                    data: {data: JSON.stringify({
                        model: obj.modelo,
                        id: obj.id,
                        field: "datas",
                        filename_field: "datas_fname",
                        data: obj.datas,
                        filename: obj.attachment_id[1],
                        //context: this.view.dataset.get_context()
                    })},
                    complete: instance.web.unblockUI,
                    //error: c.rpc_error.bind(c)
                });
                evt.stopPropagation();
            });
        },

        findById: function(idItem) {
            var self = this;
            for (var i= 0; i<self.datos.length; i++) {
                if (self.datos[i].id == idItem) {
                    return self.datos[i];
                    break;
                }
            }
            return null;
        },

        doQuery: function() {
            var self = this;
            var csvcode = self.field_manager.get_field_value("csvcode");
            var id = self.field_manager.datarecord.id;
            var args = [id, csvcode, self.field_manager.dataset.context];
            self.field_manager.dataset.call_button('doquery', args).done(function(r) {
                if (r) {
                    tira = "";
                    for (var i= 0; i<r.items.length; i++) {
                        tira += '<tr>';
                        tira += '<td>'+(r.items[i].id? r.items[i].id: "-")+'</td>';
                        tira += '<td style="white-space: nowrap;">'+(r.items[i].firmado_por? r.items[i].firmado_por[1]: "-")+'</td>';
                        tira += '<td style="white-space: nowrap;">'+(r.items[i].fecha_valid? r.items[i].fecha_valid.replace("00:00:00", ""): "-")+'</td>';
                        tira += '<td style="white-space: nowrap;">'+(r.items[i].hashcode? r.items[i].hashcode: "-")+'</td>';
                        tira += '<td style="white-space: nowrap;">'+(r.items[i].name? r.items[i].name: "-")+'</td>';
                        data = 'data-model="'+r.items[i].modelo+'" ';
                        s1 = r.items[i].attachment_id ? r.items[i].attachment_id[0] : "";
                        s2 = r.items[i].attachment_id ? r.items[i].attachment_id[1] : "";
                        data += 'data-attachment_id="'+s1+'" ';
                        data += 'data-filename="'+s2+'" ';
                        data += 'data-id="'+r.items[i].id+'" ';
                        tira += '<td><button type="button" class="oe_button custom_form_button_csv_verificar" '+data+'>Descargar</button></td>';
                        self.datos.push(r.items[i]);
                    }

                    $('#tdbody').empty();
                    $('#tdbody').append(tira);
                    self.drawTable();
                }
            });
        }
    }
}



