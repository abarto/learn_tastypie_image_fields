from tastypie.resources import ModelResource
from .models import UserProfile


class UserProfileResource(ModelResource):
    class Meta:
        queryset = UserProfile.objects.all()
        resource_name = 'user_profiles'
