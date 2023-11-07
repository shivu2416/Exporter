from django.contrib import admin
from .models import *


class MemeberView(admin.ModelAdmin):
    list_display = ["firstname"]
    

class TaskView(admin.ModelAdmin):
    list_display = ["title"]
                    
admin.site.register(Member, MemeberView)
admin.site.register(Task, TaskView)
