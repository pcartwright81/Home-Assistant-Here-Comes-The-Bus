from typing import Any, List, TypeVar, Callable, Type, cast
from datetime import datetime
import dateutil.parser


T = TypeVar("T")


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


def from_datetime(x: Any) -> datetime:
    return dateutil.parser.parse(x)


class Account:
    id: str
    contact_email: str
    carrier: int
    carrier_name: str
    contact_mobile_phone: str
    first_name: str
    last_name: str
    initial_map_lat_lon: str
    notification_language: str
    hctb_minimum_radius: int
    hctb_maximum_radius: int
    hctb_app_timeout: int
    hctb_time_limit_after_gps_activity: int
    hctb_hide_bus_on_indicator: int
    hctb_trim_leading_zeroes_in_the_app: str
    hctb_display_boarding_card_number_below_barcode: str

    def __init__(self, id: str, contact_email: str, carrier: int, carrier_name: str, contact_mobile_phone: str, first_name: str, last_name: str, initial_map_lat_lon: str, notification_language: str, hctb_minimum_radius: int, hctb_maximum_radius: int, hctb_app_timeout: int, hctb_time_limit_after_gps_activity: int, hctb_hide_bus_on_indicator: int, hctb_trim_leading_zeroes_in_the_app: str, hctb_display_boarding_card_number_below_barcode: str) -> None:
        self.id = id
        self.contact_email = contact_email
        self.carrier = carrier
        self.carrier_name = carrier_name
        self.contact_mobile_phone = contact_mobile_phone
        self.first_name = first_name
        self.last_name = last_name
        self.initial_map_lat_lon = initial_map_lat_lon
        self.notification_language = notification_language
        self.hctb_minimum_radius = hctb_minimum_radius
        self.hctb_maximum_radius = hctb_maximum_radius
        self.hctb_app_timeout = hctb_app_timeout
        self.hctb_time_limit_after_gps_activity = hctb_time_limit_after_gps_activity
        self.hctb_hide_bus_on_indicator = hctb_hide_bus_on_indicator
        self.hctb_trim_leading_zeroes_in_the_app = hctb_trim_leading_zeroes_in_the_app
        self.hctb_display_boarding_card_number_below_barcode = hctb_display_boarding_card_number_below_barcode

    @staticmethod
    def from_dict(obj: Any) -> 'Account':
        assert isinstance(obj, dict)
        id = from_str(obj.get("@ID"))
        contact_email = from_str(obj.get("@ContactEmail"))
        carrier = int(from_str(obj.get("@Carrier")))
        carrier_name = from_str(obj.get("@CarrierName"))
        contact_mobile_phone = from_str(obj.get("@ContactMobilePhone"))
        first_name = from_str(obj.get("@FirstName"))
        last_name = from_str(obj.get("@LastName"))
        initial_map_lat_lon = from_str(obj.get("@InitialMapLatLon"))
        notification_language = from_str(obj.get("@NotificationLanguage"))
        hctb_minimum_radius = int(from_str(obj.get("@HctbMinimumRadius")))
        hctb_maximum_radius = int(from_str(obj.get("@HctbMaximumRadius")))
        hctb_app_timeout = int(from_str(obj.get("@HctbAppTimeout")))
        hctb_time_limit_after_gps_activity = int(from_str(obj.get("@HctbTimeLimitAfterGpsActivity")))
        hctb_hide_bus_on_indicator = int(from_str(obj.get("@HctbHideBusOnIndicator")))
        hctb_trim_leading_zeroes_in_the_app = from_str(obj.get("@HctbTrimLeadingZeroesInTheApp"))
        hctb_display_boarding_card_number_below_barcode = from_str(obj.get("@HctbDisplayBoardingCardNumberBelowBarcode"))
        return Account(id, contact_email, carrier, carrier_name, contact_mobile_phone, first_name, last_name, initial_map_lat_lon, notification_language, hctb_minimum_radius, hctb_maximum_radius, hctb_app_timeout, hctb_time_limit_after_gps_activity, hctb_hide_bus_on_indicator, hctb_trim_leading_zeroes_in_the_app, hctb_display_boarding_card_number_below_barcode)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@ID"] = from_str(self.id)
        result["@ContactEmail"] = from_str(self.contact_email)
        result["@Carrier"] = from_str(str(self.carrier))
        result["@CarrierName"] = from_str(self.carrier_name)
        result["@ContactMobilePhone"] = from_str(self.contact_mobile_phone)
        result["@FirstName"] = from_str(self.first_name)
        result["@LastName"] = from_str(self.last_name)
        result["@InitialMapLatLon"] = from_str(self.initial_map_lat_lon)
        result["@NotificationLanguage"] = from_str(self.notification_language)
        result["@HctbMinimumRadius"] = from_str(str(self.hctb_minimum_radius))
        result["@HctbMaximumRadius"] = from_str(str(self.hctb_maximum_radius))
        result["@HctbAppTimeout"] = from_str(str(self.hctb_app_timeout))
        result["@HctbTimeLimitAfterGpsActivity"] = from_str(str(self.hctb_time_limit_after_gps_activity))
        result["@HctbHideBusOnIndicator"] = from_str(str(self.hctb_hide_bus_on_indicator))
        result["@HctbTrimLeadingZeroesInTheApp"] = from_str(self.hctb_trim_leading_zeroes_in_the_app)
        result["@HctbDisplayBoardingCardNumberBelowBarcode"] = from_str(self.hctb_display_boarding_card_number_below_barcode)
        return result


class Carrier:
    id: int
    name: str

    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name

    @staticmethod
    def from_dict(obj: Any) -> 'Carrier':
        assert isinstance(obj, dict)
        id = int(from_str(obj.get("@ID")))
        name = from_str(obj.get("@Name"))
        return Carrier(id, name)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@ID"] = from_str(str(self.id))
        result["@Name"] = from_str(self.name)
        return result


class CarrierList:
    carrier: List[Carrier]

    def __init__(self, carrier: List[Carrier]) -> None:
        self.carrier = carrier

    @staticmethod
    def from_dict(obj: Any) -> 'CarrierList':
        assert isinstance(obj, dict)
        carrier = from_list(Carrier.from_dict, obj.get("Carrier"))
        return CarrierList(carrier)

    def to_dict(self) -> dict:
        result: dict = {}
        result["Carrier"] = from_list(lambda x: to_class(Carrier, x), self.carrier)
        return result


class Contact:
    contact_id: int
    name: str
    contact_address: str
    contact_type: str
    is_active: str

    def __init__(self, contact_id: int, name: str, contact_address: str, contact_type: str, is_active: str) -> None:
        self.contact_id = contact_id
        self.name = name
        self.contact_address = contact_address
        self.contact_type = contact_type
        self.is_active = is_active

    @staticmethod
    def from_dict(obj: Any) -> 'Contact':
        assert isinstance(obj, dict)
        contact_id = int(from_str(obj.get("@ContactId")))
        name = from_str(obj.get("@Name"))
        contact_address = from_str(obj.get("@ContactAddress"))
        contact_type = from_str(obj.get("@ContactType"))
        is_active = from_str(obj.get("@IsActive"))
        return Contact(contact_id, name, contact_address, contact_type, is_active)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@ContactId"] = from_str(str(self.contact_id))
        result["@Name"] = from_str(self.name)
        result["@ContactAddress"] = from_str(self.contact_address)
        result["@ContactType"] = from_str(self.contact_type)
        result["@IsActive"] = from_str(self.is_active)
        return result


class ContactList:
    contact: List[Contact]

    def __init__(self, contact: List[Contact]) -> None:
        self.contact = contact

    @staticmethod
    def from_dict(obj: Any) -> 'ContactList':
        assert isinstance(obj, dict)
        contact = from_list(Contact.from_dict, obj.get("Contact"))
        return ContactList(contact)

    def to_dict(self) -> dict:
        result: dict = {}
        result["Contact"] = from_list(lambda x: to_class(Contact, x), self.contact)
        return result


class ContactType:
    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    @staticmethod
    def from_dict(obj: Any) -> 'ContactType':
        assert isinstance(obj, dict)
        name = from_str(obj.get("@Name"))
        return ContactType(name)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@Name"] = from_str(self.name)
        return result


class ContactTypeList:
    contact_type: List[ContactType]

    def __init__(self, contact_type: List[ContactType]) -> None:
        self.contact_type = contact_type

    @staticmethod
    def from_dict(obj: Any) -> 'ContactTypeList':
        assert isinstance(obj, dict)
        contact_type = from_list(ContactType.from_dict, obj.get("ContactType"))
        return ContactTypeList(contact_type)

    def to_dict(self) -> dict:
        result: dict = {}
        result["ContactType"] = from_list(lambda x: to_class(ContactType, x), self.contact_type)
        return result


class LicenseList:
    license: List[ContactType]

    def __init__(self, license: List[ContactType]) -> None:
        self.license = license

    @staticmethod
    def from_dict(obj: Any) -> 'LicenseList':
        assert isinstance(obj, dict)
        license = from_list(ContactType.from_dict, obj.get("License"))
        return LicenseList(license)

    def to_dict(self) -> dict:
        result: dict = {}
        result["License"] = from_list(lambda x: to_class(ContactType, x), self.license)
        return result


class Feature:
    name: str
    cost: str

    def __init__(self, name: str, cost: str) -> None:
        self.name = name
        self.cost = cost

    @staticmethod
    def from_dict(obj: Any) -> 'Feature':
        assert isinstance(obj, dict)
        name = from_str(obj.get("Name"))
        cost = from_str(obj.get("Cost"))
        return Feature(name, cost)

    def to_dict(self) -> dict:
        result: dict = {}
        result["Name"] = from_str(self.name)
        result["Cost"] = from_str(self.cost)
        return result


class Features:
    feature: List[Feature]

    def __init__(self, feature: List[Feature]) -> None:
        self.feature = feature

    @staticmethod
    def from_dict(obj: Any) -> 'Features':
        assert isinstance(obj, dict)
        feature = from_list(Feature.from_dict, obj.get("Feature"))
        return Features(feature)

    def to_dict(self) -> dict:
        result: dict = {}
        result["Feature"] = from_list(lambda x: to_class(Feature, x), self.feature)
        return result


class License:
    license_id: int
    parent_license_id: int
    name: str
    cost: str
    start_date: datetime
    end_date: datetime
    next_bill_date: datetime
    free_trial: str
    status: str
    billing_freq_months: int
    commitment_months: int
    auto_renew: str
    features: Features

    def __init__(self, license_id: int, parent_license_id: int, name: str, cost: str, start_date: datetime, end_date: datetime, next_bill_date: datetime, free_trial: str, status: str, billing_freq_months: int, commitment_months: int, auto_renew: str, features: Features) -> None:
        self.license_id = license_id
        self.parent_license_id = parent_license_id
        self.name = name
        self.cost = cost
        self.start_date = start_date
        self.end_date = end_date
        self.next_bill_date = next_bill_date
        self.free_trial = free_trial
        self.status = status
        self.billing_freq_months = billing_freq_months
        self.commitment_months = commitment_months
        self.auto_renew = auto_renew
        self.features = features

    @staticmethod
    def from_dict(obj: Any) -> 'License':
        assert isinstance(obj, dict)
        license_id = int(from_str(obj.get("@LicenseId")))
        parent_license_id = int(from_str(obj.get("@ParentLicenseId")))
        name = from_str(obj.get("@Name"))
        cost = from_str(obj.get("@Cost"))
        start_date = from_datetime(obj.get("@StartDate"))
        end_date = from_datetime(obj.get("@EndDate"))
        next_bill_date = from_datetime(obj.get("@NextBillDate"))
        free_trial = from_str(obj.get("@FreeTrial"))
        status = from_str(obj.get("@Status"))
        billing_freq_months = int(from_str(obj.get("@BillingFreqMonths")))
        commitment_months = int(from_str(obj.get("@CommitmentMonths")))
        auto_renew = from_str(obj.get("@AutoRenew"))
        features = Features.from_dict(obj.get("Features"))
        return License(license_id, parent_license_id, name, cost, start_date, end_date, next_bill_date, free_trial, status, billing_freq_months, commitment_months, auto_renew, features)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@LicenseId"] = from_str(str(self.license_id))
        result["@ParentLicenseId"] = from_str(str(self.parent_license_id))
        result["@Name"] = from_str(self.name)
        result["@Cost"] = from_str(self.cost)
        result["@StartDate"] = self.start_date.isoformat()
        result["@EndDate"] = self.end_date.isoformat()
        result["@NextBillDate"] = self.next_bill_date.isoformat()
        result["@FreeTrial"] = from_str(self.free_trial)
        result["@Status"] = from_str(self.status)
        result["@BillingFreqMonths"] = from_str(str(self.billing_freq_months))
        result["@CommitmentMonths"] = from_str(str(self.commitment_months))
        result["@AutoRenew"] = from_str(self.auto_renew)
        result["Features"] = to_class(Features, self.features)
        return result


class Licenses:
    license: License

    def __init__(self, license: License) -> None:
        self.license = license

    @staticmethod
    def from_dict(obj: Any) -> 'Licenses':
        assert isinstance(obj, dict)
        license = License.from_dict(obj.get("License"))
        return Licenses(license)

    def to_dict(self) -> dict:
        result: dict = {}
        result["License"] = to_class(License, self.license)
        return result


class Student:
    entity_id: str
    first_name: str
    last_name: str
    school_id: int
    parent_student_id: str

    def __init__(self, entity_id: str, first_name: str, last_name: str, school_id: int, parent_student_id: str) -> None:
        self.entity_id = entity_id
        self.first_name = first_name
        self.last_name = last_name
        self.school_id = school_id
        self.parent_student_id = parent_student_id

    @staticmethod
    def from_dict(obj: Any) -> 'Student':
        assert isinstance(obj, dict)
        entity_id = from_str(obj.get("@EntityID"))
        first_name = from_str(obj.get("@FirstName"))
        last_name = from_str(obj.get("@LastName"))
        school_id = int(from_str(obj.get("@SchoolId")))
        parent_student_id = from_str(obj.get("@ParentStudentId"))
        return Student(entity_id, first_name, last_name, school_id, parent_student_id)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@EntityID"] = from_str(self.entity_id)
        result["@FirstName"] = from_str(self.first_name)
        result["@LastName"] = from_str(self.last_name)
        result["@SchoolId"] = from_str(str(self.school_id))
        result["@ParentStudentId"] = from_str(self.parent_student_id)
        return result


class LinkedStudents:
    student: List[Student]

    def __init__(self, student: List[Student]) -> None:
        self.student = student

    @staticmethod
    def from_dict(obj: Any) -> 'LinkedStudents':
        assert isinstance(obj, dict)
        student = from_list(Student.from_dict, obj.get("Student"))
        return LinkedStudents(student)

    def to_dict(self) -> dict:
        result: dict = {}
        result["Student"] = from_list(lambda x: to_class(Student, x), self.student)
        return result


class NotificationTypeList:
    notification_type: List[ContactType]

    def __init__(self, notification_type: List[ContactType]) -> None:
        self.notification_type = notification_type

    @staticmethod
    def from_dict(obj: Any) -> 'NotificationTypeList':
        assert isinstance(obj, dict)
        notification_type = from_list(ContactType.from_dict, obj.get("NotificationType"))
        return NotificationTypeList(notification_type)

    def to_dict(self) -> dict:
        result: dict = {}
        result["NotificationType"] = from_list(lambda x: to_class(ContactType, x), self.notification_type)
        return result


class Row:
    image_url: str
    redirect_url: str

    def __init__(self, image_url: str, redirect_url: str) -> None:
        self.image_url = image_url
        self.redirect_url = redirect_url

    @staticmethod
    def from_dict(obj: Any) -> 'Row':
        assert isinstance(obj, dict)
        image_url = from_str(obj.get("@ImageUrl"))
        redirect_url = from_str(obj.get("@RedirectUrl"))
        return Row(image_url, redirect_url)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@ImageUrl"] = from_str(self.image_url)
        result["@RedirectUrl"] = from_str(self.redirect_url)
        return result


class Setting:
    name: str
    row: Row

    def __init__(self, name: str, row: Row) -> None:
        self.name = name
        self.row = row

    @staticmethod
    def from_dict(obj: Any) -> 'Setting':
        assert isinstance(obj, dict)
        name = from_str(obj.get("@Name"))
        row = Row.from_dict(obj.get("row"))
        return Setting(name, row)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@Name"] = from_str(self.name)
        result["row"] = to_class(Row, self.row)
        return result


class Settings:
    setting: List[Setting]

    def __init__(self, setting: List[Setting]) -> None:
        self.setting = setting

    @staticmethod
    def from_dict(obj: Any) -> 'Settings':
        assert isinstance(obj, dict)
        setting = from_list(Setting.from_dict, obj.get("Setting"))
        return Settings(setting)

    def to_dict(self) -> dict:
        result: dict = {}
        result["Setting"] = from_list(lambda x: to_class(Setting, x), self.setting)
        return result


class TimeOfDay:
    id: str
    name: str
    begin_time: datetime
    end_time: datetime

    def __init__(self, id: str, name: str, begin_time: datetime, end_time: datetime) -> None:
        self.id = id
        self.name = name
        self.begin_time = begin_time
        self.end_time = end_time

    @staticmethod
    def from_dict(obj: Any) -> 'TimeOfDay':
        assert isinstance(obj, dict)
        id = from_str(obj.get("@ID"))
        name = from_str(obj.get("@Name"))
        begin_time = from_datetime(obj.get("@BeginTime"))
        end_time = from_datetime(obj.get("@EndTime"))
        return TimeOfDay(id, name, begin_time, end_time)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@ID"] = from_str(self.id)
        result["@Name"] = from_str(self.name)
        result["@BeginTime"] = self.begin_time.isoformat()
        result["@EndTime"] = self.end_time.isoformat()
        return result


class TimeOfDays:
    time_of_day: List[TimeOfDay]

    def __init__(self, time_of_day: List[TimeOfDay]) -> None:
        self.time_of_day = time_of_day

    @staticmethod
    def from_dict(obj: Any) -> 'TimeOfDays':
        assert isinstance(obj, dict)
        time_of_day = from_list(TimeOfDay.from_dict, obj.get("TimeOfDay"))
        return TimeOfDays(time_of_day)

    def to_dict(self) -> dict:
        result: dict = {}
        result["TimeOfDay"] = from_list(lambda x: to_class(TimeOfDay, x), self.time_of_day)
        return result


class ParentLogin:
    account: Account
    licenses: Licenses
    carrier_list: CarrierList
    time_of_days: TimeOfDays
    linked_students: LinkedStudents
    contact_list: ContactList
    contact_type_list: ContactTypeList
    license_list: LicenseList
    notification_type_list: NotificationTypeList
    settings: Settings

    def __init__(self, account: Account, licenses: Licenses, carrier_list: CarrierList, time_of_days: TimeOfDays, linked_students: LinkedStudents, contact_list: ContactList, contact_type_list: ContactTypeList, license_list: LicenseList, notification_type_list: NotificationTypeList, settings: Settings) -> None:
        self.account = account
        self.licenses = licenses
        self.carrier_list = carrier_list
        self.time_of_days = time_of_days
        self.linked_students = linked_students
        self.contact_list = contact_list
        self.contact_type_list = contact_type_list
        self.license_list = license_list
        self.notification_type_list = notification_type_list
        self.settings = settings

    @staticmethod
    def from_dict(obj: Any) -> 'ParentLogin':
        assert isinstance(obj, dict)
        account = Account.from_dict(obj.get("Account"))
        licenses = Licenses.from_dict(obj.get("Licenses"))
        carrier_list = CarrierList.from_dict(obj.get("CarrierList"))
        time_of_days = TimeOfDays.from_dict(obj.get("TimeOfDays"))
        linked_students = LinkedStudents.from_dict(obj.get("LinkedStudents"))
        contact_list = ContactList.from_dict(obj.get("ContactList"))
        contact_type_list = ContactTypeList.from_dict(obj.get("ContactTypeList"))
        license_list = LicenseList.from_dict(obj.get("LicenseList"))
        notification_type_list = NotificationTypeList.from_dict(obj.get("NotificationTypeList"))
        settings = Settings.from_dict(obj.get("Settings"))
        return ParentLogin(account, licenses, carrier_list, time_of_days, linked_students, contact_list, contact_type_list, license_list, notification_type_list, settings)

    def to_dict(self) -> dict:
        result: dict = {}
        result["Account"] = to_class(Account, self.account)
        result["Licenses"] = to_class(Licenses, self.licenses)
        result["CarrierList"] = to_class(CarrierList, self.carrier_list)
        result["TimeOfDays"] = to_class(TimeOfDays, self.time_of_days)
        result["LinkedStudents"] = to_class(LinkedStudents, self.linked_students)
        result["ContactList"] = to_class(ContactList, self.contact_list)
        result["ContactTypeList"] = to_class(ContactTypeList, self.contact_type_list)
        result["LicenseList"] = to_class(LicenseList, self.license_list)
        result["NotificationTypeList"] = to_class(NotificationTypeList, self.notification_type_list)
        result["Settings"] = to_class(Settings, self.settings)
        return result


class Status:
    code: int
    message: str
    next_id: int
    next_call_time: str

    def __init__(self, code: int, message: str, next_id: int, next_call_time: str) -> None:
        self.code = code
        self.message = message
        self.next_id = next_id
        self.next_call_time = next_call_time

    @staticmethod
    def from_dict(obj: Any) -> 'Status':
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
    parent_login: ParentLogin

    def __init__(self, xsi_schema_location: str, version: str, xmlns: str, xmlns_xsi: str, status: Status, parent_login: ParentLogin) -> None:
        self.xsi_schema_location = xsi_schema_location
        self.version = version
        self.xmlns = xmlns
        self.xmlns_xsi = xmlns_xsi
        self.status = status
        self.parent_login = parent_login

    @staticmethod
    def from_dict(obj: Any) -> 'SynoviaAPI':
        assert isinstance(obj, dict)
        xsi_schema_location = from_str(obj.get("@xsi:schemaLocation"))
        version = from_str(obj.get("@Version"))
        xmlns = from_str(obj.get("@xmlns"))
        xmlns_xsi = from_str(obj.get("@xmlns:xsi"))
        status = Status.from_dict(obj.get("Status"))
        parent_login = ParentLogin.from_dict(obj.get("ParentLogin"))
        return SynoviaAPI(xsi_schema_location, version, xmlns, xmlns_xsi, status, parent_login)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@xsi:schemaLocation"] = from_str(self.xsi_schema_location)
        result["@Version"] = from_str(self.version)
        result["@xmlns"] = from_str(self.xmlns)
        result["@xmlns:xsi"] = from_str(self.xmlns_xsi)
        result["Status"] = to_class(Status, self.status)
        result["ParentLogin"] = to_class(ParentLogin, self.parent_login)
        return result


class S1157Result:
    synovia_api: SynoviaAPI

    def __init__(self, synovia_api: SynoviaAPI) -> None:
        self.synovia_api = synovia_api

    @staticmethod
    def from_dict(obj: Any) -> 'S1157Result':
        assert isinstance(obj, dict)
        synovia_api = SynoviaAPI.from_dict(obj.get("SynoviaApi"))
        return S1157Result(synovia_api)

    def to_dict(self) -> dict:
        result: dict = {}
        result["SynoviaApi"] = to_class(SynoviaAPI, self.synovia_api)
        return result


class S1157Response:
    xmlns: str
    s1157_result: S1157Result

    def __init__(self, xmlns: str, s1157_result: S1157Result) -> None:
        self.xmlns = xmlns
        self.s1157_result = s1157_result

    @staticmethod
    def from_dict(obj: Any) -> 'S1157Response':
        assert isinstance(obj, dict)
        xmlns = from_str(obj.get("@xmlns"))
        s1157_result = S1157Result.from_dict(obj.get("s1157Result"))
        return S1157Response(xmlns, s1157_result)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@xmlns"] = from_str(self.xmlns)
        result["s1157Result"] = to_class(S1157Result, self.s1157_result)
        return result


class SBody:
    s1157_response: S1157Response

    def __init__(self, s1157_response: S1157Response) -> None:
        self.s1157_response = s1157_response

    @staticmethod
    def from_dict(obj: Any) -> 'SBody':
        assert isinstance(obj, dict)
        s1157_response = S1157Response.from_dict(obj.get("s1157Response"))
        return SBody(s1157_response)

    def to_dict(self) -> dict:
        result: dict = {}
        result["s1157Response"] = to_class(S1157Response, self.s1157_response)
        return result


class SEnvelope:
    xmlns_s: str
    s_body: SBody

    def __init__(self, xmlns_s: str, s_body: SBody) -> None:
        self.xmlns_s = xmlns_s
        self.s_body = s_body

    @staticmethod
    def from_dict(obj: Any) -> 'SEnvelope':
        assert isinstance(obj, dict)
        xmlns_s = from_str(obj.get("@xmlns:s"))
        s_body = SBody.from_dict(obj.get("s:Body"))
        return SEnvelope(xmlns_s, s_body)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@xmlns:s"] = from_str(self.xmlns_s)
        result["s:Body"] = to_class(SBody, self.s_body)
        return result


class S1157:
    s_envelope: SEnvelope

    def __init__(self, s_envelope: SEnvelope) -> None:
        self.s_envelope = s_envelope

    @staticmethod
    def from_dict(obj: Any) -> 'S1157':
        assert isinstance(obj, dict)
        s_envelope = SEnvelope.from_dict(obj.get("s:Envelope"))
        return S1157(s_envelope)

    def to_dict(self) -> dict:
        result: dict = {}
        result["s:Envelope"] = to_class(SEnvelope, self.s_envelope)
        return result


def S1157_from_dict(s: Any) -> S1157:
    return S1157.from_dict(s)


def S1157_to_dict(x: S1157) -> Any:
    return to_class(S1157, x)
