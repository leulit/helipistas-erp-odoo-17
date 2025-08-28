# -*- encoding: utf-8 -*-
import math
import base64
import os
from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from math import sin, cos, radians, acos
import calendar
from datetime import datetime, date, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo import SUPERUSER_ID
import unicodedata
import logging
import pytz
from reportlab.graphics.barcode import createBarcodeDrawing, getCodes
# from reportlab.lib.pagesizes import cm

_logger = logging.getLogger(__name__)


DENSIDAD_COMBUSTIBLE = {
    'R44': 0.71,
    'R22': 0.71,
    'EC120B': 0.79,
    'CABRI G2': 0.71
}

ROL_DIRECCION = 'Dirección'
ROL_SUPERADMIN = 'SuperAdmin'
ROL_RESP_FORMACION = 'Responsable formación'
ROL_RESP_SMS = 'Responsable SMS'
ROL_RESP_OPERACIONES = 'Responsable Operaciones'
ROL_FINANCIERO = 'Financiero'
ROL_PILOTO_EXTERNO = 'Piloto Externo'
ROL_COMERCIAL = 'Comercial'
ROL_RESP_COMERCIAL = 'Responsable Comercial'


STD_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
ISO_DATETIME_FORMAT = "%Y%m%d%H%M%S"
STD_TIME_FORMAT = "%H:%M:%S"

STD_DATETIME_NO_SECONDS_FORMAT = "%Y-%m-%d %H:%M"

STD_DATE_FORMAT = "%Y-%m-%d"
ISO_DATE_FORMAT = "%Y%m%d"
ESP_DATE_FORMAT = "%d-%m-%Y"


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def chunk_based_on_size(lst, n):
    for x in range(0, len(lst), n):
        each_chunk = lst[x: n+x]

        if len(each_chunk) < n:
            each_chunk = each_chunk + [None for y in range(n-len(each_chunk))]
        yield each_chunk

        
def getStrTimeUTC(fecha, hora, strTimeZone):  
    try:
        date2 = leulit_float_time_to_str( hora )
        date1 = fecha.strftime("%Y-%m-%d")
        tira =  date1+" "+date2
        valor = datetime.strptime(tira,"%Y-%m-%d %H:%M")
        tz = pytz.timezone(strTimeZone)
        mtz = tz.localize(datetime(valor.year, valor.month, valor.day, valor.hour, valor.minute))
        dt_utc = mtz.astimezone(pytz.timezone('UTC'))
        dt_utc = dt_utc.replace(tzinfo=None)
        result = dt_utc.strftime("%H:%M")
        return result
    except Exception as e:
        _logger.error("getStrTimeUTC %r",e)
        return "00:00"

def getPropertiesArray(object):
    properties = [a for a in dir(object) if not a.startswith('__') and not a.startswith('_')]
    dictionario = {}
    for property in properties:
        if not callable(getattr(object, property)):
            dictionario.update({property: getattr(object,property)})
    return dictionario


def freeze(d):
    if isinstance(d, dict):
        return frozenset((key, freeze(value)) for key, value in d.items())
    elif isinstance(d, list):
        return tuple(freeze(value) for value in d)
    return d

def getHashOfData(data):
    hashCode = hash(freeze(data)) 
    return hashCode if hashCode > 0 else (hashCode * -1)


def str_date_format(fecha, formatOrigen="%Y-%m-%d", formatDestino="%d-%m-%Y"):
    # if not isinstance(fecha, datetime):
    #     fecha = datetime.strptime(fecha, formatOrigen)
    fecha = fecha.strftime( formatDestino )
    return fecha


def str_today(self):
    return datetime.now().strftime("%Y-%m-%d")


def getStartEndMonth(strfecha=False):
    if strfecha:
        objfecha = datetime.strptime(strfecha, STD_DATE_FORMAT)
        monthrange = calendar.monthrange(objfecha.year, objfecha.month)
        startmonth = "{0}-{1}-01".format(objfecha.year, pad_left(objfecha.month, 2))
        endmonth = "{0}-{1}-{2}".format(objfecha.year, pad_left(objfecha.month, 2), pad_left(monthrange[1],2))
        return {
            'startmonth' : startmonth,
            'endmonth' : endmonth,
            'month' : objfecha.month
        }
    else:
        return False


def startEndMonth(objfecha=False):
    monthrange = calendar.monthrange(objfecha.year, objfecha.month)
    startmonth = "{0}-{1}-01".format(objfecha.year, pad_left(objfecha.month, 2))
    endmonth = "{0}-{1}-{2}".format(objfecha.year, pad_left(objfecha.month, 2), pad_left(monthrange[1],2))
    return {
        'startmonth' : datetime.strptime(startmonth, STD_DATE_FORMAT),
        'endmonth' : datetime.strptime(endmonth, STD_DATE_FORMAT),
        'month' : objfecha.month
    }



def getStartEndYear(strfecha=False):
    if strfecha:
        objfecha = datetime.strptime(strfecha, STD_DATE_FORMAT)
        startyear = "{0}-01-01".format(objfecha.year)
        endyear = "{0}-12-31".format(objfecha.year)
        return {
            'startyear' : startyear,
            'endyear' : endyear,
            'year': objfecha.year
        }
    else:
        return False     


def startEndYear(objfecha=False):
    startyear = "{0}-01-01".format(objfecha.year)
    endyear = "{0}-12-31".format(objfecha.year)
    return {
        'startyear' : startyear,
        'endyear' : endyear,
        'year': objfecha.year
    }


def isoDateTimeStrToDefaultDateStr(isodatetimestr):
    fecha = datetime.strptime(isodatetimestr, ISO_DATETIME_FORMAT)
    fecha = fecha.strftime(STD_DATE_FORMAT)
    return fecha


def str_date_to_date(fecha):
    try:
        if not isinstance(fecha, datetime):
            if fecha:
                start = datetime.strptime(fecha, "%Y-%m-%d")
            else:
                return False
        else:
            start = fecha
        return start
    except ValueError:
        _logger.error("-->str_date_to_datetime---> ValueError = %r",ValueError)
        return False

def hlp_float_time_convert(float_val):
    factor = float_val < 0 and -1 or 1
    val = abs(float_val)
    horas = factor * int(math.floor(val))
    minutos = int(round((val % 1) * 60))
    if minutos >= 60:
        minutos = 0
        horas += 1
    return horas, minutos

def hlp_float_time_to_str(float_val):
    if float_val == None:
        return "00:00"
    else:
        datos = hlp_float_time_convert(float_val)
        tira = "%02d:%02d" % (datos[0], datos[1])
        return tira

def removeCharsFromStr(tira, chars):
    for ch in chars:
        if ch in tira:
            tira = tira.replace(ch,"")
    return tira

def pad_left(n, width, pad="0"):
    return ((pad * width) + str(n))[-width:]

# def loggerByEmployee(s, dat, employee):
#     if employee == 22:
#         _logger.error("--> lbe00 --> {0} %r".format(s),dat)

def getObjCompany(self,cr,uid,id):
    user = self.env('res.users').browse(cr, uid, id)[0]
    objCompany = user.company_id
    return objCompany


def str_date_less(fecha, fecha_limite):    
    if not isinstance(fecha, datetime) and not isinstance(fecha, date):
        fecha = datetime.strptime(fecha, "%Y-%m-%d").date()
    if not isinstance(fecha_limite, datetime) and not isinstance(fecha_limite, date):
        fecha_limite = datetime.strptime(fecha_limite, "%Y-%m-%d").date()
    return fecha <= fecha_limite

def intersection(lst1, lst2):
    return set(lst1).intersection(lst2)
    #return list(set(lst1) & set(lst2))


def getOverlapedIntervals(intervals):
    overlapping = [ [x,y] for x in intervals for y in intervals if x is not y and x[1]>y[0] and x[0]<y[0] ]
    return overlapping


def listToStr(lista, separator=','):
    tira = ','.join(map(str, lista))
    return tira

def merge_intervals(v):
    if v == None or len(v) == 0 :
        return None
    result = []
    result.append([v[0][0], v[0][1]])
    for i in range(1, len(v)):
        x1 = v[i][0]
        y1 = v[i][1]
        x2 = result[len(result) - 1][0]
        y2 = result[len(result) - 1][1]
        if y2 >= x1:
            result[len(result) - 1][1] = max(y1, y2)
        else:
            result.append([x1, y1])
    return result

def mergeRanges(rows, start_key, end_key, id_key):
    if len(rows) > 1:
        ranges = sorted(rows, key=lambda x: x[start_key])
        saved = dict(ranges[0])
        for range_set in sorted(ranges, key=lambda x: x[start_key]):
            if range_set[start_key] <= saved[end_key]:
                saved[end_key] = max(saved[end_key], range_set[end_key])
            else:
                yield dict(saved)
                saved[start_key] = range_set[start_key]
                saved[end_key] = range_set[end_key]
                saved[id_key] = range_set[id_key]
        yield dict(saved)
    else:
        saved = {
            start_key   : rows[0][start_key],
            end_key     : rows[0][end_key],
            id_key      : rows[0][id_key]
        }
        yield dict(saved)


def getStrToday():
    return datetime.now().strftime(STD_DATE_FORMAT)

def getDateToday():
    hoy = datetime.now()
    if isinstance(hoy, datetime):
        return hoy.date()
    else:
        return hoy

def datetimeToDate(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, basestring):
        return strFechaToObj(value)
    return value


def getStrTodayFullIsoFormat():
    return datetime.now().strftime(ISO_DATETIME_FORMAT)

def _allows_thread(name):
    import threading
    for th in threading.enumerate():
        if th.getName() == name:
            return False
    return True

def async_task(cr, uid, target, context=None):
    import sys
    import traceback
    import psycopg2

    try:
        target(cr, uid, context)
        return True
    except Exception as exc:
        cr.rollback()
        ex_type, sys_exc, tb = sys.exc_info()
        tb_msg = ''.join(traceback.format_tb(tb, 30))
        msg = _("Unexpected exception.\n %s \n %s" % (repr(exc), tb_msg))
        _logger.error("-- async_task --> err 2 -> %r ", msg)
    finally:
        try:
            cr.commit()
        except psycopg2.Error:
            _logger.exception('-- async_task --> err 3 -> Can not do final commit')
        cr.close()
        _logger.exception('-- async_task --> TAREA FINALIZADA')


def getMaxDate(fecha1, fecha2):
    if not isinstance(fecha1, datetime):
        fecha1 = datetime.strptime(fecha1, STD_DATE_FORMAT)
    if not isinstance(fecha2, datetime):
        fecha2 = datetime.strptime(fecha2, STD_DATE_FORMAT)

    if fecha1 > fecha2:
        return fecha1
    else:
        return fecha2


def formatFecha(fecha, formatDestino = STD_DATE_FORMAT, formatOrigen = STD_DATE_FORMAT ):
    if not isinstance(fecha, datetime):
        fecha = datetime.strptime(fecha, formatOrigen)
    fecha = fecha.strftime( formatDestino )
    return fecha

def strFechaFormat(fecha, format):
    fecha = datetime.strptime(fecha, STD_DATE_FORMAT)
    fecha = fecha.strftime(format)
    return fecha

def objFechaToStr( fecha ):
    if isinstance(fecha, str):
        return fecha
    elif isinstance(fecha, date):
        fecha = fecha.strftime( STD_DATE_FORMAT )
        return fecha
    elif isinstance(fecha, datetime):
        fecha = fecha.date().strftime( STD_DATE_FORMAT )
        return fecha

def endMonth( fecha, return_str = True ):
    if not isinstance(fecha, datetime) and not isinstance(fecha, date):
        fecha = datetime.strptime(fecha, STD_DATE_FORMAT)
    last_day_month = calendar.monthrange(fecha.year, fecha.month)[1]
    str1 = "{0}-{1}-{2}".format(fecha.year, fecha.month, last_day_month)
    if return_str:
        return str1
    else:
        return strFechaToObj( str1 )


def startMonth( fecha, return_str = True ):
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, STD_DATE_FORMAT)
    str1 = "{0}-{1}-01".format(fecha.year, fecha.month)
    if return_str:
        return str1
    else:
        return strFechaToObj( str1 )


def daysOfMonth( fecha ):
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, STD_DATE_FORMAT)
    last_day_month = calendar.monthrange(fecha.year, fecha.month)[1]
    return last_day_month


def strFechaToObj(fecha):
    if isinstance(fecha, str):
        return datetime.strptime(fecha, STD_DATE_FORMAT)
    else:
        if isinstance(fecha, datetime):
            return fecha.date()
        else:
            return fecha

def strFechaToDate(fecha):
    obj = strFechaToObj(fecha)
    if obj:
        if isinstance(obj, datetime):
            return obj.date()
        else:
            return obj


def set_key(dictionary, key, value):
    if key not in dictionary:
        dictionary[key] = value
    elif type(dictionary[key]) == list:
        dictionary[key].append(value)
    else:
        dictionary[key] = [dictionary[key], value]
    return dictionary


# def get_qr_base64_image(valor, width, height, hr, code='QR'):
#     """ genrating image for barcode """
#     try:
#         ret_val = createBarcodeDrawing(code, value=str(valor), width=width * cm, height=height * cm)
#         return base64.encodestring(ret_val.asString('jpg'))
#     except Exception as e:
#         _logger.error('Error %r', e)
#         return ""


def get_vuelo_disponibilidad(tiempo):
    return tiempo + 1.25


def salto_linea(texto):
    return texto.replace('\n', '<br />')


def stringDate(date):
    stringdate = ''
    if date:
        mes = ''
        if date.month == 1:
            mes = 'Enero'
        elif date.month == 2:
            mes = 'Febrero'
        elif date.month == 3:
            mes = 'Marzo'
        elif date.month == 4:
            mes = 'Abril'
        elif date.month == 5:
            mes = 'Mayo'
        elif date.month == 6:
            mes = 'Junio'
        elif date.month == 7:
            mes = 'Julio'
        elif date.month == 8:
            mes = 'Agosto'
        elif date.month == 9:
            mes = 'Septiembre'
        elif date.month == 10:
            mes = 'Octubre'
        elif date.month == 11:
            mes = 'Noviembre'
        elif date.month == 12:
            mes = 'Diciembre'
        stringdate = str(date.day) + ' de ' + mes + ' de ' + str(date.year)
    return stringdate


def stringDatetoNumber(date):
    if date:
        mes = 0
        if date == 'Enero':
            mes = 1
        elif date == 'Febrero':
            mes = 2
        elif date == 'Marzo':
            mes = 3
        elif date == 'Abril':
            mes = 4
        elif date == 'Mayo':
            mes = 5
        elif date == 'Junio':
            mes = 6
        elif date == 'Julio':
            mes = 7
        elif date == 'Agosto':
            mes = 8
        elif date == 'Septiembre':
            mes = 9
        elif date == 'Octubre':
            mes = 10
        elif date == 'Noviembre':
            mes = 11
        elif date == 'Diciembre':
            mes = 12
    return mes


def ampliarLimiteHorasMensuales(month, limit, horas, tiempo):
    if month == 1:
        if limit.horas_enero != 0.0:
            if horas.horas_enero + tiempo > limit.horas_enero:
                return True
    elif month == 2:
        if limit.horas_febrero != 0.0:
            if horas.horas_febrero + tiempo > limit.horas_febrero:
                return True
    elif month == 3:
        if limit.horas_marzo != 0.0:
            if horas.horas_marzo + tiempo > limit.horas_marzo:
                return True
    elif month == 4:
        if limit.horas_abril != 0.0:
            if horas.horas_abril + tiempo > limit.horas_abril:
                return True
    elif month == 5:
        if limit.horas_mayo != 0.0:
            if horas.horas_mayo + tiempo > limit.horas_mayo:
                return True
    elif month == 6:
        if limit.horas_junio != 0.0:
            if horas.horas_junio + tiempo > limit.horas_junio:
                return True
    elif month == 7:
        if limit.horas_julio != 0.0:
            if horas.horas_julio + tiempo > limit.horas_julio:
                return True
    elif month == 8:
        if limit.horas_agosto != 0.0:
            if horas.horas_agosto + tiempo > limit.horas_agosto:
                return True
    elif month == 9:
        if limit.horas_septiembre != 0.0:
            if horas.horas_septiembre + tiempo > limit.horas_septiembre:
                return True
    elif month == 10:
        if limit.horas_octubre != 0.0:
            if horas.horas_octubre + tiempo > limit.horas_octubre:
                return True
    elif month == 11:
        if limit.horas_noviembre != 0.0:
            if horas.horas_noviembre + tiempo > limit.horas_noviembre:
                return True
    elif month == 12:
        if limit.horas_diciembre != 0.0:
            if horas.horas_diciembre + tiempo > limit.horas_diciembre:
                return True
    return False


def numbertoStingMonth(date):
    if date:
        mes = ''
        if date == 1:
            mes = 'Enero'
        elif date == 2:
            mes = 'Febrero'
        elif date == 3:
            mes = 'Marzo'
        elif date == 4:
            mes = 'Abril'
        elif date == 5:
            mes = 'Mayo'
        elif date == 6:
            mes = 'Junio'
        elif date == 7:
            mes = 'Julio'
        elif date == 8:
            mes = 'Agosto'
        elif date == 9:
            mes = 'Septiembre'
        elif date == 10:
            mes = 'Octubre'
        elif date == 11:
            mes = 'Noviembre'
        elif date == 12:
            mes = 'Diciembre'
    return mes


def daysMonth(mes):
    days = 0
    if mes == 1:
        days = 31
    elif mes == 2:
        days = 28
    elif mes == 3:
        days = 31
    elif mes == 4:
        days = 30
    elif mes == 5:
        days = 31
    elif mes == 6:
        days = 30
    elif mes == 7:
        days = 31
    elif mes == 8:
        days = 31
    elif mes == 9:
        days = 30
    elif mes == 10:
        days = 31
    elif mes == 11:
        days = 30
    elif mes == 12:
        days = 31
    return days


def _calculo_calendario_dias(last_date, meses):
    valor = datetime.strptime(last_date, '%Y-%m-%d')
    new_fecha = (valor + relativedelta(months=meses))
    dias = (new_fecha - valor).days
    year_valor = valor.year
    year_fecha = new_fecha.year
    for year in range(year_valor, year_fecha + 1):
        if year % 4 == 0:
            if year % 100 != 0 or year % 400 == 0:
                dias = dias - 1
    return dias


def cal_days_diff(a, b):
    #A = a.replace(hour=0, minute=0, second=0, microsecond=0)
    #B = b.replace(hour=0, minute=0, second=0, microsecond=0)
    if isinstance(a, datetime):
        a = a.date()
    if isinstance(b, datetime):
        b = b.date()
    A = a
    B = b
    return (A - B).days


def eliminaTagsHtml(texto):
    a = 0
    while a >= 0:
        a = texto.find("<")
        if a >= 0:
            b = texto.find(">", a)
            texto = texto[:a] + texto[b + 1:]
    return texto


def leulit_float_time_convert(float_val):
    factor = float_val < 0 and -1 or 1
    val = abs(float_val)
    horas = factor * int(math.floor(val))
    minutos = int(round((val % 1) * 60))
    if minutos >= 60:
        minutos = 0
        horas += 1
    return horas, minutos


def leulit_float_minutes_to_str(float_val):
    hours = float_val / 60
    return leulit_float_time_to_str(hours)

def leulit_float_time_to_minutes(float_val):
    datos = leulit_float_time_convert(float_val)
    minutos = datos[0] * 60 + datos[1]
    return minutos


def leulit_float_time_to_str(float_val):
    if float_val == None:
        return "00:00"
    else:
        datos = leulit_float_time_convert(float_val)
        tira = "%02d:%02d" % (datos[0], datos[1])
        return tira


def leulit_str_to_float_time(time_string):
    fields = time_string.split(":")
    hours = fields[0] if len(fields) > 0 else 0.0
    minutes = fields[1] if len(fields) > 1 else 0.0
    seconds = fields[2] if len(fields) > 2 else 0.0
    return float(hours) + (float(minutes) / 60.0) + (float(seconds) / pow(60.0, 2))


def leulit_datetime_to_float_time(odatetime):
    if not isinstance(odatetime, date):
        odatetime = odatetime.strptime("%Y-%m-%d %H:%M:%S")
    else:
        odatetime = odatetime
    time_string = odatetime.strftime("%H:%M")
    fields = time_string.split(":")
    hours = fields[0] if len(fields) > 0 else 0.0
    minutes = fields[1] if len(fields) > 1 else 0.0
    seconds = fields[2] if len(fields) > 2 else 0.0
    return float(hours) + (float(minutes) / 60.0) + (float(seconds) / pow(60.0, 2))


def getLabelFromSelection( valor, selection ):
    lista = selection
    matching = [s for s in lista if valor in s]
    if matching:
        if len(matching) > 0:
            if len(matching[0]) > 0:
                return matching[0][1]
    return ''


def _get_tipo_trabajo():
    return (
        ('AOC', 'AOC'),
        ('Trabajo Aereo', 'Trabajo Aereo'),
        ('Escuela', 'Escuela'),
        ('LCI', 'LCI'),
    )


def leulit_get_tipos_planificacion():
    return (
        ('15', 'Administración'),
        ('1', 'CINEFLEX'),
        ('14', 'Campaña bomberos'),
        ('21', 'Operador Campaña bomberos'),
        ('19', 'Comercial'),
        ('12', 'Entrenamiento compañía'),
        ('2', 'Escuela Vuelo'),
        ('13', 'Escuela Teórica'),
        ('3', 'Helitaxi'),
        ('20', 'IT'),
        ('17', 'No disponible (vacaciones, ausencias, etc..)'),
        ('16', 'Otros'),
        ('4', 'NCO'),
        ('5', 'Ruta AIGÜES TARRAGONA'),
        ('6', 'Ruta CLH'),
        ('22', 'Ruta ATL'),
        ('7', 'Ruta ENAGAS'),
        ('8', 'Ruta GAS NATURAL'),
        ('9', 'Ruta REPSOL'),
        ('18', 'Taller'),
        ('10', 'Trabajo aereo'),
        ('11', 'Vuelo Turístico'),
    )


def leulit_get_tipos_movimiento():
    return (
        ('compra', 'Compra'),
        ('movimiento_interno', 'Movimiento interno'),
        ('instalacion', 'Instalación'),
        ('desinstalacion', 'Desinstalación'),
        ('venta', 'Venta'),
        ('cesion', 'Cesión'),
        ('baja', 'Baja / Material inútil'),
        ('reparacion', 'Reparación')
    )


def leulit_get_compania_interna():
    return (
        ('1', 'Helipistas'),
        ('2', 'Ícarus')
    )


def leulit_get_desc_tipos_planificacion( valor ):
    return getLabelFromSelection( valor, leulit_get_tipos_planificacion())

def leulit_get_estados_anomalias():
    return (
        ('pending', 'Pendiente'),
        ('deferred', 'Diferido'),
        ('closed', 'Cerrado'),
        ('flightcanceled', 'Vuelo cancelado'),
    )


def leulit_get_meses():
    return (
        ('Enero', 'Enero'),
        ('Febrero', 'Febrero'),
        ('Marzo', 'Marzo'),
        ('Abril', 'Abril'),
        ('Mayo', 'Mayo'),
        ('Junio', 'Junio'),
        ('Julio', 'Julio'),
        ('Agosto', 'Agosto'),
        ('Septiembre', 'Septiembre'),
        ('Octubre', 'Octubre'),
        ('Noviembre', 'Noviembre'),
        ('Diciembre', 'Diciembre'),
    )


def leulit_get_estados_ot_mantenimiento():
    return (
        ('active', 'Activa'),
        ('abierta', 'Abierta'),
        ('aceptada', 'Aceptada'),
        ('entaller', 'En Taller'),
        ('realizada', 'Realizada'),
        ('cerrada', 'Cerrada'),
        ('cancelada', 'Cancelada'),
    )


def leulit_getTipoOperacion():
    return (
        ('AOC EH05', 'AOC EH05'),
        ('AOC P3', 'AOC P3'),
        ('ATO', 'ATO'),
        ('TTAA', 'TTAA'),
    )

def hlp_float_minutes_to_str(float_val):
    hours = float_val / 60
    return hlp_float_time_to_str(hours)    

def hlp_float_time_to_minutes(float_val):
    datos = hlp_float_time_convert(float_val)
    minutos = datos[0] * 60 + datos[1]
    return minutos


def leulit_get_tipos_helicopteros():
    return (
        ('AS350', 'AS350'),
        ('EC120B', 'EC120B'),
        ('EC130', 'EC130'),
        ('R22', 'R22'),
        ('R44', 'R44'),
        ('CABRI G2', 'CABRI G2'),
        ('DJI', 'DJI'),
    )


def getSuperUserId():
    return SUPERUSER_ID


# **************************************************************************************************** #
#  Name:                isSuperUser
# Description:         Check that the user is or isn't the superuser (True or False)
# Imports:             -
# Author:              Gemma Flores Castillo
# Last Modification:   2017 - 07 - 13
# **************************************************************************************************** #
def isSuperUser(uid):
    return SUPERUSER_ID == uid


def leulit_get_states_machine():
    return (
        ('En servicio', 'En servicio'),
        ('En taller', 'En taller'),
    )


def leulit_get_desc_not_need_notam():
    return (
        ('vuelo-local', 'Vuelo local'),
        ('otros', 'Otros'),
    )


def leulit_get_estados_reminder():
    return (
        ('on', 'Activa'),
        ('out', 'Cancelada'),
        ('end', 'Finalizada'),
        ('off', 'Inactiva'),
        ('over', 'Superada'),
    )

def leulit_get_desc_estado_reminder( valor ):
    lista = leulit_get_estados_reminder()
    matching = [s for s in lista if valor in s]
    return matching[0][1]

def leulit_get_fabricantes():
    return (
        ('robinson', 'Robinson'),
        ('eurocopter', 'Eurocopter'),
        ('guimbal', 'Guimbal'),
        ('dji', 'DJI')
    )

def leulit_get_desc_fabricante( valor ):
    lista = leulit_get_fabricantes()
    matching = [s for s in lista if valor in s]
    return matching[0][1]

def leulit_get_tipo_tarea():
    return (
        ('sale.order', 'Presupuesto'),
        ('crm.phonecall', 'Llamada'),
        ('calendar.event', 'Visita'),
        ('leulit.tarea', 'Tarea'),
    )

def leulit_get_tipo_tarea_proc():
    return (
        ('clase', 'Clase'),
        ('tarea', 'Tarea'),
        ('vuelo', 'Vuelo'),
    )

def leulit_get_dangerlevel():
    return (
        ('normal', 'Normal'),
        ('info', 'Aviso'),
        ('warn', 'Alerta'),
        ('error', 'Peligro'),
        ('critical', 'Crítico'),
    )


def leulit_get_desc_tipomotor( valor ):
    return getLabelFromSelection( valor, leulit_get_tipomotor())


def leulit_get_tipomotor():
    return (
           ('piston','Pistón'),
           ('turbina','Turbina'),
           ('rpas','RPAS'),
        )

def leulit_get_desc_dangerlevel( valor ):
    lista = leulit_get_dangerlevel()
    matching = [s for s in lista if valor in s]
    return matching[0][1]


def leulit_get_default_dangerlevel():
    return 'normal'


def leulit_get_tipos_reminder():
    return (
        ('1', 'Prórroga'),
        ('2', 'Renovación'),
        ('3', 'Recomendación'),
    )

def leulit_get_desc_tipo_reminder( valor ):
    lista = leulit_get_tipos_reminder()
    matching = [s for s in lista if valor in s]
    return matching[0][1]


def leulit_get_default_estado_reminder():
    return 'on'


def leulit_get_earth_radius():
    return 6371000


def calc_dist_fixed(lat_a, long_a, lat_b, long_b):
    try:
        lat_a = radians(lat_a)
        lat_b = radians(lat_b)
        delta_long = radians(long_a - long_b)
        cos_x = (sin(lat_a) * sin(lat_b) + cos(lat_a) * cos(lat_b) * cos(delta_long))
        return acos(cos_x) * leulit_get_earth_radius()
    except Exception as e:
        _logger.error('utilitylib.calc_dist_fixed -> Exception = %r', str(e))
        return 0


def calc_rumbo(lat_a, long_a, lat_b, long_b):
    try:
        startLat = math.radians(lat_a)
        startLong = math.radians(long_a)
        endLat = math.radians(lat_b)
        endLong = math.radians(long_b)

        dLong = endLong - startLong

        dPhi = math.log(math.tan(endLat / 2.0 + math.pi / 4.0) / math.tan(startLat / 2.0 + math.pi / 4.0))
        if abs(dLong) > math.pi:
            if dLong > 0.0:
                dLong = -(2.0 * math.pi - dLong)
            else:
                dLong = (2.0 * math.pi + dLong)

        bearing = (math.degrees(math.atan2(dLong, dPhi)) + 360.0) % 360.0
        return bearing
    except Exception as e:
        _logger.error('utilitylib.calc_rumbo -> Exception = %r', str(e))
        return 0


def minDateTimes(date1, date2):
    if not date1 and date2:
        return date2
    if date1 and not date2:
        return date1
    if not date1 and not date2:
        return False

    date1 = datetime.strptime(date1, "%Y-%m-%d %H:%M:%S")
    date2 = datetime.strptime(date2, "%Y-%m-%d %H:%M:%S")
    if date1 > date2:
        return date2
    else:
        return date1


def maxDateTimes(date1, date2):
    if not date1 and date2:
        return date2
    if date1 and not date2:
        return date1
    if not date1 and not date2:
        return False

    date1 = datetime.strptime(date1, "%Y-%m-%d %H:%M:%S")
    date2 = datetime.strptime(date2, "%Y-%m-%d %H:%M:%S")
    if date1 > date2:
        return date1
    else:
        return date2     



def isLessDateTimes(date1, date2):
    if not date1 and date2:
        return date2
    if date1 and not date2:
        return date1
    if not date1 and not date2:
        return False

    date1 = datetime.strptime(date1, "%Y-%m-%d %H:%M:%S")
    date2 = datetime.strptime(date2, "%Y-%m-%d %H:%M:%S")
    if date1 > date2:
        return False
    else:
        return True


def diff_times_in_minutes(time1, time2):
    hours = int(time1)
    minutes = (time1 * 60) % 60
    seconds = (time1 * 3600) % 60
    fecha1 = datetime.now()
    fecha1 = fecha1.replace(hour=int(hours), minute=int(minutes), second=int(seconds))
    hours = int(time2)
    minutes = (time2 * 60) % 60
    seconds = (time2 * 3600) % 60
    fecha2 = datetime.now()
    fecha2 = fecha2.replace(hour=int(hours), minute=int(minutes), second=int(seconds))
    diff = fecha2 - fecha1
    minutes = (diff.seconds) / 60
    return minutes


def add_minutes_to_decimal_time(tiempo, minutes):
    hours = int(tiempo)
    minutes = (tiempo * 60) % 60
    seconds = (tiempo * 3600) % 60
    fecha = datetime.now()
    fecha = fecha.replace(hour = int(hours), minute = int(minutes), second = int(seconds))
    fecha = fecha + timedelta(minutes = minutes)
    tira = fecha.strftime("%H:%M:%S")
    return time_string_to_decimals( tira )

def addDays(fecha, numOfDays, return_str = True  ):
    if not isinstance(fecha, datetime) and not isinstance(fecha, date) and fecha:
        fecha = datetime.strptime(fecha, STD_DATE_FORMAT)
    fecha = fecha + relativedelta(days=numOfDays)
    if return_str:
        return objFechaToStr( fecha )
    else:
        return fecha

def get_tiempo_vuelo_segundos(nm, kt):
    valor = 0
    if kt > 0:
        metros = convert_nauticmiles_metros(nm)
        metros_segundo = convert_nudos_metros_por_segundo(kt)
        if metros_segundo > 0:
            valor = metros / metros_segundo
        else:
            valor = 0
    return valor

def get_tiempo_vuelo_decimal( nm, kt):
    valor = get_tiempo_vuelo_segundos(nm, kt)
    if valor > 0:
        valor = valor / 3600
    return valor


def convert_nudos_metros_por_segundo(valor):
    # 1 kt = 0.51444444444 m/s

    if isinstance(valor,float) or isinstance(valor,int):
        return valor * 0.51444444444
    else:
        return 0


def convert_metros_nauticmiles( valor ):
    #1 m = 0.000539956803 nm
    if isinstance(valor,float) or isinstance(valor,int):
        return valor * 0.000539956803
    else:
        return 0

def convert_nauticmiles_metros( valor ):
    # 1nm = 1852m
    if isinstance(valor, float) or isinstance(valor, int):
        return valor * 1852
    else:
        return 0


def convert_metros_por_segundo_nudos( valor ):
    # 1 m/s = 1.94384 kt
    if isinstance(valor, float) or isinstance(valor, int):
        return valor * 1.94384
    else:
        return 0


def convert_litros_to_kg( litros, modelo ):
    valor = {
        'R44': 0.71,
        'R22': 0.71,
        'EC120B': 0.79,
        'CABRI G2': 0.71
    }.get(modelo, 0)
    return round(litros * valor, 2)

def convert_litros_to_gal( litros, modelo ):
    valor = 0.264172
    return round(litros * valor, 2)


def getModulePath():
    return os.path.abspath(os.path.dirname(__file__))


def getJasperReportsPath():
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), 'report/')


def thousandsSeparator(valor, locale=''):
    return '{0:.2}'.format(valor)


def clasificacion_riesgo(probabilidad, severidad):
    res = {}
    if probabilidad != False and severidad != False:
        riesgo = ''
        clas_riesgo = {
            '5A': 'Inaceptable',
            '4A': 'Inaceptable',
            '3A': 'Inaceptable',
            '5B': 'Inaceptable',
            '4B': 'Inaceptable',
            '5C': 'Inaceptable',
            '2A': 'Tolerable',
            '3B': 'Tolerable',
            '2B': 'Tolerable',
            '4C': 'Tolerable',
            '3C': 'Tolerable',
            '2C': 'Tolerable',
            '5D': 'Tolerable',
            '4D': 'Tolerable',
            '3D': 'Tolerable',
            '5E': 'Tolerable',
            '4E': 'Tolerable',
            '1A': 'Aceptable',
            '1B': 'Aceptable',
            '1C': 'Aceptable',
            '1D': 'Aceptable',
            '1E': 'Aceptable',
            '2D': 'Aceptable',
            '2E': 'Aceptable',
            '3E': 'Aceptable',
        }
        riesgo = probabilidad + severidad
        if riesgo in clas_riesgo.keys():
            res = clas_riesgo.get(riesgo)
        else:
            res = '            '
        return res

def condition(operand, left, right):
    if operand == '=':
        operand = '=='
        return eval(' '.join((str(left), operand, str(right))))
    elif operand == 'ilike':
        return eval("'{0}' {1} '{2}'".format(str(left), operand, str(right)))
    elif operand == 'like':
        return eval("'{0}' {1} '{2}'".format(str(left), operand, str(right)))



def get_res_user_from_hr_employee(self, cr, uid, ids):
    employee = self.env('hr.employee').browse(cr, uid, ids)
    if employee.user_id.id != False:
        user = self.env('res.users').browse(cr, uid, employee.user_id.id)
        if user.partner_id != []:
            return user.partner_id.id
    return False

def str_datetime_to_user_timezone(self, cr, uid, date):
    if not isinstance(date, datetime):
        start = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    else:
        start = date
    user = self.env('res.users').browse(cr, uid, uid)
    tz = pytz.timezone(user.tz) if user.tz else pytz.utc
    start = pytz.utc.localize(start).astimezone(tz)  # convert start in user's timezone
    return start.strftime("%Y-%m-%d %H:%M:%S")

def str_datetime_to_utc_timezone(self, cr, uid,  date):
    try:
        if not isinstance(date, datetime):
            start = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        else:
            start = date
        user = self.env('res.users').browse(cr, uid, uid)
        tz = pytz.timezone(user.tz) if user.tz else pytz.utc

        local_dt = tz.localize(start, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)
        return utc_dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def str_datetime_to_datetime(self, cr, uid,  date):
    try:
        if not isinstance(date, datetime):
            if date:
                start = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
            else:
                return False
        else:
            start = date
        return start
    except ValueError:
        _logger.error("-->str_datetime_to_datetime---> ValueError = %r",ValueError)
        return False


def str_date_from_datetime(self, date, format="%Y-%m-%d"):
    try:
        valor = self.str_datetime_to_datetime(date)
        if valor:
            return valor.strftime(format)
        return False
    except ValueError:
        _logger.error("-->str_date_from_datetime---> valor = %r",valor)
        return False


def str_time_from_datetime(self, cr, uid,  date, format="%H:%M:%S"):
    try:
        valor = self.str_datetime_to_datetime(cr, uid, date)
        if valor:
            valor = valor.strftime(format)
        return valor
    except ValueError:
        _logger.error("-->3str_time_from_datetime---> valor = %r",valor)
        return False


def decimal_time_from_datetime(self, cr, uid,  date):
    try:
        time_string = self.str_time_from_datetime(cr, uid, date, format="%H:%M:%S")
        if time_string:
            fields = time_string.split(":")
            hours = fields[0] if len(fields) > 0 else 0.0
            minutes = fields[1] if len(fields) > 1 else 0.0
            seconds = fields[2] if len(fields) > 2 else 0.0
            return float(hours) + (float(minutes) / 60.0) + (float(seconds) / pow(60.0, 2))            
        return False
    except ValueError:
        return False        

def decimal_time_from_datetime(self, cr, uid,  date):
    try:
        time_string = self.str_time_from_datetime(cr, uid, date, format="%H:%M:%S")
        if time_string:
            return self.time_string_to_decimals(cr, uid,  time_string)
        return False
    except ValueError:
        return False

def decimal_time_to_str(tiempo):
    hours = int(tiempo)
    hours = hours if hours <= 23 else 23
    minutes = (tiempo * 60) % 60
    seconds = (tiempo * 3600) % 60
    return "{0}:{1}:{2}".format(hours,"{0}".format(int(minutes)).zfill(2),"{0}".format(int(seconds)).zfill(2))

def decimal_time_to_str_without_seconds(tiempo):
    hours = int(tiempo)
    minutes = (tiempo * 60) % 60
    return "{0}:{1}".format(hours,"{:02}".format(int(round(minutes))))


def time_string_to_decimals(self, cr, uid,  time_string):
    fields = time_string.split(":")
    hours = fields[0] if len(fields) > 0 else 0.0
    minutes = fields[1] if len(fields) > 1 else 0.0
    seconds = fields[2] if len(fields) > 2 else 0.0
    return float(hours) + (float(minutes) / 60.0) + (float(seconds) / pow(60.0, 2))   
    
def date_difference_in_decimal(self, cr, uid,  data1, data2):    
    data1 = self.str_datetime_to_datetime(cr, uid, data1)
    data2 = self.str_datetime_to_datetime(cr, uid, data2)
    diff = data2 - data1
    seconds = diff.days * 24 * 3600 + diff.seconds
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    hours = hours + (days*24)    
    decimal = self.time_string_to_decimals(cr, uid, "{0}:{1}:{2}".format(hours, minutes, seconds))
    return decimal

def getHash(self, cr, uid, ids):
    if isinstance(ids, list):
        ids = ids[0]
    item = self.read(cr, uid, ids, [])
    if isinstance(item, list):
        item = item[0]
    tira = ''.join(item)
    import hashlib
    h = hashlib.md5()
    h.update(tira)
    return h.hexdigest()


def getHashWithSalt(self, cr, uid, ids):
    if isinstance(ids, list):
        ids = ids[0]
    tira = self.getHash(cr, uid, ids)
    SECRET_KEY = self.pool['res.users'].get_otp_secret(cr, uid)
    from werkzeug.security import pbkdf2_hex
    return pbkdf2_hex(tira, SECRET_KEY, iterations=1000)
    '''
    withSalt = "{0}-{1}".format(tira, SECRET_KEY)
    result = generate_password_hash(withSalt, "sha256")
    arrResult = result.split('$')
    return arrResult[2]
    '''

def compareEncryptedHash(self, cr, uid, id, hash):
    goodHash = self.getHashWithSalt(cr, uid, id)
    from hmac import compare_digest
    return compare_digest(goodHash, hash)


def get_date_time_str(strDate, time):
    strTime = decimal_time_to_str(time)
    return "{0} {1}".format(strDate, strTime)

def get_date_time(fecha, tiempo):
    strTime = decimal_time_to_str_without_seconds(tiempo)
    strFecha = fecha.strftime(STD_DATE_FORMAT)
    strFechaTime = "{0} {1}".format(strFecha, strTime)
    return datetime.strptime(strFechaTime, STD_DATETIME_NO_SECONDS_FORMAT)


def rowsToDict(cursor, rows):
    rowsresult = []
    for row in rows:
        obj = {}
        for (attr, val) in zip((d[0] for d in cursor.description), row):
            #obj.append({attr:val})
            obj[attr] = val
        rowsresult.append(obj)
    return rowsresult

def str_date_less_equal_today(fecha):
    hoy = datetime.now()
    if isinstance(hoy, datetime):
        hoy = hoy.date()
    if not isinstance(fecha, datetime) and not isinstance(fecha, date):
        fecha = datetime.strptime(fecha, "%Y-%m-%d").date()
    return fecha <= hoy

def date_less_equal_today(fecha):
    hoy = datetime.now()
    if isinstance(hoy, datetime):
        hoy = hoy.date()
    if not isinstance(fecha, datetime) or not isinstance(fecha, date):
        fecha = datetime.strptime(fecha, "%Y-%m-%d").date()
    return fecha <= hoy


def runQuery(cursor, sql):
    cursor.execute(sql)
    rows = cursor.fetchall()
    return rowsToDict(cursor, rows)

def runQueryReturnOne(cursor, sql):
    cursor.execute(sql)
    rows = cursor.fetchall()
    items = rowsToDict(cursor, rows)
    if len(items) > 0:
        return items[0]
    else:
        return False

