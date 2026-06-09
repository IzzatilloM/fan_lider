import django, os, glob
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.template.loader import get_template
from django.template import TemplateSyntaxError

base = 'templates'
bad = 0
n = 0
for f in glob.glob(base + '/**/*.html', recursive=True):
    rel = os.path.relpath(f, base).replace(os.sep, '/')
    n += 1
    try:
        get_template(rel)
    except TemplateSyntaxError as e:
        bad += 1
        print('SYNTAX ERROR', rel, '->', e)
    except Exception as e:
        bad += 1
        print('ERROR', rel, '->', type(e).__name__, e)
print(f'checked {n} templates, problems={bad}')
