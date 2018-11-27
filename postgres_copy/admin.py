from django import forms
from django.contrib import admin
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.generic.base import TemplateResponse
from functools import update_wrapper
from io import TextIOWrapper
from .managers import CopyManager


class CopyImportForm(forms.Form):
    file = forms.FileField()


class CopyAdmin(admin.ModelAdmin):
    actions = ['export_view']
    change_list_template = 'admin/import_change_list.html'
    copy_import_form = CopyImportForm
    copy_mapped_fields = {}
    copy_static_mapping = {}

    def get_urls(self):

        from django.urls import path

        super_urls = super().get_urls()

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name

        url_patterns = [
                   path('import/', wrap(self.import_view), name='%s_%s_import' % info),
                   path('export/', wrap(self.export_view), name='%s_%s_export' % info),
                ]

        return url_patterns + super_urls

    def get_copy_import_form(self):
        return self.copy_import_form

    def import_view(self, request):

        has_error = False

        if not self.copy_mapped_fields and not self.copy_static_mapping:
            error_message = "No fields are mapped yet. Please set <code>copy_mapped_fields</code>" \
                        + " and/or <code>copy_static_mapping</code> on your admin class."
            self.message_user(request, mark_safe(error_message), messages.WARNING)
            has_error = True

        if not isinstance(getattr(self.model, 'objects'), CopyManager):
            error_message = "Please set <code>objects = CopyManager()</code>" \
                        + " on your model in order to continue."
            self.message_user(request, mark_safe(error_message), messages.WARNING)
            has_error = True

        if has_error:
            preserved_filters = self.get_preserved_filters(request)
            redirect_url = reverse('admin:%s_%s_changelist' %
                                   (self.model._meta.app_label, self.model._meta.model_name),
                                   current_app=self.admin_site.name)
            redirect_url = add_preserved_filters({'preserved_filters': preserved_filters,
                                                 'opts': self.model._meta}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        # this form might need to be override-able? give them the option.
        form = self.get_copy_import_form()(data=request.POST or None, files=request.FILES or None)

        context = self.admin_site.each_context(request)
        context.update({
                'app_label': self.model._meta.app_label,
                'form': form,
                'opts': self.model._meta

            })

        if request.method == 'POST':

            if form.is_valid():

                insert_count = self.model.objects.from_csv(TextIOWrapper(form.cleaned_data['file']),
                                                           dict(**self.copy_mapped_fields),
                                                           static_mapping=self.copy_static_mapping)

                self.message_user(request, "Added %s %s." %
                                  (insert_count, self.model._meta.verbose_name_plural),
                                  messages.SUCCESS)

        return TemplateResponse(request, 'admin/upload.html', context)

    def export_view(self, request, queryset):

        filename_slug = self.model._meta.verbose_name_plural.replace(' ', '-')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="export-%s.csv"' % filename_slug
        queryset.to_csv(response)

        return response
    export_view.short_description = 'Export'
