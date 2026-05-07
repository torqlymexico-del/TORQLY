# Torqly / El Garagillo

Ecosistema modular para la operacion de un negocio de lavado y detallado automotriz. El proyecto corre sobre `FastAPI`, `SQLAlchemy`, `Alembic`, `JWT` y MySQL configurable por `.env`, con panel web ligero orientado a agenda, cobro, operacion y canales externos.

## Estado actual

### FASE 1 implementada
- Login con JWT y cookie `HttpOnly`
- Usuarios y roles
- Clientes
- Vehiculos
- Catalogo de servicios
- Citas manuales
- Agenda diaria
- Dashboard inicial
- Base MySQL por `DATABASE_URL`
- Soft delete y auditoria basica

### FASE 2 implementada
- Integracion modular de Google Calendar
- POS / cobros con extras, descuentos y ticket
- Pagos y resumen de venta
- Comisiones por operador
- Cortes de caja
- Vistas: `/pos`, `/payments`, `/cash-cuts`, `/commissions`

### FASE 3 implementada
- WhatsApp Cloud API con webhook real, envio saliente y persistencia de conversaciones
- Flujo conversacional para capturar nombre, vehiculo, servicio, fecha y hora
- Creacion de cita desde WhatsApp con origen `whatsapp`
- ClickUp real para crear y actualizar tareas
- Webhook de ClickUp para sincronizar tareas terminadas hacia MySQL
- Notificaciones internas en base de datos
- Panel WhatsApp: `/whatsapp/conversations`
- Panel operador: `/operator/tasks`
- Webhooks publicos: `/webhooks/whatsapp` y `/webhooks/clickup`

### FASE 4 implementada
- Bot personal interno por reglas con comandos de consulta y accion
- Historial de comandos en `internal_bot_messages`
- Reportes avanzados con filtros por fecha, operador, servicio y metodo de pago
- Exportaciones a Google Sheets para corte, ventas, comisiones, inventario y agenda
- Automatizaciones internas con APScheduler
- Recordatorios de cita y recordatorios al operador
- Aviso automatico al cliente cuando el servicio termina
- Cierre diario sugerido con exportacion opcional a Google Sheets
- Monitor de stock bajo
- Dashboard reforzado con alertas, tareas por operador y errores de integracion
- Centro de notificaciones: `/notifications`
- Vista del bot: `/bot`
- Vista de reportes: `/reports`

Si faltan credenciales externas, el sistema sigue operando. La app muestra advertencias en `/health`, registra `integration_logs` y no rompe los flujos internos.

## Stack

- Backend: `FastAPI`
- ORM: `SQLAlchemy 2.x`
- Migraciones: `Alembic`
- DB: `MySQL` mediante `PyMySQL`
- Auth: `JWT`
- Frontend: HTML server-rendered + CSS local
- Integraciones: WhatsApp Cloud API, Google Calendar, ClickUp
- Configuracion: `.env`

## Estructura

```text
app/
  main.py
  config.py
  database.py
  dependencies.py
  security.py
  enums.py
  models/
  schemas/
  routes/
    api/
    web/
  services/
  integrations/
    whatsapp/
    google/
    clickup/
  templates/
  static/
  utils/
alembic/
scripts/
requirements.txt
.env.example
README.md
```

## Archivos importantes

### Nucleo
- `app/main.py`
  Crea la app, monta estaticos, registra routers y expone webhooks publicos.
- `app/config.py`
  Centraliza variables desde `.env`, URL de MySQL y estado de integraciones.
- `app/database.py`
  Engine y sesiones SQLAlchemy.
- `app/security.py`
  Hash de contrasenas y JWT.
- `app/dependencies.py`
  Usuario actual y control de roles.

### Dominio y orquestacion
- `app/services/appointments.py`
  Flujo principal de citas y sincronizacion con Google, ClickUp, WhatsApp y notificaciones.
- `app/services/payments.py`
  POS y cobros.
- `app/services/cash_cuts.py`
  Cortes de caja.
- `app/services/commissions.py`
  Comisiones.
- `app/services/notifications.py`
  Notificaciones internas.
- `app/services/whatsapp_conversations.py`
  Conversaciones, mensajes, modo humano y creacion de citas desde chat.
- `app/services/service_jobs.py`
  Tareas del operador: iniciar, terminar y reportar problemas.
- `app/services/clickup_webhooks.py`
  Sincronizacion desde webhook de ClickUp hacia MySQL.
- `app/services/internal_bot/`
  Parser por reglas y ejecucion del bot interno.
- `app/services/automations/service.py`
  Recordatorios, cierre diario, stock bajo y avisos operativos.
- `app/services/scheduler.py`
  Scheduler con APScheduler para automatizaciones periodicas.
- `app/services/reports.py`
  Reportes avanzados, agregaciones y filtros.

### Integraciones
- `app/integrations/google/calendar.py`
  Crea, actualiza o cancela eventos de Google Calendar.
- `app/integrations/google/sheets.py`
  Exportaciones operativas a Google Sheets.
- `app/integrations/whatsapp/client.py`
  Envio saliente a WhatsApp Cloud API.
- `app/integrations/whatsapp/webhook.py`
  Verificacion de token, firma y parser del webhook.
- `app/integrations/clickup/client.py`
  Creacion y actualizacion de tareas en ClickUp.

### Interfaz
- `app/routes/web/whatsapp.py`
  Panel de conversaciones y respuesta manual.
- `app/routes/web/operator_tasks.py`
  Panel de tareas del operador.
- `app/templates/whatsapp/index.html`
  Inbox y detalle de chat.
- `app/templates/operator_tasks/index.html`
  Vista operativa del lavador / operador.

### Infra
- `alembic/versions/20260424_0001_initial_schema.py`
  Migracion base.
- `alembic/versions/20260424_0002_phase2_operations.py`
  Migracion FASE 2.
- `alembic/versions/20260424_0003_phase3_channels_and_notifications.py`
  Migracion FASE 3.
- `alembic/versions/20260425_0004_phase4_bot_scheduler_and_stock.py`
  Migracion FASE 4.

## Modelos creados

- `users`
- `clients`
- `vehicles`
- `services_catalog`
- `appointments`
- `service_jobs`
- `payments`
- `payment_items`
- `commissions`
- `cash_cuts`
- `inventory_products`
- `inventory_movements`
- `whatsapp_conversations`
- `whatsapp_messages`
- `notifications`
- `internal_bot_messages`
- `audit_logs`
- `integration_logs`

## Requisitos previos

- Python 3.11+
- MySQL 8+ o compatible
- Base de datos creada, por ejemplo `torqly_db`

## Instalacion local

### Windows PowerShell
```powershell
.\scripts\install.ps1
```

### Linux / macOS
```bash
chmod +x scripts/install.sh scripts/run.sh
./scripts/install.sh
```

## Configuracion

1. Copia `.env.example` a `.env`
2. Ajusta `DATABASE_URL` a tu MySQL
3. Configura `SECRET_KEY`
4. Configura `APP_PUBLIC_URL` con una URL publica si vas a probar webhooks externos
5. Opcional: activa bootstrap admin

```env
BOOTSTRAP_ADMIN_ON_STARTUP=true
DEFAULT_ADMIN_PHONE=6140000000
DEFAULT_ADMIN_PASSWORD=ChangeMe123!
```

### Prueba local rapida

Si solo quieres validar el sistema localmente sin preparar MySQL todavia, puedes usar SQLite:

```env
DATABASE_URL=sqlite:///./torqly_local.db
BOOTSTRAP_ADMIN_ON_STARTUP=true
DEFAULT_ADMIN_PHONE=6140000000
DEFAULT_ADMIN_PASSWORD=ChangeMe123!
```

Luego ejecuta migraciones y levanta la app. Cuando quieras volver a MySQL, solo cambia `DATABASE_URL`.

## Variables importantes de `.env`

### Base

```env
APP_PUBLIC_URL=http://127.0.0.1:8000
BASE_URL=http://127.0.0.1:8000
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/torqly_db
```

### WhatsApp Cloud API

```env
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_API_VERSION=v20.0
WHATSAPP_WEBHOOK_SECRET=
```

Nota:
- El proyecto sigue aceptando las variables legacy `META_WHATSAPP_*` por compatibilidad.
- `WHATSAPP_WEBHOOK_SECRET` es opcional. Si lo configuras, la firma del webhook se valida.

### Google Calendar

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_PROJECT_ID=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/api/v1/integrations/google/callback
GOOGLE_CALENDAR_ID=primary
GOOGLE_SERVICE_ACCOUNT_FILE=
GOOGLE_REFRESH_TOKEN=
GOOGLE_TOKEN_URI=https://oauth2.googleapis.com/token
GOOGLE_CALENDAR_SCOPES=https://www.googleapis.com/auth/calendar
GOOGLE_CALENDAR_SEND_UPDATES=all
```

### Google Sheets

```env
GOOGLE_SHEETS_ENABLED=false
GOOGLE_SHEETS_SPREADSHEET_ID=
GOOGLE_SHEETS_CREDENTIALS_FILE=
```

### ClickUp

```env
CLICKUP_API_TOKEN=
CLICKUP_TEAM_ID=
CLICKUP_SPACE_ID=
CLICKUP_FOLDER_ID=
CLICKUP_LIST_ID=
CLICKUP_WEBHOOK_SECRET=
```

### Scheduler y automatizaciones

```env
SCHEDULER_ENABLED=true
DAILY_CLOSE_TIME=20:00
```

## Migraciones

### Windows PowerShell
```powershell
.\.venv\Scripts\alembic upgrade head
```

### Linux / macOS
```bash
source .venv/bin/activate
alembic upgrade head
```

Las migraciones son incrementales. Si cambias modelos en el futuro, crea una revision nueva; no modifiques las migraciones historicas.

## Arranque

### Windows
```powershell
.\scripts\run.ps1
```

### Windows con `.bat`
```powershell
.\scripts\run.bat
```

### Arranque de un clic
```powershell
.\iniciar_servidor.bat
```

Este lanzador:
- crea `.env` si no existe
- crea `.venv` e instala dependencias si hace falta
- corre migraciones
- inicia el servidor si todavia no esta arriba
- abre `/login` automaticamente

### Linux / macOS
```bash
./scripts/run.sh
```

### Manual

```powershell
.\.venv\Scripts\uvicorn app.main:app --reload
```

La aplicacion queda en:
- [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Docs API: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Endpoints relevantes

### Auth
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

### Citas
- `GET /api/v1/appointments`
- `POST /api/v1/appointments`
- `PUT /api/v1/appointments/{id}`
- `POST /api/v1/appointments/{id}/cancel`

### Pagos y cortes
- `GET /api/v1/payments`
- `POST /api/v1/payments`
- `GET /api/v1/cash-cuts/daily`
- `POST /api/v1/cash-cuts`

### Comisiones y reportes
- `GET /api/v1/commissions`
- `GET /api/v1/commissions/operators/{operator_id}`
- `GET /api/v1/reports/basic-summary`
- `GET /api/v1/reports/daily`
- `GET /api/v1/reports/weekly`
- `GET /api/v1/reports/operators`
- `GET /api/v1/reports/services`
- `GET /api/v1/reports/sales`
- `GET /api/v1/reports/commissions`

### Endpoints directos FASE 4
- `POST /bot/command`
- `GET /bot/history`
- `GET /reports/daily`
- `GET /reports/weekly`
- `GET /reports/operators`
- `GET /reports/services`
- `GET /reports/sales`
- `GET /reports/commissions`
- `POST /exports/google-sheets/daily-cut`
- `POST /exports/google-sheets/sales`
- `POST /exports/google-sheets/commissions`
- `POST /exports/google-sheets/inventory`
- `POST /exports/google-sheets/agenda`

### Integraciones y webhooks
- `GET /api/v1/integrations/status`
- `GET /webhooks/whatsapp`
- `POST /webhooks/whatsapp`
- `POST /webhooks/clickup`
- Compatibilidad previa:
  - `GET /api/v1/integrations/whatsapp/webhook`
  - `POST /api/v1/integrations/whatsapp/webhook`
  - `POST /api/v1/integrations/clickup/webhook`

## Configuracion de WhatsApp Cloud API

### 1. Meta app

1. Crea una app en Meta for Developers
2. Activa WhatsApp Cloud API
3. Obtiene:
   - `WHATSAPP_ACCESS_TOKEN`
   - `WHATSAPP_PHONE_NUMBER_ID`
   - `WHATSAPP_BUSINESS_ACCOUNT_ID`
4. Define `WHATSAPP_VERIFY_TOKEN` en `.env`

### 2. Webhook de Meta

Configura en Meta:
- Callback URL: `https://TU-URL-PUBLICA/webhooks/whatsapp`
- Verify token: el mismo valor de `WHATSAPP_VERIFY_TOKEN`

Cuando Meta haga la verificacion, la app responde desde:
- `GET /webhooks/whatsapp`

Los mensajes entrantes llegan a:
- `POST /webhooks/whatsapp`

### 3. Flujo implementado

- Mensaje inicial
- Solicitud de nombre
- Solicitud de vehiculo
- Solicitud de servicio
- Solicitud de fecha
- Solicitud de hora
- Confirmacion
- Creacion de cita
- Sincronizacion con Google Calendar si esta configurado
- Sincronizacion con ClickUp si esta configurado
- Confirmacion por WhatsApp

### 4. Modo humano

Desde `/whatsapp/conversations` puedes:
- Activar modo humano
- Desactivar modo humano
- Responder manualmente
- Relacionar cliente
- Crear cita desde la conversacion

Si la conversacion esta en modo humano, el bot deja de responder.

## Configuracion de ClickUp

### 1. API

1. Genera `CLICKUP_API_TOKEN`
2. Ubica `CLICKUP_LIST_ID`
3. Opcional: configura `clickup_user_id` en cada operador desde `/panel/usuarios` para asignacion automatica

### 2. Webhook

Configura un webhook en ClickUp apuntando a:
- `https://TU-URL-PUBLICA/webhooks/clickup`

Si defines `CLICKUP_WEBHOOK_SECRET`, la firma entrante se valida.

### 3. Comportamiento implementado

- Al crear una cita, se intenta crear tarea ClickUp
- Al actualizar fecha, hora, operador o estado, se intenta actualizar la tarea
- Al cancelar o terminar un servicio, se intenta sincronizar el estado
- Si ClickUp marca una tarea como terminada por webhook, la app:
  - actualiza MySQL
  - cierra `service_job`
  - genera notificacion interna
  - manda mensaje por WhatsApp al cliente si hay telefono

## Uso de ngrok para pruebas locales

Si pruebas desde tu laptop local, usa una URL publica temporal:

```bash
ngrok http 8000
```

Luego coloca la URL HTTPS publica en:
- `APP_PUBLIC_URL`
- Callback URL de Meta
- Webhook URL de ClickUp

Ejemplo:

```env
APP_PUBLIC_URL=https://abcd-1234.ngrok-free.app
```

## Flujo de sincronizacion implementado

### Al crear cita
- Guarda en MySQL
- Intenta crear Google Calendar
- Intenta crear ClickUp
- Intenta notificar al cliente por WhatsApp
- Genera notificaciones internas

### Al cancelar cita
- Actualiza MySQL
- Intenta cancelar Google Calendar
- Intenta actualizar ClickUp
- Intenta avisar al cliente por WhatsApp
- Genera notificacion interna

### Al terminar desde ClickUp
- Webhook entra por `/webhooks/clickup`
- Se localiza `clickup_task_id`
- Se marca la cita y el `service_job` como terminados
- Se genera notificacion interna
- Se envia WhatsApp al cliente si aplica

## Bot interno

Vista:
- `/bot`

API:
- `POST /api/v1/bot/command`
- `GET /api/v1/bot/history`
- aliases equivalentes: `POST /bot/command` y `GET /bot/history`

Comandos soportados:
- `agenda de hoy`
- `ventas de hoy`
- `corte de hoy`
- `tareas de Juan`
- `servicios pendientes`
- `servicios en proceso`
- `servicios terminados`
- `comisiones de hoy`
- `comisiones de Juan`
- `reasigna el Civic negro a Pedro`
- `marca terminado el servicio 152`
- `crea cita para mañana a las 10 lavado premium Civic negro`

Si el parser no reconoce el texto, responde:
- `No entendi el comando. Prueba con: agenda de hoy, ventas de hoy, tareas de Juan.`

El bot usa datos reales de MySQL y guarda historial en `internal_bot_messages`.

## Reportes avanzados

Vista:
- `/reports`

Filtros disponibles:
- fecha inicial
- fecha final
- operador
- servicio
- metodo de pago

Indicadores implementados:
- ventas por dia
- ventas por metodo de pago
- servicios mas vendidos
- servicios cancelados
- ticket promedio
- operador con mas servicios
- operador con mas comisiones
- horas pico
- duracion promedio por servicio
- clientes frecuentes

## Google Sheets

Configuracion minima:
1. Activa `GOOGLE_SHEETS_ENABLED=true`
2. Define `GOOGLE_SHEETS_SPREADSHEET_ID`
3. Define `GOOGLE_SHEETS_CREDENTIALS_FILE` o reutiliza las credenciales de Google ya configuradas

Exports implementados:
- corte diario
- ventas diarias
- comisiones
- inventario
- agenda

Si faltan credenciales, la app:
- no se cae
- responde `status=skipped`
- registra el evento en `integration_logs`
- deja advertencia visible en `/health`

## Scheduler y automatizaciones

Configuracion:
```env
SCHEDULER_ENABLED=true
DAILY_CLOSE_TIME=20:00
```

Tareas automaticas:
- cada 5 minutos: revisa citas proximas y lanza recordatorios
- cada 30 minutos: revisa stock bajo
- diario a `DAILY_CLOSE_TIME`: genera corte sugerido y exporta si Google Sheets esta activo

Automatizaciones incluidas:
- Recordatorio al cliente 1 hora antes de la cita
- Recordatorio al operador 30 minutos antes
- Mensaje `Tu vehiculo ya esta listo.` al terminar un servicio
- Notificacion para caja cuando un servicio queda listo para cobro
- Cierre diario sugerido
- Alerta de stock bajo

## Pruebas locales exactas de FASE 4

### 1. Preparar entorno

1. Copia `.env.example` a `.env`
2. Configura `DATABASE_URL`
3. Si vas a usar webhooks externos, configura `APP_PUBLIC_URL`
4. Si vas a exportar a Sheets, configura `GOOGLE_SHEETS_ENABLED`, `GOOGLE_SHEETS_SPREADSHEET_ID` y credenciales
5. Ajusta `SCHEDULER_ENABLED` y `DAILY_CLOSE_TIME` si quieres validar automatizaciones
4. Ejecuta `.\scripts\install.ps1`
5. Ejecuta `.\.venv\Scripts\alembic upgrade head`
6. Levanta el servidor con `.\scripts\run.ps1`

### 2. Probar WhatsApp -> MySQL

1. Configura Meta o usa un emisor real de webhook
2. Verifica Meta con `GET /webhooks/whatsapp`
3. Envía un mensaje al numero conectado
4. Completa el flujo: nombre, vehiculo, servicio, fecha, hora, confirmacion
5. Verifica en la base:
   - `whatsapp_conversations`
   - `whatsapp_messages`
   - `appointments` con origen `whatsapp`

### 3. Probar MySQL -> Google Calendar

1. Configura Google Calendar
2. Repite una cita desde panel o desde WhatsApp
3. Verifica `appointments.google_event_id`
4. Si Google no esta configurado, valida que la cita se guarde y el warning aparezca en `/health`

### 4. Probar MySQL -> ClickUp

1. Configura `CLICKUP_API_TOKEN` y `CLICKUP_LIST_ID`
2. Asigna `clickup_user_id` al operador si quieres assignee automatico
3. Crea una cita
4. Verifica `appointments.clickup_task_id` y `appointments.clickup_task_url`

### 5. Probar ClickUp -> Dashboard

1. Configura webhook de ClickUp apuntando a `/webhooks/clickup`
2. Marca una tarea como terminada en ClickUp
3. Verifica:
   - `appointments.status = terminado`
   - `service_jobs.status = terminado`
   - nueva fila en `notifications`
   - mensaje saliente al cliente en `whatsapp_messages` si hay telefono

### 6. Probar panel WhatsApp

1. Entra a `/whatsapp/conversations`
2. Verifica lista de conversaciones y mensajes
3. Activa modo humano
4. Responde manualmente
5. Relaciona un cliente
6. Crea una cita desde la conversacion

### 7. Probar panel operador

1. Asigna una cita a un operador
2. Inicia sesion con ese operador
3. Entra a `/operator/tasks`
4. Usa `Iniciar`
5. Usa `Terminar`
6. Usa `Reportar problema`

### 8. Probar bot interno

1. Entra a `/bot` con admin o supervisor
2. Ejecuta `agenda de hoy`
3. Ejecuta `ventas de hoy`
4. Ejecuta `tareas de Juan`
5. Ejecuta `marca terminado el servicio 152` usando un ID real
6. Ejecuta `crea cita para manana a las 10 lavado premium Civic negro`
7. Verifica historial en `/bot` o `GET /bot/history`

### 9. Probar reportes

1. Entra a `/reports`
2. Filtra por fecha, operador, servicio y metodo
3. Verifica tablas de ventas, servicios, clientes, duraciones y horas pico
4. Prueba tambien `GET /reports/daily` y `GET /reports/sales`

### 10. Probar exportaciones a Google Sheets

1. Configura Google Sheets real
2. Ejecuta:
   - `POST /exports/google-sheets/daily-cut`
   - `POST /exports/google-sheets/sales`
   - `POST /exports/google-sheets/commissions`
   - `POST /exports/google-sheets/inventory`
   - `POST /exports/google-sheets/agenda`
3. Verifica las pestañas en el spreadsheet
4. Si falta credencial, confirma que la respuesta sea `skipped` y que la app siga operando

### 11. Probar scheduler y automatizaciones

1. Crea una cita para dentro de 60 minutos con telefono de cliente
2. Espera la corrida del scheduler o llama manualmente a los servicios desde shell
3. Verifica mensaje saliente y notificacion interna
4. Crea una cita para dentro de 30 minutos con operador asignado y telefono del operador
5. Verifica recordatorio interno
6. Termina un servicio y valida:
   - mensaje al cliente
   - notificacion `Servicio listo para cobro`
7. Baja el stock de un producto a su minimo y espera la revision de stock
8. Ajusta `DAILY_CLOSE_TIME` cercano, reinicia la app y verifica corte sugerido al cierre

## Permisos por rol

- `admin`
  Control total
- `supervisor`
  Agenda, operadores, reportes, bot interno, reasignacion y seguimiento operativo
- `cashier`
  POS, pagos, cortes, agenda, clientes, vehiculos y reportes operativos
- `operator`
  Solo tareas asignadas, iniciar, terminar y reportar problema

## Notas de diseno

- Se usa soft delete en entidades operativas para no perder historial.
- La logica de negocio vive en `services/`, no en routers.
- Las integraciones estan desacopladas en `integrations/`.
- Los webhooks publicos no requieren login y estan excluidos del redirect al formulario.
- El esquema sigue listo para crecer a multi-tenant/SaaS con separacion futura por negocio o workspace.

## Checklist final del sistema

- FASE 1: login, usuarios, clientes, vehiculos, servicios, citas, agenda y MySQL
- FASE 2: Google Calendar, POS, pagos, cortes y comisiones
- FASE 3: WhatsApp Cloud API, ClickUp, webhooks, panel de conversaciones, panel operador y notificaciones
- FASE 4: bot interno, reportes avanzados, Google Sheets, automatizaciones, scheduler, dashboard mejorado y centro de notificaciones
- Integraciones desacopladas y tolerantes a credenciales faltantes
- Migraciones incrementales con Alembic
- Compatibilidad local con SQLite para smoke test y MySQL para operacion
- Base lista para seguir hacia multi-sucursal o SaaS
