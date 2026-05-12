from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    CASHIER = "cashier"
    OPERATOR = "operator"
    SUPERVISOR = "supervisor"


class ServiceType(str, Enum):
    WASH = "lavado"
    DETAILING = "detallado"
    POLISHING = "pulido"
    CERAMIC = "ceramico"
    MOBILE = "domicilio"


class AppointmentStatus(str, Enum):
    PENDING = "pendiente"
    CONFIRMED = "confirmado"
    IN_PROGRESS = "en_proceso"
    FINISHED = "terminado"
    CANCELLED = "cancelado"


class AppointmentOrigin(str, Enum):
    MANUAL = "manual"
    WHATSAPP = "whatsapp"
    GOOGLE_CALENDAR = "google_calendar"
    CLICKUP = "clickup"


class JobStatus(str, Enum):
    PENDING = "pendiente"
    STARTED = "en_proceso"
    FINISHED = "terminado"


class PaymentMethod(str, Enum):
    CASH = "efectivo"
    CARD = "tarjeta"
    TRANSFER = "transferencia"
    COURTESY = "cortesia"
    CREDIT = "credito"
    DEPOSIT = "deposito"


class ChargeStatus(str, Enum):
    PENDING = "pendiente"
    PAID = "pagado"


class PaymentItemType(str, Enum):
    SERVICE = "service"
    EXTRA = "extra"


class CashCutStatus(str, Enum):
    OPEN = "abierto"
    CLOSED = "cerrado"


class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class InventoryMovementType(str, Enum):
    PURCHASE = "compra"
    CONSUMPTION = "consumo"
    ADJUSTMENT = "ajuste"


class WhatsAppConversationMode(str, Enum):
    BOT = "bot"
    HUMAN = "humano"


class WhatsAppBotState(str, Enum):
    NEW = "new"
    WAITING_NAME = "waiting_name"
    WAITING_VEHICLE = "waiting_vehicle"
    WAITING_SERVICE = "waiting_service"
    WAITING_DATE = "waiting_date"
    WAITING_TIME = "waiting_time"
    WAITING_LOCATION = "waiting_location"
    CONFIRMING = "confirming"
    COMPLETED = "completed"
    HUMAN_MODE = "human_mode"
    RETURNING_CLIENT_CONFIRM = "returning_client_confirm"


class WhatsAppConversationStatus(str, Enum):
    OPEN = "abierta"
    CLOSED = "cerrada"
    ARCHIVED = "archivada"


class MessageDirection(str, Enum):
    INBOUND = "entrante"
    OUTBOUND = "saliente"


class IntegrationProvider(str, Enum):
    GOOGLE_CALENDAR = "google_calendar"
    GOOGLE_SHEETS = "google_sheets"
    WHATSAPP = "whatsapp"
    CLICKUP = "clickup"


class CompanyStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class IntegrationAccountProvider(str, Enum):
    WHATSAPP_META = "whatsapp_meta"
    GOOGLE_CALENDAR = "google_calendar"
    GOOGLE_SHEETS = "google_sheets"
    CLICKUP = "clickup"
    META_BUSINESS = "meta_business"
    CUSTOM = "custom"


class IntegrationAccountStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    EXPIRED = "expired"


class IntegrationStatus(str, Enum):
    SKIPPED = "omitido"
    SUCCESS = "exitoso"
    FAILED = "fallido"


class InternalBotIntent(str, Enum):
    GET_TODAY_AGENDA = "get_today_agenda"
    GET_TODAY_SALES = "get_today_sales"
    GET_TODAY_CASH_CUT = "get_today_cash_cut"
    GET_OPERATOR_TASKS = "get_operator_tasks"
    GET_PENDING_SERVICES = "get_pending_services"
    GET_IN_PROGRESS_SERVICES = "get_in_progress_services"
    GET_FINISHED_SERVICES = "get_finished_services"
    GET_TODAY_COMMISSIONS = "get_today_commissions"
    GET_OPERATOR_COMMISSIONS = "get_operator_commissions"
    REASSIGN_OPERATOR = "reassign_operator"
    FINISH_SERVICE = "finish_service"
    CREATE_APPOINTMENT = "create_appointment"
    GET_ANALYTICS = "get_analytics"
    GET_NAVIGATION_HELP = "get_navigation_help"
    UNKNOWN = "unknown"


class InternalBotStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    UNKNOWN = "unknown"


class OrderStatus(str, Enum):
    QUEUED = "en_cola"
    IN_PROGRESS = "en_proceso"
    READY = "listo"
    DELIVERED = "entregado"
    CANCELLED = "cancelado"


class OrderPaymentStatus(str, Enum):
    PENDING = "pendiente"
    PARTIAL = "parcial"
    PAID = "pagado"
    CREDIT = "credito"
    COURTESY = "cortesia"


class CashSessionStatus(str, Enum):
    OPEN = "abierta"
    CLOSED = "cerrada"


class CashMovementType(str, Enum):
    INCOME = "ingreso"
    EXPENSE = "egreso"
    WITHDRAWAL = "retiro"
    DEPOSIT = "deposito"


class SalaryFrequency(str, Enum):
    WEEKLY = "semanal"
    BIWEEKLY = "quincenal"
    MONTHLY = "mensual"


class CreditMovementType(str, Enum):
    CHARGE = "cargo"
    PAYMENT = "pago"
    COURTESY = "cortesia"
    ADJUSTMENT = "ajuste"
