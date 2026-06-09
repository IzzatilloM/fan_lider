from django import forms

from courses.models import Course

from .models import Assessment, Lesson

_INPUT = 'form-control'
_SELECT = 'form-select'


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ['student', 'course', 'type', 'title', 'date', 'score', 'max_score', 'comment']
        widgets = {
            'student': forms.Select(attrs={'class': _SELECT}),
            'course': forms.Select(attrs={'class': _SELECT}),
            'type': forms.Select(attrs={'class': _SELECT}),
            'title': forms.TextInput(attrs={'class': _INPUT}),
            'date': forms.DateInput(attrs={'class': _INPUT, 'type': 'date'}),
            'score': forms.NumberInput(attrs={'class': _INPUT, 'step': '0.5'}),
            'max_score': forms.NumberInput(attrs={'class': _INPUT, 'step': '0.5'}),
            'comment': forms.TextInput(attrs={'class': _INPUT}),
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['course', 'date', 'topic', 'description', 'homework']
        widgets = {
            'course': forms.Select(attrs={'class': _SELECT}),
            'date': forms.DateInput(attrs={'class': _INPUT, 'type': 'date'}),
            'topic': forms.TextInput(attrs={'class': _INPUT}),
            'description': forms.Textarea(attrs={'class': _INPUT, 'rows': 2}),
            'homework': forms.Textarea(attrs={'class': _INPUT, 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].queryset = Course.objects.exclude(status='finished')
