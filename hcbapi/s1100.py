from typing import Any, List, TypeVar, Callable, Type, cast


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


class Customer:
    name: str
    id: str
    planned_routing_system: str
    snapshot_start_date: str
    snapshot_id: int
    last_import_run_date: str
    last_import_status: str
    hctb_minimum_radius: int
    hctb_maximum_radius: int
    hctb_sso_type: str
    hctb_setting_registration_enabled: str
    hctb_setting_password_reset_enabled: str
    hctb_trim_leading_zeroes_in_the_app: str
    hctb_display_boarding_card_number_below_barcode: str
    local_id: int
    host: str
    ecommerce_url: str
    store_id: str
    api_token: str
    profile_id: str
    admin_email: str
    customer_email: str

    def __init__(self, name: str, id: str, planned_routing_system: str, snapshot_start_date: str, snapshot_id: int, last_import_run_date: str, last_import_status: str, hctb_minimum_radius: int, hctb_maximum_radius: int, hctb_sso_type: str, hctb_setting_registration_enabled: str, hctb_setting_password_reset_enabled: str, hctb_trim_leading_zeroes_in_the_app: str, hctb_display_boarding_card_number_below_barcode: str, local_id: int, host: str, ecommerce_url: str, store_id: str, api_token: str, profile_id: str, admin_email: str, customer_email: str) -> None:
        self.name = name
        self.id = id
        self.planned_routing_system = planned_routing_system
        self.snapshot_start_date = snapshot_start_date
        self.snapshot_id = snapshot_id
        self.last_import_run_date = last_import_run_date
        self.last_import_status = last_import_status
        self.hctb_minimum_radius = hctb_minimum_radius
        self.hctb_maximum_radius = hctb_maximum_radius
        self.hctb_sso_type = hctb_sso_type
        self.hctb_setting_registration_enabled = hctb_setting_registration_enabled
        self.hctb_setting_password_reset_enabled = hctb_setting_password_reset_enabled
        self.hctb_trim_leading_zeroes_in_the_app = hctb_trim_leading_zeroes_in_the_app
        self.hctb_display_boarding_card_number_below_barcode = hctb_display_boarding_card_number_below_barcode
        self.local_id = local_id
        self.host = host
        self.ecommerce_url = ecommerce_url
        self.store_id = store_id
        self.api_token = api_token
        self.profile_id = profile_id
        self.admin_email = admin_email
        self.customer_email = customer_email

    @staticmethod
    def from_dict(obj: Any) -> 'Customer':
        assert isinstance(obj, dict)
        name = from_str(obj.get("@Name"))
        id = from_str(obj.get("@ID"))
        planned_routing_system = from_str(obj.get("@PlannedRoutingSystem"))
        snapshot_start_date = from_str(obj.get("@SnapshotStartDate"))
        snapshot_id = int(from_str(obj.get("@SnapshotId")))
        last_import_run_date = from_str(obj.get("@LastImportRunDate"))
        last_import_status = from_str(obj.get("@LastImportStatus"))
        hctb_minimum_radius = int(from_str(obj.get("@HctbMinimumRadius")))
        hctb_maximum_radius = int(from_str(obj.get("@HctbMaximumRadius")))
        hctb_sso_type = from_str(obj.get("@HctbSsoType"))
        hctb_setting_registration_enabled = from_str(obj.get("@HctbSettingRegistrationEnabled"))
        hctb_setting_password_reset_enabled = from_str(obj.get("@HctbSettingPasswordResetEnabled"))
        hctb_trim_leading_zeroes_in_the_app = from_str(obj.get("@HctbTrimLeadingZeroesInTheApp"))
        hctb_display_boarding_card_number_below_barcode = from_str(obj.get("@HctbDisplayBoardingCardNumberBelowBarcode"))
        local_id = int(from_str(obj.get("@LocalId")))
        host = from_str(obj.get("@Host"))
        ecommerce_url = from_str(obj.get("@EcommerceUrl"))
        store_id = from_str(obj.get("@StoreId"))
        api_token = from_str(obj.get("@ApiToken"))
        profile_id = from_str(obj.get("@ProfileId"))
        admin_email = from_str(obj.get("@AdminEmail"))
        customer_email = from_str(obj.get("@CustomerEmail"))
        return Customer(name, id, planned_routing_system, snapshot_start_date, snapshot_id, last_import_run_date, last_import_status, hctb_minimum_radius, hctb_maximum_radius, hctb_sso_type, hctb_setting_registration_enabled, hctb_setting_password_reset_enabled, hctb_trim_leading_zeroes_in_the_app, hctb_display_boarding_card_number_below_barcode, local_id, host, ecommerce_url, store_id, api_token, profile_id, admin_email, customer_email)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@Name"] = from_str(self.name)
        result["@ID"] = from_str(self.id)
        result["@PlannedRoutingSystem"] = from_str(self.planned_routing_system)
        result["@SnapshotStartDate"] = from_str(self.snapshot_start_date)
        result["@SnapshotId"] = from_str(str(self.snapshot_id))
        result["@LastImportRunDate"] = from_str(self.last_import_run_date)
        result["@LastImportStatus"] = from_str(self.last_import_status)
        result["@HctbMinimumRadius"] = from_str(str(self.hctb_minimum_radius))
        result["@HctbMaximumRadius"] = from_str(str(self.hctb_maximum_radius))
        result["@HctbSsoType"] = from_str(self.hctb_sso_type)
        result["@HctbSettingRegistrationEnabled"] = from_str(self.hctb_setting_registration_enabled)
        result["@HctbSettingPasswordResetEnabled"] = from_str(self.hctb_setting_password_reset_enabled)
        result["@HctbTrimLeadingZeroesInTheApp"] = from_str(self.hctb_trim_leading_zeroes_in_the_app)
        result["@HctbDisplayBoardingCardNumberBelowBarcode"] = from_str(self.hctb_display_boarding_card_number_below_barcode)
        result["@LocalId"] = from_str(str(self.local_id))
        result["@Host"] = from_str(self.host)
        result["@EcommerceUrl"] = from_str(self.ecommerce_url)
        result["@StoreId"] = from_str(self.store_id)
        result["@ApiToken"] = from_str(self.api_token)
        result["@ProfileId"] = from_str(self.profile_id)
        result["@AdminEmail"] = from_str(self.admin_email)
        result["@CustomerEmail"] = from_str(self.customer_email)
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


class NotificationLanguageList:
    notification_language: List[ContactType]

    def __init__(self, notification_language: List[ContactType]) -> None:
        self.notification_language = notification_language

    @staticmethod
    def from_dict(obj: Any) -> 'NotificationLanguageList':
        assert isinstance(obj, dict)
        notification_language = from_list(ContactType.from_dict, obj.get("NotificationLanguage"))
        return NotificationLanguageList(notification_language)

    def to_dict(self) -> dict:
        result: dict = {}
        result["NotificationLanguage"] = from_list(lambda x: to_class(ContactType, x), self.notification_language)
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


class ValidateCustomerAccountNumber:
    customer: Customer
    license_list: LicenseList
    carrier_list: CarrierList
    contact_type_list: ContactTypeList
    notification_language_list: NotificationLanguageList
    notification_type_list: NotificationTypeList

    def __init__(self, customer: Customer, license_list: LicenseList, carrier_list: CarrierList, contact_type_list: ContactTypeList, notification_language_list: NotificationLanguageList, notification_type_list: NotificationTypeList) -> None:
        self.customer = customer
        self.license_list = license_list
        self.carrier_list = carrier_list
        self.contact_type_list = contact_type_list
        self.notification_language_list = notification_language_list
        self.notification_type_list = notification_type_list

    @staticmethod
    def from_dict(obj: Any) -> 'ValidateCustomerAccountNumber':
        assert isinstance(obj, dict)
        customer = Customer.from_dict(obj.get("Customer"))
        license_list = LicenseList.from_dict(obj.get("LicenseList"))
        carrier_list = CarrierList.from_dict(obj.get("CarrierList"))
        contact_type_list = ContactTypeList.from_dict(obj.get("ContactTypeList"))
        notification_language_list = NotificationLanguageList.from_dict(obj.get("NotificationLanguageList"))
        notification_type_list = NotificationTypeList.from_dict(obj.get("NotificationTypeList"))
        return ValidateCustomerAccountNumber(customer, license_list, carrier_list, contact_type_list, notification_language_list, notification_type_list)

    def to_dict(self) -> dict:
        result: dict = {}
        result["Customer"] = to_class(Customer, self.customer)
        result["LicenseList"] = to_class(LicenseList, self.license_list)
        result["CarrierList"] = to_class(CarrierList, self.carrier_list)
        result["ContactTypeList"] = to_class(ContactTypeList, self.contact_type_list)
        result["NotificationLanguageList"] = to_class(NotificationLanguageList, self.notification_language_list)
        result["NotificationTypeList"] = to_class(NotificationTypeList, self.notification_type_list)
        return result


class SynoviaAPI:
    xsi_schema_location: str
    version: str
    xmlns: str
    xmlns_xsi: str
    status: Status
    validate_customer_account_number: ValidateCustomerAccountNumber

    def __init__(self, xsi_schema_location: str, version: str, xmlns: str, xmlns_xsi: str, status: Status, validate_customer_account_number: ValidateCustomerAccountNumber) -> None:
        self.xsi_schema_location = xsi_schema_location
        self.version = version
        self.xmlns = xmlns
        self.xmlns_xsi = xmlns_xsi
        self.status = status
        self.validate_customer_account_number = validate_customer_account_number

    @staticmethod
    def from_dict(obj: Any) -> 'SynoviaAPI':
        assert isinstance(obj, dict)
        xsi_schema_location = from_str(obj.get("@xsi:schemaLocation"))
        version = from_str(obj.get("@Version"))
        xmlns = from_str(obj.get("@xmlns"))
        xmlns_xsi = from_str(obj.get("@xmlns:xsi"))
        status = Status.from_dict(obj.get("Status"))
        validate_customer_account_number = ValidateCustomerAccountNumber.from_dict(obj.get("ValidateCustomerAccountNumber"))
        return SynoviaAPI(xsi_schema_location, version, xmlns, xmlns_xsi, status, validate_customer_account_number)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@xsi:schemaLocation"] = from_str(self.xsi_schema_location)
        result["@Version"] = from_str(self.version)
        result["@xmlns"] = from_str(self.xmlns)
        result["@xmlns:xsi"] = from_str(self.xmlns_xsi)
        result["Status"] = to_class(Status, self.status)
        result["ValidateCustomerAccountNumber"] = to_class(ValidateCustomerAccountNumber, self.validate_customer_account_number)
        return result


class S1100Result:
    synovia_api: SynoviaAPI

    def __init__(self, synovia_api: SynoviaAPI) -> None:
        self.synovia_api = synovia_api

    @staticmethod
    def from_dict(obj: Any) -> 'S1100Result':
        assert isinstance(obj, dict)
        synovia_api = SynoviaAPI.from_dict(obj.get("SynoviaApi"))
        return S1100Result(synovia_api)

    def to_dict(self) -> dict:
        result: dict = {}
        result["SynoviaApi"] = to_class(SynoviaAPI, self.synovia_api)
        return result


class S1100Response:
    xmlns: str
    s1100_result: S1100Result

    def __init__(self, xmlns: str, s1100_result: S1100Result) -> None:
        self.xmlns = xmlns
        self.s1100_result = s1100_result

    @staticmethod
    def from_dict(obj: Any) -> 'S1100Response':
        assert isinstance(obj, dict)
        xmlns = from_str(obj.get("@xmlns"))
        s1100_result = S1100Result.from_dict(obj.get("s1100Result"))
        return S1100Response(xmlns, s1100_result)

    def to_dict(self) -> dict:
        result: dict = {}
        result["@xmlns"] = from_str(self.xmlns)
        result["s1100Result"] = to_class(S1100Result, self.s1100_result)
        return result


class SBody:
    s1100_response: S1100Response

    def __init__(self, s1100_response: S1100Response) -> None:
        self.s1100_response = s1100_response

    @staticmethod
    def from_dict(obj: Any) -> 'SBody':
        assert isinstance(obj, dict)
        s1100_response = S1100Response.from_dict(obj.get("s1100Response"))
        return SBody(s1100_response)

    def to_dict(self) -> dict:
        result: dict = {}
        result["s1100Response"] = to_class(S1100Response, self.s1100_response)
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


class S1100:
    s_envelope: SEnvelope

    def __init__(self, s_envelope: SEnvelope) -> None:
        self.s_envelope = s_envelope

    @staticmethod
    def from_dict(obj: Any) -> 'S1100':
        assert isinstance(obj, dict)
        s_envelope = SEnvelope.from_dict(obj.get("s:Envelope"))
        return S1100(s_envelope)

    def to_dict(self) -> dict:
        result: dict = {}
        result["s:Envelope"] = to_class(SEnvelope, self.s_envelope)
        return result


def s1100_from_dict(s: Any) -> S1100:
    return S1100.from_dict(s)


def s1100_to_dict(x: S1100) -> Any:
    return to_class(S1100, x)
