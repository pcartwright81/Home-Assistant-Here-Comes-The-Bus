import aiohttp
import untangle
from datetime import datetime
from xml.sax.saxutils import escape

url = "https://api.synovia.com/SynoviaApi.svc"


def GetSoapHeader():
    payload = '<?xml version="1.0" encoding="utf-8"?>'
    payload += '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
    payload += "<soap:Body>"
    return payload


def GetSoapFooter():
    payload = "</soap:Body>"
    payload += "</soap:Envelope>"
    return payload


def GetStandardHeaders():
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


async def GetSchoolInfo(schoolCode):
    payload = GetSoapHeader()
    payload += '<s1100 xmlns="http://tempuri.org/">'
    payload += "<P1>" + schoolCode + "</P1>"
    payload += "</s1100>"
    payload += GetSoapFooter()
    headers = GetStandardHeaders()
    headers["soapaction"] = "http://tempuri.org/ISynoviaApi/s1100"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers) as response:
            doc = untangle.parse(await response.text())
            customerAccount = (
                doc.s_Envelope.s_Body.s1100Response.s1100Result.SynoviaApi.ValidateCustomerAccountNumber
            )
            id = customerAccount.Customer["ID"]
            return {"Id": id}


async def GetUserInfo(schoolId, username, password):
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
            doc = untangle.parse(await response.text())
            login = doc.s_Envelope.s_Body.s1157Response.s1157Result.SynoviaApi.ParentLogin
            parentId = login.Account["ID"]
            students = [
                {"StudentId": student["EntityID"], "FirstName": student["FirstName"]}
                for student in login.LinkedStudents.Student
            ]
            return {"ParentId": parentId, "Students": students}


async def GetBusLocation(schoolId, parentId, studentId):
    nw = datetime.now()
    timeofDayId = "6E7A050E-0295-4200-8EDC-3611BB5DE1C1"  # default am
    if nw.hour >= 12:
        timeofDayId = "55632A13-35C5-4169-B872-F5ABDC25DF6A"  # pm
    payload = GetSoapHeader()
    payload += '<s1158 xmlns="http://tempuri.org/">'
    payload += "<P1>" + schoolId + "</P1>"
    payload += "<P2>" + parentId + "</P2>"
    payload += "<P3>" + studentId + "</P3>"
    payload += "<P4>" + timeofDayId + "</P4>"
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
            respText = await response.text()
            data =  {
                "Name": "",
                "Latitude": "",
                "Longitude": "",
                "Address": "",
                "Status": "Out of Service",
            }         
            if "VehicleLocation" not in respText:
                return data
            doc = untangle.parse(respText)
            vehicleLocation = (
                doc.s_Envelope.s_Body.s1158Response.s1158Result.SynoviaApi.GetStudentStopsAndScans.GetStudentStops.VehicleLocation
            )
            data["Name"] = vehicleLocation["Name"]
            data["Latitude"] = vehicleLocation["Latitude"]
            data["Longitude"] = vehicleLocation["Longitude"]
            data["Address"] = vehicleLocation["Address"]
            return data
