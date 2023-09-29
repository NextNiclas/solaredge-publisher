FROM python:slim

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org install -r requirements.txt
COPY main.py main.py

CMD ["python3","main.py"]