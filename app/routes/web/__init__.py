from fastapi import APIRouter

from app.routes.web import (
    agenda,
    appointments,
    auth,
    bot,
    cash_cuts,
    clients,
    commissions,
    companies,
    dashboard,
    integrations,
    notifications,
    operator_tasks,
    payments,
    pos,
    reports,
    services_catalog,
    users,
    vehicles,
    whatsapp,
)


web_router = APIRouter()
web_router.include_router(auth.router)
web_router.include_router(dashboard.router)
web_router.include_router(integrations.router)
web_router.include_router(companies.router)
web_router.include_router(bot.router)
web_router.include_router(users.router)
web_router.include_router(clients.router)
web_router.include_router(vehicles.router)
web_router.include_router(services_catalog.router)
web_router.include_router(appointments.router)
web_router.include_router(agenda.router)
web_router.include_router(pos.router)
web_router.include_router(payments.router)
web_router.include_router(cash_cuts.router)
web_router.include_router(commissions.router)
web_router.include_router(reports.router)
web_router.include_router(notifications.router)
web_router.include_router(whatsapp.router)
web_router.include_router(operator_tasks.router)
