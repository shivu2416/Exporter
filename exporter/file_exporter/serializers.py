from rest_framework import serializers
from .models import *



class  MembersSerialzer(serializers.ModelSerializer):
    
    class Meta:
        model = Member
        fields = '__all__'
        
        

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'description']