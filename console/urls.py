from django.urls import path

from console import views, views_reports

app_name = "console"

urlpatterns = [
    path("", views.tickets, name="tickets"),
    path("sign-in", views.sign_in, name="sign-in"),
    path("sign-out", views.sign_out, name="sign-out"),
    path("tickets/<str:ticket_id>", views.ticket, name="ticket"),
]

# Report pages (4.U3)
urlpatterns += [
    path(
        "tickets/<str:ticket_id>/reports/<str:kind>",
        views_reports.report,
        name="report",
    ),
    path(
        "tickets/<str:ticket_id>/reports/<str:kind>/record",
        views_reports.record,
        name="record",
    ),
    path("tickets/<str:ticket_id>/close", views_reports.close, name="close"),
]
