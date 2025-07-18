FROM python:3.13

WORKDIR /home/app

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN venv/bin/pip install --upgrade pip
RUN venv/bin/pip install -r requirements.txt

RUN apt-get update
RUN apt-get install -y dos2unix

COPY app_pkg app_pkg
COPY migrations migrations
COPY services services
COPY dicomWebApp.py config.py boot.sh ./

RUN dos2unix < boot.sh > boot_bkp.sh
RUN rm boot.sh
RUN mv boot_bkp.sh boot.sh
RUN chmod +x boot.sh

CMD ["./boot.sh"]