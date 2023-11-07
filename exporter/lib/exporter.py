import csv
from io import BytesIO

import xlsxwriter
from django.http import StreamingHttpResponse
from django.template import loader
from django.utils.functional import cached_property
from rest_framework.exceptions import (
    MethodNotAllowed,
    NotFound,
)

import weasyprint
from django.http import Http404, StreamingHttpResponse
from django.template.loader import get_template
# from docx import Document


class Exporter:
    """ Utility class for exporting data to csv or xlsx format """

    def __init__(self, serializer, labels=None, objects=None, obj=None, context=None):
        self.obj = obj
        self.objects = objects if objects else []
        if obj:
            self.objects.append(obj)
        self.serializer = serializer
        self._labels = labels
        self.context = context

    @cached_property
    def labels(self):
        if self._labels:
            return self._labels
        serializer = self.serializer()
        return {field_name: serializer.fields[field_name].label for field_name in serializer.fields if field_name != 'answer_options'}

    @property
    def row_labels(self):
        return list(self.labels.values())

    @property
    def rows(self):
        serializer_kwargs = {
            'many': True
        }
        if self.context:
            serializer_kwargs['context'] = self.context
        items = self.serializer(self.objects, **serializer_kwargs).data
        for item in items:
            yield [item.get(field_name) for field_name in self.labels]
            try:
                answerOptions = item.pop('answer_options')
                if answerOptions:
                    for answerOption in answerOptions:
                        yield [answerOption.get(field_name) for field_name in self.labels]
            except:
                pass


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


class ExportMixin:
    """ A mixin class that plays nicely with drf viewset """
    exporter_class = Exporter
    export_serializer_class = None
    bold_rows = set()  # list of row number that should be set to bold
    csv_delimeter = ','
    export_file_name = 'export'

    def get_export_serializer_context(self):
        return {}

    def get_export_serializer_class(self):
        return self.export_serializer_class

    def get_export_filename(self, queryset):
        return self.export_file_name

    def get_download_format(self, *args):
        download_format = self.request.GET.get('export')
        if download_format in ['csv', 'xlsx', 'pdf', 'docx','json']:
            return download_format
        return None

    def get_bold_rows(self):
        return self.bold_rows

    def get_exporter_class(self):
        return self.exporter_class

    def get_exporter(self, queryset):
        context = self.get_export_serializer_context()
        return self.get_exporter_class()(self.get_export_serializer_class(), objects=queryset, context=context)

    def get_export_objects(self):
        return []

    def get_export_object(self):
        return {}

    def get_export_rows(self, queryset):
        exporter = self.get_exporter(queryset)
        yield exporter.row_labels
        yield from exporter.rows

    def export_objects(self):
        download_format = self.get_download_format()
        if download_format:
            if self.action == 'list':
                objects = self.get_export_objects()
            elif self.action == 'retrieve':
                objects = [self.get_export_object()]
            else:
                raise MethodNotAllowed
            if download_format == 'csv':
                return self.download_csv(objects)
            if download_format == 'json':
                return self.download_json(objects)
            if download_format == 'xlsx':
                return self.download_xlsx(objects)
            if download_format == 'pdf':
                return self.download_pdf(objects)
            if download_format == 'docx':
                return self.download_docx(objects)
        return None

    def write_xlsx_rows(self, sheet, queryset, book):
        bold_cell_format = book.add_format({'bold': True})
        for row_number, row in enumerate(self.get_export_rows(queryset)):
            should_be_bold = row_number in self.get_bold_rows()
            for column_number, cell_data in enumerate(row):
                sheet.write(
                    row_number,
                    column_number,
                    str(cell_data) if cell_data is not None else '',
                    bold_cell_format if should_be_bold else None
                )

    def download_xlsx(self, queryset):
        output = BytesIO()
        book = xlsxwriter.Workbook(output)
        sheet = book.add_worksheet()
        self.write_xlsx_rows(sheet, queryset, book)
        book.close()  # close book and save it in "output"
        output.seek(0)  # seek stream on begin to retrieve all data from it

        # send "output" object to stream with mimetype and filename
        response = StreamingHttpResponse(
            output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{self.get_export_filename(queryset)}.xlsx'
        return response

    def get_csv_delimeter(self):
        return self.csv_delimeter

    def download_csv(self, queryset):
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer, delimiter=self.get_csv_delimeter(), dialect='excel')
        response = StreamingHttpResponse((writer.writerow(row) for row in self.get_export_rows(queryset)),
                                         content_type="text/csv")
        response['Content-Disposition'] = f'attachment; filename="{self.get_export_filename(queryset)}.csv"'
        return response

    def download_json(self, queryset): 
        from django.http import HttpResponse       
        response = HttpResponse(
                queryset,
                content_type="application/force-download")
        response['Content-Disposition'] = f'attachment; filename="{self.get_export_filename(queryset)}.json"'
        return response

    def download_pdf(self, queryset):
        raise NotFound

    def download_docx(self, queryset):
        raise NotFound


class ListExportMixin(ExportMixin):

    def get_export_ids(self):
        return self.request.GET.getlist('export_ids', [])

    def get_export_objects(self):
        queryset = self.filter_queryset(self.get_queryset())
        export_ids = self.get_export_ids()
        if export_ids:
            queryset = queryset.filter(id__in=export_ids)
        return queryset

    def list(self, request, *args, **kwargs):
        return self.export_objects() or super().list(request, *args, **kwargs)


class RetrieveExportMixin(ExportMixin):

    def get_export_object(self):
        return self.get_object()

    def retrieve(self, request, *args, **kwargs):
        return self.export_objects() or super().retrieve(request, *args, **kwargs)


class ExporterWithFieldGetters(Exporter):
    @property
    def rows(self):
        serializer_kwargs = {
            'many': True
        }
        if self.context:
            serializer_kwargs['context'] = self.context
        items = self.serializer(self.objects, **serializer_kwargs).data
        for item in items:
            yield [
                getattr(self, f"get_{field_name}", self.get_default_value)(item, field_name)
                for field_name in self.labels
            ]

    def get_default_value(self, item, field_name):
        return item[field_name]


class ExportPDFMixin:
    """
        Exports all rows as table in pdf
    """
    html_template ="empty.html"

    def get_pdf_context(self, queryset):
        return {
            "export_rows": self.get_export_rows(queryset),
            "bold_rows": self.get_bold_rows()
        }

    def get_rendered_pdf_html(self, queryset):
        context = self.get_pdf_context(queryset)
        template = get_template(self.html_template)
        return template.render(context)

    def download_pdf(self, queryset):
        html = self.get_rendered_pdf_html(queryset)

        doc = weasyprint.HTML(string=html)
        output = doc.write_pdf()
        response = StreamingHttpResponse(
            BytesIO(output), content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{self.get_export_filename(queryset)}.pdf'
        return response