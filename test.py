
import os
import asyncio

from .hcbapi import hcbapi


async def RunTest():  
    school = await hcbapi.GetSchoolInfo(os.environ['HCB_SCHOOLCODE'])
    schoolId = school.customer.id
    userInfo = await hcbapi.GetUserInfo(schoolId, os.environ['HCB_USERNAME'], os.environ['HCB_Password'])
    parentId = userInfo.account.id
    studentId = userInfo.linked_students.student[0].entity_id
    stops = await hcbapi.GetBusLocation(schoolId, parentId, studentId, AM_ID)
    print(stops.vehicle_location.address)

asyncio.run(RunTest())
