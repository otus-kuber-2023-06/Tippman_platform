FROM python:3.7
COPY templates ./templates
COPY mysql-operator.py ./mysql-operator.py
RUN pip install --upgrade pip && pip install kopf pyyaml kubernetes jinja2
CMD kopf run /mysql-operator.py --verbose