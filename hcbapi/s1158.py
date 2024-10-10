from datetime import datetime
from uuid import UUID
from typing import Any, List, TypeVar, Callable, Type, cast
import dateutil.parser


T = TypeVar("T")


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_datetime(x: Any) -> datetime:
    return dateutil.parser.parse(x)


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


class StudentStop:
    name: str
    latitude: str
    longitude: str
    start_time: datetime
    stop_type: str
    substitute_vehicle_name: str
    vehicle_name: str
    stop_id: str
    arrival_time: datetime
    time_of_day_id: str
    vehicle_id: UUID
    esn: str
    tier_start_time: datetime
    bus_visibility_start_offset: int

    def __init__(
        self,
        name: str,
        latitude: str,
        longitude: str,
        start_time: datetime,
        stop_type: str,
        substitute_vehicle_name: str,
        vehicle_name: str,
        stop_id: str,
        arrival_time: datetime,
        time_of_day_id: str,
        vehicle_id: UUID,
        esn: str,
        tier_start_time: datetime,
        bus_visibility_start_offset: int,
    ) -> None:
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.start_time = start_time
        self.stop_type = stop_type
        self.substitute_vehicle_name = substitute_vehicle_name
        self.vehicle_name = vehicle_name
        self.stop_id = stop_id
        self.arrival_time = arrival_time
        self.time_of_day_id = time_of_day_id
        self.vehicle_id = vehicle_id
        self.esn = esn
        self.tier_start_time = tier_start_time
        self.bus_visibility_start_offset = bus_visibility_start_offset

    @staticmethod
    def from_dict(obj: Any) -> "StudentStop":
        assert isinstance(obj, dict)
        name = from_str(obj.get("@Name"))
        latitude = from_str(obj.get("@Latitude"))
        longitude = from_str(obj.get("@Longitude"))
        start_time = from_datetime(obj.get("@StartTime"))
        stop_type = from_str(obj.get("@StopType"))
        substitute_vehicle_name = from_str(obj.get("@SubstituteVehicleName"))
        vehicle_name = from_str(obj.get("@VehicleName"))
        stop_id = from_str(obj.get("@StopId"))
        arrival_time = from_datetime(obj.get("@ArrivalTime"))
        time_of_day_id = from_str(obj.get("@TimeOfDayId"))
        vehicle_id = UUID(obj.get("@VehicleId"))
        esn = from_str(obj.get("@Esn"))
        tier_start_time = from_datetime(obj.get("@TierStartTime"))
        bus_visibility_start_offset = int(
            from_str(obj.get("@BusVisibilityStartOffset"))
        )
        return StudentStop(
            name,
            latitude,
            longitude,
            start_time,
            stop_type,
            substitute_vehicle_name,
            vehicle_name,
            stop_id,
            arrival_time,
            time_of_day_id,
            vehicle_id,
            esn,
            tier_start_time,
            bus_visibility_start_offset,
        )

    def to_dict(self) -> dict:
        result: dict = {}
        result["@Name"] = from_str(self.name)
        result["@Latitude"] = from_str(self.latitude)
        result["@Longitude"] = from_str(self.longitude)
        result["@StartTime"] = self.start_time.isoformat()
        result["@StopType"] = from_str(self.stop_type)
        result["@SubstituteVehicleName"] = from_str(self.substitute_vehicle_name)
        result["@VehicleName"] = from_str(self.vehicle_name)
        result["@StopId"] = from_str(self.stop_id)
        result["@ArrivalTime"] = self.arrival_time.isoformat()
        result["@TimeOfDayId"] = from_str(self.time_of_day_id)
        result["@VehicleId"] = str(self.vehicle_id)
        result["@Esn"] = from_str(self.esn)
        result["@TierStartTime"] = self.tier_start_time.isoformat()
        result["@BusVisibilityStartOffset"] = from_str(
            str(self.bus_visibility_start_offset)
        )
        return result


class StudentStops:
    student_stop: List[StudentStop]

    def __init__(self, student_stop: List[StudentStop]) -> None:
        self.student_stop = student_stop

    @staticmethod
    def from_dict(obj: Any) -> "StudentStops":
        if(obj is None):
            return None
        assert isinstance(obj, dict)
        student_stop = from_list(StudentStop.from_dict, obj.get("StudentStop"))
        return StudentStops(student_stop)

    def to_dict(self) -> dict:
        result: dict = {}
        result["StudentStop"] = from_list(
            lambda x: to_class(StudentStop, x), self.student_stop
        )
        return result


class VehicleLocation:
    name: str
    latitude: str
    longitude: str
    log_time: str
    ignition: str
    latent: str
    time_zone_offset: int
    heading: str
    speed: int
    address: str
    message_code: int
    display_on_map: str

    def __init__(
        self,
        name: str,
        latitude: str,
        longitude: str,
        log_time: str,
        ignition: str,
        latent: str,
        time_zone_offset: int,
        heading: str,
        speed: int,
        address: str,
        message_code: int,
        display_on_map: str,
    ) -> None:
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.log_time = log_time
        self.ignition = ignition
        self.latent = latent
        self.time_zone_offset = time_zone_offset
        self.heading = heading
        self.speed = speed
        self.address = address
        self.message_code = message_code
        self.display_on_map = display_on_map

    @staticmethod
    def from_dict(obj: Any) -> "VehicleLocation":
        if(obj is None):
            return None
        assert isinstance(obj, dict)
        name = from_str(obj.get("@Name"))
        latitude = from_str(obj.get("@Latitude"))
        longitude = from_str(obj.get("@Longitude"))
        log_time = from_str(obj.get("@LogTime"))
        ignition = from_str(obj.get("@Ignition"))
        latent = from_str(obj.get("@Latent"))
        time_zone_offset = int(from_str(obj.get("@TimeZoneOffset")))
        heading = from_str(obj.get("@Heading"))
        speed = int(from_str(obj.get("@Speed")))
        address = from_str(obj.get("@Address"))
        message_code = int(from_str(obj.get("@MessageCode")))
        display_on_map = from_str(obj.get("@DisplayOnMap"))
        return VehicleLocation(
            name,
            latitude,
            longitude,
            log_time,
            ignition,
            latent,
            time_zone_offset,
            heading,
            speed,
            address,
            message_code,
            display_on_map,
        )

    def to_dict(self) -> dict:
        result: dict = {}
        result["@Name"] = from_str(self.name)
        result["@Latitude"] = from_str(self.latitude)
        result["@Longitude"] = from_str(self.longitude)
        result["@LogTime"] = from_str(self.log_time)
        result["@Ignition"] = from_str(self.ignition)
        result["@Latent"] = from_str(self.latent)
        result["@TimeZoneOffset"] = from_str(str(self.time_zone_offset))
        result["@Heading"] = from_str(self.heading)
        result["@Speed"] = from_str(str(self.speed))
        result["@Address"] = from_str(self.address)
        result["@MessageCode"] = from_str(str(self.message_code))
        result["@DisplayOnMap"] = from_str(self.display_on_map)
        return result


class GetStudentStops:
    vehicle_location: VehicleLocation
    student_stops: StudentStops

    def __init__(
        self, vehicle_location: VehicleLocation, student_stops: StudentStops
    ) -> None:
        self.vehicle_location = vehicle_location
        self.student_stops = student_stops

    @staticmethod
    def from_dict(obj: Any) -> "GetStudentStops":
        assert isinstance(obj, dict)
        vehicle_location = VehicleLocation.from_dict(obj.get("VehicleLocation"))
        student_stops = StudentStops.from_dict(obj.get("StudentStops"))
        return GetStudentStops(vehicle_location, student_stops)

    def to_dict(self) -> dict:
        result: dict = {}
        result["VehicleLocation"] = to_class(VehicleLocation, self.vehicle_location)
        result["StudentStops"] = to_class(StudentStops, self.student_stops)
        return result


class GetStudentStopsAndScans:
    get_student_stops: GetStudentStops

    def __init__(self, get_student_stops: GetStudentStops) -> None:
        self.get_student_stops = get_student_stops

    @staticmethod
    def from_dict(obj: Any) -> "GetStudentStopsAndScans":
        assert isinstance(obj, dict)
        get_student_stops = GetStudentStops.from_dict(obj.get("GetStudentStops"))
        return GetStudentStopsAndScans(get_student_stops)

    def to_dict(self) -> dict:
        result: dict = {}
        result["GetStudentStops"] = to_class(GetStudentStops, self.get_student_stops)
        return result


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

    @staticmethod
    def from_dict(obj: Any) -> "Status":
        assert isinstance(obj, dict)
        code = int(from_str(obj.get("@Code")))
        message = from_str(obj.get("@Message"))
        next_id = int(from_str(obj.get("@NextID")))
        next_call_time = from_str(obj.get("@NextCallTime"))
        return Status(code, message, next_id, next_call_time)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@Code"] = from_str(str(self.code))
        result["@Message"] = from_str(self.message)
        result["@NextID"] = from_str(str(self.next_id))
        result["@NextCallTime"] = from_str(self.next_call_time)
        return result


class SynoviaAPI:
    xsi_schema_location: str
    version: str
    xmlns: str
    xmlns_xsi: str
    status: Status
    get_student_stops_and_scans: GetStudentStopsAndScans

    def __init__(
        self,
        xsi_schema_location: str,
        version: str,
        xmlns: str,
        xmlns_xsi: str,
        status: Status,
        get_student_stops_and_scans: GetStudentStopsAndScans,
    ) -> None:
        self.xsi_schema_location = xsi_schema_location
        self.version = version
        self.xmlns = xmlns
        self.xmlns_xsi = xmlns_xsi
        self.status = status
        self.get_student_stops_and_scans = get_student_stops_and_scans

    @staticmethod
    def from_dict(obj: Any) -> "SynoviaAPI":
        assert isinstance(obj, dict)
        xsi_schema_location = from_str(obj.get("@xsi:schemaLocation"))
        version = from_str(obj.get("@Version"))
        xmlns = from_str(obj.get("@xmlns"))
        xmlns_xsi = from_str(obj.get("@xmlns:xsi"))
        status = Status.from_dict(obj.get("Status"))
        get_student_stops_and_scans = GetStudentStopsAndScans.from_dict(
            obj.get("GetStudentStopsAndScans")
        )
        return SynoviaAPI(
            xsi_schema_location,
            version,
            xmlns,
            xmlns_xsi,
            status,
            get_student_stops_and_scans,
        )

    def to_dict(self) -> dict:
        result: dict = {}
        result["@xsi:schemaLocation"] = from_str(self.xsi_schema_location)
        result["@Version"] = from_str(self.version)
        result["@xmlns"] = from_str(self.xmlns)
        result["@xmlns:xsi"] = from_str(self.xmlns_xsi)
        result["Status"] = to_class(Status, self.status)
        result["GetStudentStopsAndScans"] = to_class(
            GetStudentStopsAndScans, self.get_student_stops_and_scans
        )
        return result


class S1158Result:
    synovia_api: SynoviaAPI

    def __init__(self, synovia_api: SynoviaAPI) -> None:
        self.synovia_api = synovia_api

    @staticmethod
    def from_dict(obj: Any) -> "S1158Result":
        assert isinstance(obj, dict)
        synovia_api = SynoviaAPI.from_dict(obj.get("SynoviaApi"))
        return S1158Result(synovia_api)

    def to_dict(self) -> dict:
        result: dict = {}
        result["SynoviaApi"] = to_class(SynoviaAPI, self.synovia_api)
        return result


class S1158Response:
    xmlns: str
    s1158_result: S1158Result

    def __init__(self, xmlns: str, s1158_result: S1158Result) -> None:
        self.xmlns = xmlns
        self.s1158_result = s1158_result

    @staticmethod
    def from_dict(obj: Any) -> "S1158Response":
        assert isinstance(obj, dict)
        xmlns = from_str(obj.get("@xmlns"))
        s1158_result = S1158Result.from_dict(obj.get("s1158Result"))
        return S1158Response(xmlns, s1158_result)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@xmlns"] = from_str(self.xmlns)
        result["s1158Result"] = to_class(S1158Result, self.s1158_result)
        return result


class SBody:
    s1158_response: S1158Response

    def __init__(self, s1158_response: S1158Response) -> None:
        self.s1158_response = s1158_response

    @staticmethod
    def from_dict(obj: Any) -> "SBody":
        assert isinstance(obj, dict)
        s1158_response = S1158Response.from_dict(obj.get("s1158Response"))
        return SBody(s1158_response)

    def to_dict(self) -> dict:
        result: dict = {}
        result["s1158Response"] = to_class(S1158Response, self.s1158_response)
        return result


class SEnvelope:
    xmlns_s: str
    s_body: SBody

    def __init__(self, xmlns_s: str, s_body: SBody) -> None:
        self.xmlns_s = xmlns_s
        self.s_body = s_body

    @staticmethod
    def from_dict(obj: Any) -> "SEnvelope":
        assert isinstance(obj, dict)
        xmlns_s = from_str(obj.get("@xmlns:s"))
        s_body = SBody.from_dict(obj.get("s:Body"))
        return SEnvelope(xmlns_s, s_body)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@xmlns:s"] = from_str(self.xmlns_s)
        result["s:Body"] = to_class(SBody, self.s_body)
        return result


class S1158:
    s_envelope: SEnvelope

    def __init__(self, s_envelope: SEnvelope) -> None:
        self.s_envelope = s_envelope

    @staticmethod
    def from_dict(obj: Any) -> "S1158":
        assert isinstance(obj, dict)
        s_envelope = SEnvelope.from_dict(obj.get("s:Envelope"))
        return S1158(s_envelope)

    def to_dict(self) -> dict:
        result: dict = {}
        result["s:Envelope"] = to_class(SEnvelope, self.s_envelope)
        return result


def S1158_from_dict(s: Any) -> S1158:
    return S1158.from_dict(s)


def S1158_to_dict(x: S1158) -> Any:
    return to_class(S1158, x)
