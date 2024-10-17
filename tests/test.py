"""Runs a simple test to make sure the api is up."""

import asyncio
import json
import os

from hcb_soap_client import HcbSoapClient


async def _run_test() -> None:
    client = HcbSoapClient()
    school = await client.get_school_info(os.environ["HCB_SCHOOLCODE"])
    school_id = school.customer.id
    user_info = await client.get_parent_info(
        school_id, os.environ["HCB_USERNAME"], os.environ["HCB_PASSWORD"]
    )
    parent_id = user_info.account.id
    student_id = user_info.linked_students.student[0].entity_id
    stops = await client.get_bus_info(school_id, parent_id, student_id, client.AM_ID)
    print(json.dumps(stops))  # noqa: T201
    print(  # noqa: T201
        await client.test_connection(
            os.environ["HCB_SCHOOLCODE"],
            os.environ["HCB_USERNAME"],
            os.environ["HCB_PASSWORD"],
        )
    )


asyncio.run(_run_test())
