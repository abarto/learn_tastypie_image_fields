learn_tastypie_image_fields
===========================

Introduction
------------

This project was created to provide a complete example that illustrates how to implement image uploads and models with image fields with `Tastypie <http://tastypieapi.org/>`_. It is based on a `similar project <https://github.com/abarto/learn_drf_with_images>`_ that used `Django REST Framework <http://www.django-rest-framework.org/>`_.

The model
---------

There's only one class that represents the typical "User Profile" use case on a `Django <https://www.djangoproject.com/>`_ site:

::

    def upload_to(instance, filename):
        return 'user_profile_image/{}/{}'.format(instance.user_id, filename)


    class UserProfile(models.Model):
        GENDER_UNKNOWN = 'U'
        GENDER_MALE = 'M'
        GENDER_FEMALE = 'F'
        GENDER_CHOICES = (
            (GENDER_UNKNOWN, _('unknown')),
            (GENDER_MALE, _('male')),
            (GENDER_FEMALE, _('female')),
        )

        user = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True)
        date_of_birth = models.DateField(_('date of birth'), blank=True, null=True)
        phone_number = PhoneNumberField(_('phone number'), blank=True)
        gender = models.CharField(_('gender'), max_length=1, choices=GENDER_CHOICES, default=GENDER_UNKNOWN)
        image = models.ImageField(_('image'), blank=True, null=True, upload_to=upload_to)

With the exception of the ``phone_number`` field (which uses `django-phonenumber-field <https://github.com/stefanfoulis/django-phonenumber-field>`_), the rest of the fields are regular Django fields, including the ``image`` which is the subject of this project and represents an image for the associated user.

The API
-------

While researching a solution for the image upload problem I noticed that there are many ways to tackle the problem. I chose two that made more sense (at least to me):

* Using Base64FileField, as suggested in Tastypie's `issue #42 <https://github.com/django-tastypie/django-tastypie/issues/42>`_.
* Using a nested resource, which is pretty much the same as I did in the `similar other project <https://github.com/abarto/learn_drf_with_images>`_.

Authentication
--------------

Before I show you my solutions, I wanted to bring to your attention that the project's API is using OAuth2 authentication using `django-tastypie-oauth <https://github.com/orcasgit/django-tastypie-oauth>`_ with the `django-oauth-toolkit <https://github.com/evonove/django-oauth-toolkit>`_ backend. The following session shows the typical workflow of requesting an access token and consuming one of the endpoints::

    $ curl --silent --header "Content-Type: application/x-www-form-urlencoded" --header "Accept: application/json" --request POST --data "username=admin&password=admin&client_id=CfR9JqZkNkllBA6Am5a7Za95pvppJG2lsOlKRzRn&grant_type=password" http://localhost:8000/o/token/| python -mjson.tool
    {
        "access_token": "w5bnAX9Hew3dcor4zJyWt2DW5L2RjQ",
        "expires_in": 36000,
        "refresh_token": "fO4wb7OYSPZFoyV6ugUPnXmGa4s2wj",
        "scope": "read write",
        "token_type": "Bearer"
    }

    $ curl --silent --header "Accept: application/json" --header "Authorization: Bearer w5bnAX9Hew3dcor4zJyWt2DW5L2RjQ" http://localhost:8000/api/v1/user_profiles/ | python -mjson.tool
    {
        "meta": {
            "limit": 20,
            "next": null,
            "offset": 0,
            "previous": null,
            "total_count": 3
        },
        "objects": [
            {
                "date_of_birth": "2015-07-04",
                "gender": "M",
                "image": "/media/user_profile_image/1/admin_nhOs1pw.png",
                "phone_number": "+12126160002",
                "resource_uri": "/api/v1/user_profiles/1/"
            },
            {
                "date_of_birth": "2015-07-09",
                "gender": "M",
                "image": null,
                "phone_number": "+12126160001",
                "resource_uri": "/api/v1/user_profiles/2/"
            },
            {
                "date_of_birth": "2015-07-10",
                "gender": "F",
                "image": null,
                "phone_number": "+12126160000",
                "resource_uri": "/api/v1/user_profiles/3/"
            }
        ]
    }

Just to be sure, try to hit the same resource without providing the ``Authorization`` HTTP header::

    $ curl --verbose --header "Accept: application/json" http://localhost:8000/api/v1/user_profiles/
    *   Trying 127.0.0.1...
    * Connected to localhost (127.0.0.1) port 8000 (#0)
    > GET /api/user_profiles/ HTTP/1.1
    > User-Agent: curl/7.40.0
    > Host: localhost:8000
    > Accept: application/json
    >
    * HTTP 1.0, assume close after body
    < HTTP/1.0 401 UNAUTHORIZED
    < Date: Fri, 24 Jul 2015 20:04:59 GMT
    < Server: WSGIServer/0.2 CPython/3.4.2
    < Content-Type: text/html; charset=utf-8
    < X-Frame-Options: SAMEORIGIN
    <
    * Closing connection 0

Using Base64FileField
---------------------

For solution using the custom file field we made use of the `Base64FileField <https://gist.github.com/klipstein/709890>`_ that allows us to update the resources providing Base64 encoded file contents within the JSON payload. Afterwards when we retrieve the resource, the URL for it is presented. Here's the implementation::

    class UserProfileResource(ModelResource):
        # Suggested by https://github.com/django-tastypie/django-tastypie/issues/42
        image = Base64FileField("image", null=True, blank=True)

        class Meta:
            queryset = UserProfile.objects.all()
            resource_name = 'user_profiles'
            authentication = OAuth20Authentication()
            authorization = DjangoAuthorization()

As you can see, it is pretty simple, as we only need to declare the specific field. The following session shows how it would work::

    $ curl --silent --header "Accept: application/json" --header "Authorization: Bearer w5bnAX9Hew3dcor4zJyWt2DW5L2RjQ" http://localhost:8000/api/v1/user_profiles/1/ | python -mjson.tool
    {
        "date_of_birth": "2015-07-04",
        "gender": "M",
        "image": "/media/user_profile_image/1/admin.png",
        "phone_number": "+12126160002",
        "resource_uri": "/api/v1/user_profiles/1/"
    }

    $ curl --verbose --header "Accept: application/json" --header "Authorization: Bearer w5bnAX9Hew3dcor4zJyWt2DW5L2RjQ" --header "Content-Type: application/json" --request POST --data '{"date_of_birth": "2015-07-04", "gender": "M", "image": {"name": "admin2.png", "file": "iVBORw0KGgoAAAANSUhEUgAAAoAAAAGQCAIAAACxkUZyAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3wcXAQ4OKKvd0gAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAAE+klEQVR42u3VMREAAAjEsAf/nsEFA5dI6NLKBAA41hIAgAEDgAEDAAYMAAYMABgwABgwAGDAAGDAAIABA4ABA4ABAwAGDAAGDAAYMAAYMABgwABgwACAAQOAAQOAAQMABgwABgwAGDAAGDAAYMAAYMAAgAEDgAEDgAEDAAYMAAYMABgwABgwAGDAAGDAAIABA4ABA4ABAwAGDAAGDAAYMAAYMABgwABgwACAAQOAAQOAAQMABgwABgwAGDAAGDAAYMAAYMAAgAEDgAEDgAEDAAYMAAYMABgwABgwAGDAAGDAAIABA4ABA4ABAwAGDAAGDAAYMAAYMABgwABgwACAAQOAAQOAAQMABgwABgwAGDAAGDAAYMAAYMAAgAEDgAEDgAEDAAYMAAYMABgwABgwAGDAAGDAAIABA4ABAwAGDAAGDAAGDAAYMAAYMABgwABgwACAAQOAAQMABgwABgwABgwAGDAAGDAAYMAAYMAAgAEDgAEDAAYMAAYMAAYMABgwABgwAGDAAGDAAIABA4ABAwAGDAAGDAAGDAAYMAAYMABgwABgwACAAQOAAQMABgwABgwABgwAGDAAGDAAYMAAYMAAgAEDgAEDAAYMAAYMAAYMABgwABgwAGDAAGDAAIABA4ABAwAGDAAGDAAGDAAYMAAYMABgwABgwACAAQOAAQMABgwABgwABgwAGDAAGDAAYMAAYMAAgAEDgAEDAAYMAAYMAAYMABgwABgwAGDAAGDAAIABA4ABAwAGDAAGDAAYMAAYMAAYMABgwABgwACAAQOAAQMABgwABgwAGDAAGDAAGDAAYMAAYMAAgAEDgAEDAAYMAAYMABgwABgwABgwAGDAAGDAAIABA4ABAwAGDAAGDAAYMAAYMAAYMABgwABgwACAAQOAAQMABgwABgwAGDAAGDAAGDAAYMAAYMAAgAEDgAEDAAYMAAYMABgwABgwABgwAGDAAGDAAIABA4ABAwAGDAAGDAAYMAAYMAAYMABgwABgwACAAQOAAQMABgwABgwAGDAAGDAAGDAAYMAAYMAAgAEDgAEDAAYMAAYMABgwABgwABgwAGDAAGDAAIABA4ABAwAGDAAGDAAYMAAYMAAYsAQAYMAAYMAAgAEDgAEDAAYMAAYMABgwABgwAGDAAGDAAGDAAIABA4ABAwAGDAAGDAAYMAAYMABgwABgwABgwACAAQOAAQMABgwABgwAGDAAGDAAYMAAYMAAYMAAgAEDgAEDAAYMAAYMABgwABgwAGDAAGDAAGDAAIABA4ABAwAGDAAGDAAYMAAYMABgwABgwABgwACAAQOAAQMABgwABgwAGDAAGDAAYMAAYMAAYMAAgAEDgAEDAAYMAAYMABgwABgwAGDAAGDAAGDAAIABA4ABAwAGDAAGDAAYMAAYMABgwABgwABgwACAAQOAAQMABgwABgwAGDAAGDAAYMAAYMAAYMAAgAEDgAEDAAYMAAYMABgwABgwAGDAAGDAAIABA4ABA4ABAwAGDAAGDAAYMAAYMABgwABgwACAAQOAAQOAAQMABgwABgwAGDAAGDAAYMAAYMAAgAEDgAEDgAEDAAYMAAYMABgwABgwAGDAAGDAAIABA4ABA4ABAwAGDAAGDAAYMAAYMABgwABgwACAAQOAAQOAAQMABgwABgwAGDAAGDAAYMAAYMAAgAEDgAEDgAEDAAYMAH8tQcUEH9I2Dr8AAAAASUVORK5CYII=", "content_type": "image/png" }, "phone_number": "+12126160002"}' --request PUT http://localhost:8000/api/v1/user_profiles/1/; echo
    *   Trying 127.0.0.1...
    * Connected to localhost (127.0.0.1) port 8000 (#0)
    > PUT /api/user_profiles/1/ HTTP/1.1
    > User-Agent: curl/7.40.0
    > Host: localhost:8000
    > Accept: application/json
    > Authorization: Bearer w5bnAX9Hew3dcor4zJyWt2DW5L2RjQ
    > Content-Type: application/json
    > Content-Length: 2037
    > Expect: 100-continue
    >
    * Done waiting for 100-continue
    * HTTP 1.0, assume close after body
    < HTTP/1.0 204 NO CONTENT
    < Date: Fri, 24 Jul 2015 20:33:23 GMT
    < Server: WSGIServer/0.2 CPython/3.4.2
    < X-Frame-Options: SAMEORIGIN
    < Content-Length: 0
    < Content-Type: text/html; charset=utf-8
    < Vary: Accept
    <
    * Closing connection 0

    $ curl --silent --header "Accept: application/json" --header "Authorization: Bearer w5bnAX9Hew3dcor4zJyWt2DW5L2RjQ" http://localhost:8000/api/user_profiles/1/; echo
    {"date_of_birth": "2015-07-04", "gender": "M", "image": "/media/user_profile_image/1/admin2.png", "phone_number": "+12126160002", "resource_uri": "/api/user_profiles/1/"}

We supply the file contents encoded in Base64 and a little bit of information about it, and the field handles the rest.

Using a nested resource
-----------------------

The solution using a nested resource is almost the same as I used in the other project. We define a nested resource within the context of a specific file, and within the view's implementation we handle uploads as we would do with a regular Django site::

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

In ``prepend_urls`` we declare which URLs are we going to handle and in ``set_image`` we handle the upload itself. The first part of the method follows the recipe for nested resources as defined in Tastypie's `Cookbook <http://django-tastypie.readthedocs.org/en/latest/cookbook.html>`_. We use a Django form to validate the request, and we update the Django object using the uploaded file. The following session shows how it would work::

    $ curl --silent --header "Accept: application/json" --header "Authorization: Bearer w5bnAX9Hew3dcor4zJyWt2DW5L2RjQ" http://localhost:8000/api/v1/user_profiles_nested_image/1/; echo
    {"date_of_birth": "2015-07-04", "gender": "M", "image": "/media/user_profile_image/1/admin.png", "phone_number": "+12126160002", "resource_uri": "/api/v1/user_profiles_nested_image/1/"}

    $ curl --verbose --header "Authorization: Bearer w5bnAX9Hew3dcor4zJyWt2DW5L2RjQ" --header "Accept: application/json" --request POST --form upload=@admin2.png http://localhost:8000/api/v1/user_profiles_nested_image/1/image/; echo
    *   Trying 127.0.0.1...
    * Connected to localhost (127.0.0.1) port 8000 (#0)
    * Initializing NSS with certpath: sql:/etc/pki/nssdb
    > POST /api/v1/user_profiles_nested_image/1/image/ HTTP/1.1
    > User-Agent: curl/7.40.0
    > Host: localhost:8000
    > Authorization: Bearer w5bnAX9Hew3dcor4zJyWt2DW5L2RjQ
    > Accept: application/json
    > Content-Length: 1616
    > Expect: 100-continue
    > Content-Type: multipart/form-data; boundary=------------------------d6e1b936740451d1
    >
    * Done waiting for 100-continue
    * HTTP 1.0, assume close after body
    < HTTP/1.0 201 CREATED
    < Date: Fri, 24 Jul 2015 21:24:42 GMT
    < Server: WSGIServer/0.2 CPython/3.4.2
    < Content-Type: text/html; charset=utf-8
    < X-Frame-Options: SAMEORIGIN
    < Vary: Accept
    < Location: http://localhost:8000/media/user_profile_image/1/admin2.png
    <
    * Closing connection 0

    $ curl --silent --header "Accept: application/json" --header "Authorization: Bearer w5bnAX9Hew3dcor4zJyWt2DW5L2RjQ" http://localhost:8000/api/v1/user_profiles_nested_image/1/; echo
    {"date_of_birth": "2015-07-04", "gender": "M", "image": "/media/user_profile_image/1/admin2.png", "phone_number": "+12126160002", "resource_uri": "/api/v1/user_profiles_nested_image/1/"}

Notice that the file is uploaded using multi-part form encoding.

Feedback
--------

As usual, I welcome comments, suggestions and pull requests.
