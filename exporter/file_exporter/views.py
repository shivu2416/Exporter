from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.generics import ListAPIView

from lib.exporter import ExportPDFMixin, ListExportMixin
from .serializers import *



class Test(
    ExportPDFMixin,
    ListExportMixin,
    ListAPIView
):
    serializer_class = MembersSerialzer
    export_serializer_class = MembersSerialzer
    bold_rows = [0]
    export_file_name = "Exported file"
    
    def get_queryset(self):
        return Member.objects.all()
    
    def export_objects(self):
        self.action = "list"
        download_format = self.get_download_format()
        if download_format:
            if self.action == "list":
                objects = self.get_export_objects()
            elif self.action == "retrieve":
                objects = [self.get_export_object()]
            if download_format == "csv":
                return self.download_csv(objects)
            if download_format == "json":
                return self.download_json(objects)
            if download_format == "xlsx":
                return self.download_xlsx(objects)
            if download_format == "pdf":
                return self.download_pdf(objects)
            if download_format == "docx":
                return self.download_docx(objects)
        return None

    
    
    
from rest_framework import viewsets
from .models import Task
from .serializers import TaskSerializer

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer