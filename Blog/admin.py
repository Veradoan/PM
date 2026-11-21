from django.contrib import admin
from .models import Document, Faculty, Course, Rate, Comment, Report


admin.site.register(Faculty)
admin.site.register(Course)
admin.site.register(Document)
admin.site.register(Rate)
admin.site.register(Comment)
admin.site.register(Report)
