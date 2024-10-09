from typing import List


class StudentStopZone:
    student_entity_id: str
    zone_id: int
    radius: str
    latitude: str
    longitude: str
    zone_geostring: str
    time_of_day_id: str
    stop_id: str
    stop_name: str
    stop_latitude: str
    stop_longitude: str

    def __init__(
        self,
        student_entity_id: str,
        zone_id: int,
        radius: str,
        latitude: str,
        longitude: str,
        zone_geostring: str,
        time_of_day_id: str,
        stop_id: str,
        stop_name: str,
        stop_latitude: str,
        stop_longitude: str,
    ) -> None:
        self.student_entity_id = student_entity_id
        self.zone_id = zone_id
        self.radius = radius
        self.latitude = latitude
        self.longitude = longitude
        self.zone_geostring = zone_geostring
        self.time_of_day_id = time_of_day_id
        self.stop_id = stop_id
        self.stop_name = stop_name
        self.stop_latitude = stop_latitude
        self.stop_longitude = stop_longitude


class GetAccountZones:
    student_stop_zone: List[StudentStopZone]

    def __init__(self, student_stop_zone: List[StudentStopZone]) -> None:
        self.student_stop_zone = student_stop_zone


class Status:
    code: int
    message: str
    next_id: int
    next_call_time: str

    def __init__(
        self, code: int, message: str, next_id: int, next_call_time: str
    ) -> None:
        self.code = code
        self.message = message
        self.next_id = next_id
        self.next_call_time = next_call_time


class SynoviaAPI:
    status: Status
    get_account_zones: GetAccountZones
    xmlns: str
    xmlns_xsi: str
    xsi_schema_location: str
    version: str

    def __init__(
        self,
        status: Status,
        get_account_zones: GetAccountZones,
        xmlns: str,
        xmlns_xsi: str,
        xsi_schema_location: str,
        version: str,
    ) -> None:
        self.status = status
        self.get_account_zones = get_account_zones
        self.xmlns = xmlns
        self.xmlns_xsi = xmlns_xsi
        self.xsi_schema_location = xsi_schema_location
        self.version = version


class S1133Result:
    synovia_api: SynoviaAPI

    def __init__(self, synovia_api: SynoviaAPI) -> None:
        self.synovia_api = synovia_api


class S1133Response:
    s1133_result: S1133Result
    xmlns: str

    def __init__(self, s1133_result: S1133Result, xmlns: str) -> None:
        self.s1133_result = s1133_result
        self.xmlns = xmlns


class Body:
    s1133_response: S1133Response
    prefix: str

    def __init__(self, s1133_response: S1133Response, prefix: str) -> None:
        self.s1133_response = s1133_response
        self.prefix = prefix


class Envelope:
    body: Body
    xmlns_s: str
    prefix: str

    def __init__(self, body: Body, xmlns_s: str, prefix: str) -> None:
        self.body = body
        self.xmlns_s = xmlns_s
        self.prefix = prefix


class S1133:
    envelope: Envelope

    def __init__(self, envelope: Envelope) -> None:
        self.envelope = envelope
