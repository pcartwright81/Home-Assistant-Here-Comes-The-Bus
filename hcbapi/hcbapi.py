import aiohttp, xmltodict
import aiohttp
from xml.sax.saxutils import escape

from .S1158 import S1158, GetStudentStops
from .s1100 import (
    S1100,
    ValidateCustomerAccountNumber,
)
from .s1157 import S1157, ParentLogin

url = "https://api.synovia.com/SynoviaApi.svc"

AM_ID = "6E7A050E-0295-4200-8EDC-3611BB5DE1C1"
PM_ID = "55632A13-35C5-4169-B872-F5ABDC25DF6A"

def GetSoapHeader() -> str:
    payload = '<?xml version="1.0" encoding="utf-8"?>'
    payload += '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
    payload += "<soap:Body>"
    return payload


def GetSoapFooter() -> str:
    payload = "</soap:Body>"
    payload += "</soap:Envelope>"
    return payload


def GetStandardHeaders() -> str:
    return {
        "app-version": "3.6.0",
        "app-name": "hctb",
        "client-version": "3.6.0",
        "user-agent": "hctb/3.6.0 App-Press/3.6.0",
        "cache-control": "no-cache",
        "content-type": "text/xml",
        "host": "api.synovia.com",
        "connection": "Keep-Alive",
        "accept-encoding": "gzip",
        "cookie": "SRV=prdweb1",
    }


async def GetSchoolInfo(schoolCode: str) -> ValidateCustomerAccountNumber:
    payload = GetSoapHeader()
    payload += '<s1100 xmlns="http://tempuri.org/">'
    payload += "<P1>" + schoolCode + "</P1>"
    payload += "</s1100>"
    payload += GetSoapFooter()
    headers = GetStandardHeaders()
    headers["soapaction"] = "http://tempuri.org/ISynoviaApi/s1100"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers) as response:
            text = await response.text()
            o = xmltodict.parse(text)
            root = S1100.from_dict(o)
            return root.s_envelope.s_body.s1100_response.s1100_result.synovia_api.validate_customer_account_number


async def GetUserInfo(schoolId: str, username: str, password: str) -> ParentLogin:
    payload = GetSoapHeader()
    payload += '<s1157 xmlns="http://tempuri.org/">'
    payload += "<P1>" + schoolId + "</P1>"
    payload += "<P2>" + username + "</P2>"
    payload += "<P3>" + escape(password) + "</P3>"
    payload += "<P4>LookupItem_Source_Android</P4>"
    payload += "<P5>Android</P5>"
    payload += "<P6>3.6.0</P6>"
    payload += "<P7/>"
    payload += "</s1157>"
    payload += GetSoapFooter()
    headers = GetStandardHeaders()
    headers["soapaction"] = "http://tempuri.org/ISynoviaApi/s1157"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers) as response:
            text = await response.text()
            o = xmltodict.parse(text, force_list={"Student"})
            root = S1157.from_dict(o)
            return root.s_envelope.s_body.s1157_response.s1157_result.synovia_api.parent_login


async def GetBusLocation(
    schoolId: str, parentId: str, studentId: str, timeOfDayId: str
) -> GetStudentStops:
    payload = GetSoapHeader()
    payload += '<s1158 xmlns="http://tempuri.org/">'
    payload += "<P1>" + schoolId + "</P1>"
    payload += "<P2>" + parentId + "</P2>"
    payload += "<P3>" + studentId + "</P3>"
    payload += "<P4>" + timeOfDayId + "</P4>"
    payload += "<P5>true</P5>"
    payload += "<P6>false</P6>"
    payload += "<P7>10</P7>"
    payload += "<P8>14</P8>"
    payload += "<P9>english</P9>"
    payload += "</s1158>"
    payload += GetSoapFooter()
    headers = GetStandardHeaders()
    headers["soapaction"] = "http://tempuri.org/ISynoviaApi/s1158"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers) as response:
            text = await response.text()
            o = xmltodict.parse(text)
            root = S1158.from_dict(o)
            return root.s_envelope.s_body.s1158_response.s1158_result.synovia_api.get_student_stops_and_scans.get_student_stops
