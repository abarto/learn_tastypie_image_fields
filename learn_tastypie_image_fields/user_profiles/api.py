import base64
import os
import mimetypes

from django import forms
from django.conf.urls import url
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files.uploadedfile import SimpleUploadedFile

from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from tastypie.http import HttpGone, HttpMultipleChoices, HttpCreated, HttpBadRequest
from tastypie.resources import ModelResource
from tastypie.utils import trailing_slash
from tastypie_oauth.authentication import OAuth20Authentication

from .models import UserProfile


class Base64FileField(fields.FileField):
    """
    A django-tastypie field for handling file-uploads through raw post data.
    It uses base64 for en-/decoding the contents of the file.
    Usage:
    class MyResource(ModelResource):
        file_field = Base64FileField("file_field")
        class Meta:
            queryset = ModelWithFileField.objects.all()
    In the case of multipart for submission, it would also pass the filename.
    By using a raw post data stream, we have to pass the filename within our
    file_field structure:
    file_field = {
        "name": "myfile.png",
        "file": "longbas64encodedstring",
        "content_type": "image/png" # on hydrate optional
    }
    Your file_field will by dehydrated in the above format if the return64
    keyword argument is set to True on the field, otherwise it will simply
    return the URL.
    """

    def __init__(self, *args, **kwargs):
        self.return64 = kwargs.pop('return64', False)
        super(Base64FileField, self).__init__(*args, **kwargs)

    def _url(self, obj):
        instance = getattr(obj, self.instance_name, None)
        try:
            url = getattr(instance, 'url', None)
        except ValueError:
            url = None
        return url

    def dehydrate(self, bundle, **kwargs):
        if not self.return64:
            return self._url(bundle.obj)
        else:
            if (not self.instance_name in bundle.data
                    and hasattr(bundle.obj, self.instance_name)):
                file_field = getattr(bundle.obj, self.instance_name)
                if file_field:
                    content_type, encoding = mimetypes.guess_type(
                        file_field.file.name)
                    b64 = open(
                        file_field.file.name, "rb").read().encode("base64")
                    ret = {"name": os.path.basename(file_field.file.name),
                           "file": b64,
                           "content-type": (content_type or
                                            "application/octet-stream")}
                    return ret
            return None

    def hydrate(self, obj):
        value = super(Base64FileField, self).hydrate(obj)
        if value and isinstance(value, dict):
            return SimpleUploadedFile(value["name"],
                                      base64.b64decode(value["file"]),
                                      value.get("content_type",
                                                "application/octet-stream"))
        elif isinstance(value, basestring):
            if value == self._url(obj.obj):
                return getattr(obj.obj, self.instance_name).name
            return value
        else:
            return None


class UserProfileResource(ModelResource):
    # Suggested by https://github.com/django-tastypie/django-tastypie/issues/42
    image = Base64FileField("image", null=True, blank=True)

    class Meta:
        queryset = UserProfile.objects.all()
        resource_name = 'user_profiles'
        authentication = OAuth20Authentication()
        authorization = DjangoAuthorization()


class UploadFileForm(forms.Form):
    upload = forms.FileField()


class UserProfileNestedImageResource(ModelResource):
    def prepend_urls(self):
        return [
            url(
                r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/image%s$" % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('set_image'),
                name="user_profile_set_image"
            ),
        ]

    def set_image(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        self.is_authenticated(request)
        self.throttle_check(request)

        try:
            bundle = self.build_bundle(data={'pk': kwargs['pk']}, request=request)
            user_profile = self.cached_obj_get(bundle=bundle, **self.remove_api_resource_names(kwargs))
        except ObjectDoesNotExist:
            return HttpGone()
        except MultipleObjectsReturned:
            return HttpMultipleChoices("More than one resource is found at this URI.")

        form = UploadFileForm(request.POST, request.FILES)

        if form.is_valid():
            user_profile.image.delete()

            upload = request.FILES['upload']

            user_profile.image.save(upload.name, upload)

            return HttpCreated(location=user_profile.image.url)
        else:
            return HttpBadRequest()

    class Meta:
        queryset = UserProfile.objects.all()
        resource_name = 'user_profiles_nested_image'
        authentication = OAuth20Authentication()
        authorization = DjangoAuthorization()
