from fastapi import APIRouter

from app.routes.api import (
    appointments,
    auth,
    bot,
    cash_cuts,
    cash_sessions,
    catalog_families,
    clients,
    commissions,
    credits,
    dashboard,
    exports,
    integrations,
    invite_codes,
    notifications,
    team_chat,
    orders,
    payments,
    payroll,
    reports,
    services_catalog,
    users,
    vehicles,
)


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(bot.router)
api_router.include_router(users.router)
api_router.include_router(clients.router)
api_router.include_router(vehicles.router)
api_router.include_router(services_catalog.router)
api_router.include_router(catalog_families.router)
api_router.include_router(appointments.router)
api_router.include_router(orders.router)
api_router.include_router(dashboard.router)
api_router.include_router(exports.router)
api_router.include_router(integrations.router)
api_router.include_router(invite_codes.router)
api_router.include_router(team_chat.router)
api_router.include_router(notifications.router)
api_router.include_router(payments.router)
api_router.include_router(cash_cuts.router)
api_router.include_router(cash_sessions.router)
api_router.include_router(commissions.router)
api_router.include_router(credits.router)
api_router.include_router(payroll.router)
api_router.include_router(reports.router)
