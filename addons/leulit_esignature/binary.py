import base64
import openerp.addons.web.http as oeweb
from openerp.addons.web.controllers.main import content_disposition
import mimetypes
import logging
_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# Controller
#----------------------------------------------------------
class signaturedoc(oeweb.Controller):
    _cp_path = '/web/signaturedoc'

    #'url': '/web/signaturedoc/download_document?model=ir.attachment&field=datas&id={0}&filename={1}'.format(item['attachment_id'], item['datas_fname']),
    @oeweb.httprequest
    def download_document(self, req, model, field, id, filename, **kw):
        _logger.error("-->download_document--> model = %r",model)
        _logger.error("-->download_document--> id = %r",id)        
        _logger.error("-->download_document--> req = %r",req)
        _logger.error("-->download_document--> req.httprequest = %r",req.httprequest)
        _logger.error("-->download_document--> req.httprequest.method = %r",req.httprequest.method)
        _logger.error("-->download_document--> req.httprequest.environ = %r",req.httprequest.environ)
        _logger.error("-->download_document--> req.session = %r",req.session)        

        d = dict(x.replace('%22','').strip('%22').strip().split("=") for x in req.httprequest.environ['HTTP_COOKIE'].split(";"))

        session_id = d['instance0|session_id']
        _logger.error("-->download_document--> session_id = %r",session_id)        
        '''
        for k, v in d.items():
            _logger.error("-->download_document--> key = %r",k)     
            _logger.error("-->---->download_document--> value = %r",v)        

        import json
        jsonStr = json.dumps(req.session.__dict__)
        _logger.error("-->download_document--> session jsonStr = %r",jsonStr)

        from openerp import http                
        '''

        Model = req.session.model('ir.attachment')
        _logger.error("-->download_document--> Model = %r",Model)
        
        records = Model.read(id, field or False, req.context)
        filecontent = False
        for r in records:
            filecontent = r['datas']
        if filecontent and filename:
            content_type = mimetypes.guess_type(filename)
            return req.make_response(filecontent,
                    headers=[('Content-Type', content_type[0] or 'application/octet-stream'),
                            ('Content-Disposition', content_disposition(filename, req))])
        return req.not_found()


'''
            return session.url('/mail/download_attachment', {
                'model': 'mail.message',
                'id': message_id,
                'method': 'download_attachment',
                'attachment_id': attachment_id
            });

    @oeweb.httprequest
    def download_attachment(self, req, model, id, method, attachment_id, **kw):
        Model = req.session.model(model)
        res = getattr(Model, method)(int(id), int(attachment_id))
        if res:
            filecontent = base64.b64decode(res.get('base64'))
            filename = res.get('filename')
            content_type = mimetypes.guess_type(filename)
            if filecontent and filename:
                return req.make_response(filecontent,
                    headers=[('Content-Type', content_type[0] or 'application/octet-stream'),
                            ('Content-Disposition', content_disposition(filename, req))])
        return req.not_found()



from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import serialize_exception,content_disposition
import base64

class Binary(http.Controller):
 @http.route('/web/binary/download_document', type='http', auth="public")
 @serialize_exception
 def download_document(self,model,field,id,filename=None, **kw):
     """ Download link for files stored as binary fields.
     :param str model: name of the model to fetch the binary from
     :param str field: binary field
     :param str id: id of the record from which to fetch the binary
     :param str filename: field holding the file's name, if any
     :returns: :class:`werkzeug.wrappers.Response`
     """
     Model = request.registry[model]
     cr, uid, context = request.cr, request.uid, request.context
     fields = [field]
     res = Model.read(cr, uid, [int(id)], fields, context)[0]
     filecontent = base64.b64decode(res.get(field) or '')
     if not filecontent:
         return request.not_found()
     else:
         if not filename:
             filename = '%s_%s' % (model.replace('.', '_'), id)
             return request.make_response(filecontent,
                            [('Content-Type', 'application/octet-stream'),
                             ('Content-Disposition', content_disposition(filename))]) 
'''