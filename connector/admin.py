from django.contrib import admin
from django import forms
from .models import Group, User, UserState, Meeting, Invitation, Feedback, Message


# Register your models here.
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = '__all__'


class UserAdmin(admin.ModelAdmin):
    form = UserForm
    list_display = ('telegram_id', 'phone_number', 'full_name', 'finished_registration', 'enabled', 'last_seen_at')


# Register your models here.
class UserStateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = '__all__'


class UserStateAdmin(admin.ModelAdmin):
    form = UserStateForm
    list_display = ('user', 'context', 'updated_at')


class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = '__all__'


class InvitationAdmin(admin.ModelAdmin):
    form = InvitationForm
    list_display = ('user', 'year', 'week', 'accepted', 'cancel_reason', 'message_id', 'counter', 'sent_at', 'decided_at')


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = '__all__'


class GroupAdmin(admin.ModelAdmin):
    form = GroupForm
    list_display = ('name', 'number_of_people', 'created_at')


class MeetingForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = '__all__'


class MeetingAdmin(admin.ModelAdmin):
    form = MeetingForm
    list_display = ('created_at', 'broadcasted_at', 'year', 'week', 'user_a', 'user_b', 'meeting_took_place_aggregated')


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = '__all__'


class MessageAdmin(admin.ModelAdmin):
    form = MessageForm
    list_display = ('sent_at', 'message_id', 'direction', 'user', 'text')


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = '__all__'


class FeedbackAdmin(admin.ModelAdmin):
    form = FeedbackForm
    list_display = ('sent_at', 'user', 'text')


admin.site.register(Group, GroupAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(UserState, UserStateAdmin)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(Meeting, MeetingAdmin)
admin.site.register(Feedback, FeedbackAdmin)
admin.site.register(Message, MessageAdmin)
